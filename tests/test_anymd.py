from __future__ import annotations

import subprocess

from stopreplay_collect.adapters import AnyMDAdapter
from stopreplay_collect.models import ResearchRequest
from stopreplay_collect.pipeline import CollectionPipeline


def test_anymd_preserves_locators_across_runs(tmp_path, monkeypatch, storage):
    pdf = tmp_path / "two pages.pdf"
    pdf.write_bytes(b"original pdf bytes")
    docx = tmp_path / "brief.docx"
    docx.write_bytes(b"original docx bytes")

    def convert(command, **kwargs):
        assert command[-2] == "--"
        assert kwargs["check"] is True
        if command[-1] == str(pdf):
            markdown = "<!-- page 1 -->\n\nOrganization intro.\n\n<!-- page 2 -->\n\nProject details.\n"
        else:
            assert command[-1] == str(docx)
            markdown = "Organization announcements.\n"
        return subprocess.CompletedProcess(command, 0, stdout=markdown)

    monkeypatch.setattr(subprocess, "run", convert)
    pipeline = CollectionPipeline(storage)
    adapter = AnyMDAdapter()
    params = {"documents": [pdf, docx]}
    request = ResearchRequest("recon", "fixture", params=params)

    assert pipeline.run(adapter, request).sources_registered == 3
    assert pipeline.run(adapter, request).sources_registered == 0
    sources = {source["locator"]: source for source in storage.get_sources("recon")}
    assert sources["page 1"]["excerpt"] == "Organization intro."
    assert sources["page 2"]["excerpt"] == "Project details."
    pdf_source = storage.get_source("recon", sources["page 2"]["source_ref"])
    docx_source = storage.get_source("recon", sources["document"]["source_ref"])
    assert pdf_source["file_ref"] == str(pdf)
    assert docx_source["file_ref"] == str(docx)
    assert storage.get_facts("recon") == []

    filtered = ResearchRequest("another", "fixture", must_include=["Project"], params=params)
    report = pipeline.run(adapter, filtered)
    assert report.sources_registered == 1
    assert len(report.filtered) == 2
    [source] = storage.get_sources("another")
    assert source["source_ref"] == sources["page 2"]["source_ref"]


def test_anymd_continues_after_missing_and_unanchored_files(tmp_path, monkeypatch):
    corrupt = tmp_path / "corrupt.pdf"
    good = tmp_path / "good.pdf"
    corrupt.write_bytes(b"corrupt")
    good.write_bytes(b"good")

    def convert(command, **kwargs):
        markdown = "unanchored text" if command[-1] == str(corrupt) else "<!-- page 4 -->\ntext"
        return subprocess.CompletedProcess(command, 0, stdout=markdown)

    monkeypatch.setattr(subprocess, "run", convert)
    params = {"documents": [tmp_path / "missing.pdf", corrupt, good]}
    output = AnyMDAdapter().collect(ResearchRequest("recon", "fixture", params=params))

    assert len(output.retrieval_failures) == 1
    assert len(output.extraction_failures) == 1
    assert [source.locator for source in output.sources] == ["page 4"]

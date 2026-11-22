from __future__ import annotations

import json
from unittest.mock import Mock

from stopreplay_collect import run
from stopreplay_collect.adapters import OSMnxAdapter
from stopreplay_collect.models import CollectionOutput, DraftFact, DraftSource, ResearchRequest
from stopreplay_collect.pipeline import CollectionPipeline
from stopreplay_collect.static import StaticAdapter


def test_osmnx_cli_resolves_only_same_run_public_fact(storage, monkeypatch, capsys):
    source = DraftSource("demo-city", "file_upload", excerpt="The synthetic team is based in Munich, Germany.")
    fact = DraftFact("fixture", "based_in: Munich, Germany", "other", source.source_ref, assertable=True)
    adapter = StaticAdapter(CollectionOutput(sources=[source], facts=[fact]), "fixture")
    imported = CollectionPipeline(storage).run(adapter, ResearchRequest("recon", "fixture"))
    fact_id = str(imported.accepted[0]["fact_id"])

    lookup = Mock(return_value={
        "osm_type": "relation", "osm_id": 62428, "addresstype": "city",
        "display_name": "Munich, Bavaria, Germany",
    })
    monkeypatch.setitem(run._ADAPTERS, "osmnx", lambda: OSMnxAdapter(lookup=lookup))
    arguments = ["--adapter", "osmnx", "--subject", "fixture", "--based-in-fact", fact_id]

    assert run.main([*arguments, "--run", "other"]) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["retrieval_failures"] == 1
    lookup.assert_not_called()
    assert run.main(arguments) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["sources_registered"] == 1
    lookup.assert_called_once_with("Munich", "Germany")
    assert run.main(arguments) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["sources_registered"] == 0

    preserved = storage.get_source("recon", "osm:relation:62428")
    assert preserved["url"] == "https://www.openstreetmap.org/relation/62428"
    assert preserved["locator"] == "relation 62428"
    assert "© OpenStreetMap contributors" in preserved["excerpt"]
    assert len(storage.get_facts("recon")) == 1


def test_osmnx_reports_unresolved_and_non_municipal_lookups():
    lookup = Mock(side_effect=[ValueError("no results"), {
        "osm_type": "way", "osm_id": 42, "addresstype": "road", "display_name": "Road",
    }])
    adapter = OSMnxAdapter(lookup=lookup)

    def collect(claim):
        return adapter.collect(ResearchRequest("recon", "fixture", params={"based_in": claim}))

    assert len(collect("based_in: 4 High Street, Germany").retrieval_failures) == 1
    lookup.assert_not_called()
    assert len(collect("based_in: Munich, Germany").retrieval_failures) == 1
    assert len(collect("based_in: Munich, Germany").extraction_failures) == 1

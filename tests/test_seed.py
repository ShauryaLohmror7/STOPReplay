"""Seed analysis + seed ingestion tests."""
from __future__ import annotations

from stopreplay_collect import CollectionPipeline, ResearchRequest
from stopreplay_collect.seed import SeedAdapter, analyze_seed

JULIUS = "Julius Muth, revel8.ai Co-founder and Co-CEO sales"


def test_analyze_seed_extracts_name_org_anchor():
    a = analyze_seed("julius", JULIUS)
    assert a.name == "Julius Muth"
    assert a.org == "revel8"
    assert a.must_include == ["revel8"]
    assert a.include_domains == ["revel8.ai"]
    assert a.query == "Julius Muth revel8"
    claims = [f.claim for f in a.facts]
    assert "full_name: Julius Muth" in claims
    assert "company_domain: revel8.ai" in claims
    assert any(c.startswith("Co-founder and Co-CEO") and "revel8" in c for c in claims)


def test_date_of_birth_is_private_and_not_an_anchor():
    a = analyze_seed("jane", "Jane Doe born 1987 Munich")
    dob = [f for f in a.facts if f.claim.startswith("date_of_birth:")]
    assert dob and dob[0].sensitivity == "private"
    assert "1987" not in a.must_include            # a date is a scoring signal, not a filter


def test_seed_adapter_stores_foundation_facts(storage):
    report = CollectionPipeline(storage).run(
        SeedAdapter(JULIUS), ResearchRequest("recon", "julius"))
    assert report.summary()["accepted"] >= 3      # name, domain, role (at least)
    claims = [f["claim"] for f in storage.get_facts("recon", subject="julius")]
    assert "full_name: Julius Muth" in claims
    assert any("Co-CEO" in c for c in claims)
    assert storage.get_source("recon", "seed:julius") is not None


def test_private_seed_attribute_is_gated(storage):
    blocked = CollectionPipeline(storage).run(
        SeedAdapter("Jane Doe born 1987 Munich"), ResearchRequest("recon", "jane"))
    assert any("synthetic_authorized" in r["errors"][0] for r in blocked.rejected)

    allowed = CollectionPipeline(storage).run(
        SeedAdapter("Jane Doe born 1987 Munich"),
        ResearchRequest("recon", "jane", synthetic_authorized=True))
    assert any(f["claim"].startswith("date_of_birth:")
               for f in storage.get_facts("recon", subject="jane"))

"""Recon orchestrator tests with a mock storage layer."""
from __future__ import annotations

from stopreplay_collect import DraftFact, DraftSource
from stopreplay_collect.recon import run_recon


class MemoryStorage:
    def __init__(self):
        self.sources: dict[tuple[str, str], dict] = {}
        self.facts: list[dict] = []
        self._fact_counter = 0

    def register_source(self, data: dict) -> str:
        key = (data["run_id"], data["source_ref"])
        if key in self.sources:
            return "exists"
        self.sources[key] = dict(data)
        return "inserted"

    def get_source(self, run_id: str, source_ref: str) -> dict | None:
        return self.sources.get((run_id, source_ref))

    def get_sources(self, run_id: str) -> list[dict]:
        return [s for (r, _), s in self.sources.items() if r == run_id]

    def insert_fact(self, data: dict) -> str:
        self._fact_counter += 1
        fact_id = f"fact-{self._fact_counter}"
        rec = dict(data, id=fact_id)
        self.facts.append(rec)
        return fact_id

    def get_facts(self, run_id: str, subject: str | None = None, category: str | None = None) -> list[dict]:
        res = [f for f in self.facts if f["source_run"] == run_id]
        if subject:
            res = [f for f in res if f["subject"] == subject]
        if category:
            res = [f for f in res if f["category"] == category]
        return res


def test_run_recon_flow():
    storage = MemoryStorage()
    seed = "Julius Muth, revel8.ai Co-founder and Co-CEO"

    analysis, seed_rep, web_rep, gh_rep, ext_rep, hn_rep, arxiv_rep = run_recon(
        storage, "julius", seed, source_run="test-recon", limit=2,
        fetch_transcripts=False
    )

    assert analysis.name == "Julius Muth"
    assert "revel8" in analysis.must_include
    assert "revel8.ai" in analysis.include_domains
    assert hn_rep is not None
    assert arxiv_rep is not None

    # Seed facts should be persisted
    seed_facts = storage.get_facts("test-recon", subject="julius")
    claims = [f["claim"] for f in seed_facts]
    assert any("full_name: Julius Muth" in c for c in claims)
    assert any("company_domain: revel8.ai" in c for c in claims)

    # Seed source should be registered
    assert storage.get_source("test-recon", "seed:julius") is not None

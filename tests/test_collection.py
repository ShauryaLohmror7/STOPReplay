"""Collection framework + Identity adapter tests (against real Postgres)."""
from __future__ import annotations

from stopreplay_collect import (
    CollectionOutput,
    CollectionPipeline,
    DraftFact,
    DraftSource,
    IdentityAdapter,
    ResearchRequest,
)
from stopreplay_collect.base import CollectionAdapter

RUN = "recon"

JULIUS = {
    "name": "Julius Muth", "role": "Co-CEO", "org": "revel8",
    "source_ref": "identity:julius", "source_text": "Julius Muth — Co-CEO at revel8.",
    "confidence": 0.95,
}


def _request(profile, **kw):
    return ResearchRequest(source_run=RUN, subject="julius",
                           params={"profile": profile}, **kw)


class _StaticAdapter(CollectionAdapter):
    """Returns a fixed output, for exercising validation edge cases."""
    name = "static"

    def __init__(self, output: CollectionOutput):
        self._output = output

    def collect(self, request):
        return self._output


# -- identity adapter -------------------------------------------------------
def test_identity_accepts_and_registers(storage):
    report = CollectionPipeline(storage).run(IdentityAdapter(), _request(JULIUS))
    assert report.summary()["accepted"] == 1
    assert report.sources_registered == 1
    facts = storage.get_facts(RUN, subject="julius")
    assert facts[0]["claim"] == "Julius Muth is Co-CEO at revel8"
    assert storage.get_source(RUN, "identity:julius") is not None


def test_identity_dedup_on_rerun(storage):
    pipe = CollectionPipeline(storage)
    pipe.run(IdentityAdapter(), _request(JULIUS))
    second = pipe.run(IdentityAdapter(), _request(JULIUS))
    assert second.summary()["accepted"] == 0
    assert second.summary()["duplicates"] == 1
    assert len(storage.get_facts(RUN, subject="julius")) == 1


def test_identity_ambiguous_lowers_confidence(storage):
    profile = dict(JULIUS, ambiguous=True, confidence=0.95)
    CollectionPipeline(storage).run(IdentityAdapter(), _request(profile))
    fact = storage.get_facts(RUN, subject="julius")[0]
    assert fact["confidence"] <= 0.5
    assert fact["assertable"] is False


# -- guardrails -------------------------------------------------------------
def test_sensitivity_gate_blocks_private_without_authorization(storage):
    profile = dict(JULIUS, contacts=[
        {"kind": "personal mobile", "value": "redacted", "sensitivity": "private"}])
    report = CollectionPipeline(storage).run(IdentityAdapter(), _request(profile))
    # role fact accepted, private contact rejected by the gate
    assert report.summary()["accepted"] == 1
    assert report.summary()["rejected"] == 1
    assert "synthetic_authorized" in report.rejected[0]["errors"][0]


def test_sensitivity_gate_allows_when_authorized(storage):
    profile = dict(JULIUS, contacts=[
        {"kind": "personal mobile", "value": "redacted", "sensitivity": "private"}])
    report = CollectionPipeline(storage).run(
        IdentityAdapter(), _request(profile, synthetic_authorized=True))
    assert report.summary()["accepted"] == 2
    assert report.summary()["rejected"] == 0


# -- validation edge cases via a static adapter -----------------------------
def test_invalid_category_rejected(storage):
    out = CollectionOutput(
        sources=[DraftSource(source_ref="s1", origin="public_web",
                             url="http://example.test", excerpt="x")],
        facts=[DraftFact(subject="julius", claim="c", category="bogus", source_ref="s1")],
    )
    report = CollectionPipeline(storage).run(_StaticAdapter(out), ResearchRequest(RUN, "julius"))
    assert report.summary()["accepted"] == 0
    assert any("invalid category" in e for e in report.rejected[0]["errors"])


def test_unresolved_source_rejected(storage):
    out = CollectionOutput(
        facts=[DraftFact(subject="julius", claim="c", category="role", source_ref="missing")],
    )
    report = CollectionPipeline(storage).run(_StaticAdapter(out), ResearchRequest(RUN, "julius"))
    assert report.summary()["accepted"] == 0
    assert any("unresolved source_ref" in e for e in report.rejected[0]["errors"])


def test_inferred_source_requires_locator(storage):
    out = CollectionOutput(
        sources=[DraftSource(source_ref="i1", origin="inferred", excerpt="guess")],
    )
    report = CollectionPipeline(storage).run(_StaticAdapter(out), ResearchRequest(RUN, "julius"))
    assert report.summary()["sources_registered"] == 0
    assert any("inferred source" in e for e in report.rejected[0]["errors"])

"""Exact-match responses for the synthetic room fixture; not a general model."""

from .models import AnalysisRequest, RuntimeMetadata


class RoomFixtureAdapter:
    metadata = RuntimeMetadata("local-fake", "room-fixture-v1", "room-fixture-v1")

    def generate(self, request: AnalysisRequest) -> dict:
        event = request.event
        if event.text not in ("The demo is in Room A.", "Correction: the demo is in Room B."):
            return {"outcome": "no_change", "finding": None,
                    "reason": "Fixture adapter does not interpret this text; no finding proposed."}
        revised_ids = {f.revises for f in request.previous_findings}
        earlier = [f for f in request.previous_findings
                   if f.finding_id not in revised_ids
                   and f.statement == "The agenda says the demo is in Room A."]
        correction = event.text == "Correction: the demo is in Room B."
        target = earlier[-1].finding_id if correction and earlier else None
        return {
            "outcome": "revision" if target else "new",
            "finding": {
                "statement": ("The corrected agenda says the demo is in Room B." if correction
                              else "The agenda says the demo is in Room A."),
                "kind": "observation",
                "evidence": [{"event_id": event.event_id, "source_ref": event.source_ref, "quote": event.text}],
                "revises": target,
                "uncertainty": None,
            },
            "reason": "An explicit agenda correction revises the earlier finding." if target
                      else "The source directly states the room.",
        }

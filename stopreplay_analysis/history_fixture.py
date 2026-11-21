"""Generate synthetic full-history examples; no database or controller execution."""

import json
from dataclasses import asdict
from pathlib import Path

from . import Analyzer, Event
from .fake import RoomFixtureAdapter


def build_history_fixture() -> dict:
    path = Path(__file__).resolve().parent.parent / "fixtures" / "history.json"
    fixture = json.loads(path.read_text())
    analyzer = Analyzer(RoomFixtureAdapter())
    events, findings, steps = [], [], []
    for raw in fixture["events"]:
        event = Event.from_dict(raw)
        if fixture["sources"][event.source_ref]["text"] != event.text:
            raise ValueError("Fixture source does not match event text.")
        context = {
            "run_id": event.run_id, "analysis_id": fixture["analysis_id"],
            "before_sequence": event.sequence,
            "events": [asdict(item) for item in events],
            "findings": [asdict(item) for item in findings],
        }
        result = analyzer.analyze_incremental(
            event, analysis_id=fixture["analysis_id"],
            previous_events=events, previous_findings=findings)
        events.append(event)
        if result.finding is not None:
            findings.append(result.finding)
        superseded = {item.revises for item in findings}
        steps.append({
            "event": raw, "context_before": context, "result": result.to_dict(),
            "active_findings_after": [asdict(item) for item in findings
                                      if item.finding_id not in superseded],
        })
    return {
        "synthetic": True, "database_verified": False,
        "note": "Sequence-based fixture views, not committed turns. Fake responses; no model quality claim.",
        "sources": fixture["sources"], "steps": steps,
    }


if __name__ == "__main__":
    print(json.dumps(build_history_fixture(), indent=2))

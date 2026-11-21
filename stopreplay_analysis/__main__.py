"""Run the synthetic fixture: python3 -m stopreplay_analysis."""

import json
from dataclasses import asdict
from pathlib import Path

from . import Analyzer, Event
from .fake import RoomFixtureAdapter


def main() -> None:
    fixture = json.loads((Path(__file__).resolve().parent.parent / "fixtures" / "room.json").read_text())
    events = [Event.from_dict(value) for value in fixture["deliveries"]]
    for event in events:
        if fixture["sources"][event.source_ref]["text"] != event.text:
            raise ValueError("Fixture source does not match its event.")
    results = Analyzer(RoomFixtureAdapter()).analyze_initial(events, analysis_id="room-demo-v1")
    findings = [r.finding for r in results if r.finding is not None]
    # A read-only illustration for the handoff. Gary owns production projections.
    snapshots = {}
    for sequence in (1, 2):
        visible = [f for f in findings if f.sequence <= sequence]
        replaced = {f.revises for f in visible}
        snapshots[str(sequence)] = [asdict(f) for f in visible if f.finding_id not in replaced]
    print(json.dumps({"synthetic": True, "deliveries": len(events), "logical_events": len(results),
                      "results": [r.to_dict() for r in results],
                      "snapshots_by_sequence": snapshots}, indent=2))


if __name__ == "__main__":
    main()

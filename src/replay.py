"""Resumable stored-event analysis using the existing database/analysis contracts.

Execution calls this explicitly. Historical rendering only calls get_timeline;
it never calls this processor or sends a simulator message.
"""
from dataclasses import fields

from stopreplay_analysis.models import Event, Finding, Citation


def _event(row):
    return Event(**{field.name: row[field.name] for field in fields(Event)})


def _finding(row):
    data = {field.name: row[field.name] for field in fields(Finding)}
    data["evidence"] = tuple(Citation(**{field.name: citation[field.name] for field in fields(Citation)})
                             for citation in row["evidence"])
    return Finding(**data)


def replay_events(storage, analyzer, *, run_id, analysis_id):
    """Commit each analyzed event once; a failed turn leaves the checkpoint intact."""
    checkpoint = storage.current_checkpoint(run_id, analysis_id)
    completed = {r["event_id"] for r in storage.get_results(run_id, analysis_id)}
    events = sorted(storage.get_events(run_id), key=lambda e: e["sequence"])
    if len(completed) != checkpoint:
        raise ValueError("Analysis results and checkpoint disagree; reconcile storage first.")
    if {e["event_id"] for e in events[:checkpoint]} != completed:
        raise ValueError("Completed analysis is not a prefix of the event history.")
    for row in events[checkpoint:]:
        event = _event(row)
        context = storage.get_analysis_context(run_id, analysis_id, event.sequence)
        result = analyzer.analyze_incremental(
            event, analysis_id=analysis_id,
            previous_events=tuple(_event(e) for e in context["events"]),
            previous_findings=tuple(_finding(f) for f in context["findings"]))
        payload = result.to_dict()
        finding = payload.pop("finding")
        storage.commit_turn(run_id, analysis_id, checkpoint + 1, event.event_id,
                            payload, finding, expected_checkpoint=checkpoint)
        checkpoint += 1
    return storage.get_timeline(run_id, analysis_id, checkpoint)


def main():
    import argparse
    import json
    from stopreplay_db import Storage, db
    from stopreplay_analysis.engine import Analyzer
    from stopreplay_analysis.fake import RoomFixtureAdapter
    from src.runtime.adapter import ModelAdapter, build_analysis_adapter
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--analysis", required=True, help="Explicit version; reuse to resume, change to reanalyze")
    parser.add_argument("--reference", action="store_true", help="Deterministic room/history fixture only")
    args = parser.parse_args()
    if args.reference:
        adapter = RoomFixtureAdapter()
    else:
        model = ModelAdapter()
        if model.mock_mode or not model.api_key:
            parser.error("Configure the shared model or explicitly select --reference.")
        adapter = build_analysis_adapter(model)
    with db.connect() as connection:
        timeline = replay_events(Storage(connection), Analyzer(adapter), run_id=args.run, analysis_id=args.analysis)
    print(json.dumps(timeline, default=str, indent=2))


if __name__ == "__main__":
    main()

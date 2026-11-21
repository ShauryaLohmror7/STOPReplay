import json
import unittest
from pathlib import Path

from stopreplay_analysis import Analyzer, AnalysisError, Citation, Event, Finding
from stopreplay_analysis.fake import RoomFixtureAdapter
from stopreplay_analysis.history_fixture import build_history_fixture


class HistoryFixtureTests(unittest.TestCase):
    def test_full_history_survives_intervening_no_change_and_correction(self):
        value = build_history_fixture()
        first, second, third, fourth = value["steps"]
        self.assertEqual([s["result"]["outcome"] for s in value["steps"]],
                         ["new", "no_change", "revision", "no_change"])
        self.assertEqual(third["result"]["finding"]["revises"], first["result"]["finding"]["finding_id"])
        self.assertEqual(second["active_findings_after"], first["active_findings_after"])
        self.assertEqual(fourth["active_findings_after"], [third["result"]["finding"]])
        for step in value["steps"]:
            context = step["context_before"]
            self.assertTrue(all(e["sequence"] < context["before_sequence"] for e in context["events"]))
        self.assertNotIn("Room B", json.dumps(second["active_findings_after"]))
        self.assertEqual([e["event_id"] for e in fourth["context_before"]["events"]], ["e1", "e2", "e3"])
        self.assertEqual([f["sequence"] for f in fourth["context_before"]["findings"]], [1, 3])
        for step in (second, fourth):
            self.assertIsNone(step["result"]["finding"])
            self.assertIsNotNone(step["result"]["runtime"])
        expected = Path(__file__).resolve().parent.parent / "fixtures" / "history.expected.json"
        self.assertEqual(json.loads(json.dumps(value)), json.loads(expected.read_text()))

    def test_json_history_replays_and_missing_superseded_target_is_rejected(self):
        # Test-only decoding of Cem's proposed shape; controller adapter ownership stays with Shaurya.
        step = json.loads(json.dumps(build_history_fixture()))["steps"][-1]
        context = step["context_before"]
        events = [Event.from_dict(e) for e in context["events"]]
        findings = [Finding(**dict(f, evidence=tuple(Citation(**c) for c in f["evidence"])))
                    for f in context["findings"]]
        analyzer = Analyzer(RoomFixtureAdapter())
        result = analyzer.analyze_incremental(
            Event.from_dict(step["event"]), analysis_id=context["analysis_id"],
            previous_events=events, previous_findings=findings)
        self.assertEqual(result.to_dict(), step["result"])
        with self.assertRaises(AnalysisError) as caught:
            analyzer.analyze_incremental(
                Event.from_dict(step["event"]), analysis_id=context["analysis_id"],
                previous_events=events, previous_findings=findings[1:])
        self.assertEqual(caught.exception.code, "invalid_revision")

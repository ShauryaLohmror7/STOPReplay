import unittest
from dataclasses import replace

from stopreplay_analysis import Analyzer, AnalysisError, Citation
from stopreplay_analysis.fake import RoomFixtureAdapter
from stopreplay_analysis.guardrails import SemanticVerdict, verify_result

from tests.test_analysis import E1, E2, StubAdapter, proposal


class RecordingVerifier:
    def __init__(self, verdict=SemanticVerdict(True, "Quote states the room."), error=None):
        self.verdict = verdict
        self.error = error
        self.calls = []

    def __call__(self, request, result):
        self.calls.append((request, result))
        if self.error is not None:
            raise self.error
        return self.verdict


class SemanticVerifierTests(unittest.TestCase):
    def assert_error(self, code, fn):
        with self.assertRaises(AnalysisError) as caught:
            fn()
        self.assertEqual(caught.exception.code, code)

    def test_supported_verdict_returns_result_unchanged(self):
        verifier = RecordingVerifier()
        plain = Analyzer(RoomFixtureAdapter()).analyze_incremental(E1, analysis_id="v1")
        checked = Analyzer(RoomFixtureAdapter(), semantic_verifier=verifier).analyze_incremental(E1, analysis_id="v1")
        self.assertEqual(checked, plain)
        request, result = verifier.calls[0]
        self.assertEqual(request.event, E1)
        self.assertEqual(result, checked)

    def test_unsupported_or_malformed_verdict_withholds_result(self):
        for verdict in [SemanticVerdict(False, "Quote does not state a room."),
                        SemanticVerdict(True, ""), SemanticVerdict(True, "   "),
                        SemanticVerdict(1, "Truthy is not True."), {"supported": True, "explanation": "x"}, None]:
            with self.subTest(verdict=verdict):
                analyzer = Analyzer(RoomFixtureAdapter(), semantic_verifier=RecordingVerifier(verdict))
                self.assert_error("invalid_output", lambda: analyzer.analyze_incremental(E1, analysis_id="v1"))

    def test_verifier_failure_is_provider_failure_without_details(self):
        analyzer = Analyzer(RoomFixtureAdapter(), semantic_verifier=RecordingVerifier(error=RuntimeError("secret body")))
        with self.assertRaises(AnalysisError) as caught:
            analyzer.analyze_incremental(E1, analysis_id="v1")
        self.assertEqual(caught.exception.code, "provider_failure")
        self.assertNotIn("secret", str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)

    def test_model_no_change_is_reviewed(self):
        verifier = RecordingVerifier(SemanticVerdict(False, "The event does change the room."))
        response = {"outcome": "no_change", "finding": None, "reason": "Nothing new."}
        analyzer = Analyzer(StubAdapter(response), semantic_verifier=verifier)
        self.assert_error("invalid_output", lambda: analyzer.analyze_incremental(E1, analysis_id="v1"))
        self.assertEqual(verifier.calls[0][1].outcome, "no_change")

    def test_duplicate_delivery_skips_model_and_verifier(self):
        verifier = RecordingVerifier(error=AssertionError("must not run"))
        adapter = StubAdapter(error=AssertionError("must not run"))
        result = Analyzer(adapter, semantic_verifier=verifier).analyze_incremental(
            E1, analysis_id="v1", previous_events=[E1])
        self.assertEqual(result.outcome, "no_change")
        self.assertEqual((adapter.calls, verifier.calls), ([], []))

    def test_deterministic_validation_runs_before_verifier(self):
        verifier = RecordingVerifier()
        bad = proposal(evidence=[{"event_id": "e1", "source_ref": "agenda-v1", "quote": "Room Z"}])
        analyzer = Analyzer(StubAdapter(bad), semantic_verifier=verifier)
        self.assert_error("invalid_evidence", lambda: analyzer.analyze_incremental(E1, analysis_id="v1"))
        self.assertEqual(verifier.calls, [])

    def test_verify_result_directly(self):
        result = Analyzer(RoomFixtureAdapter()).analyze_incremental(E1, analysis_id="v1")
        self.assertIsNone(verify_result(None, result, RecordingVerifier()))


class UnresolvedHistoryTests(unittest.TestCase):
    def setUp(self):
        self.first = Analyzer(RoomFixtureAdapter()).analyze_incremental(E1, analysis_id="test-v1").finding
        response = proposal(E2, statement="The two records give different rooms.",
                            uncertainty="Sources disagree; no basis to choose one.")
        response["outcome"] = "conflict"
        response["finding"]["evidence"] += proposal()["finding"]["evidence"]
        self.conflict = Analyzer(StubAdapter(response)).analyze_incremental(
            E2, analysis_id="test-v1", previous_events=[E1], previous_findings=[self.first]).finding
        self.third = replace(E2, event_id="e3", sequence=3)

    def analyze_third(self, history):
        adapter = StubAdapter({"outcome": "no_change", "finding": None, "reason": "Nothing new."})
        result = Analyzer(adapter).analyze_incremental(
            self.third, analysis_id="test-v1", previous_events=[E1, E2], previous_findings=history)
        return result, adapter

    def test_valid_unresolved_history_is_accepted(self):
        result, adapter = self.analyze_third([self.first, self.conflict])
        self.assertEqual(result.outcome, "no_change")
        self.assertEqual(len(adapter.calls), 1)

    def test_unresolved_history_needs_both_sides_and_cannot_revise(self):
        one_sided = replace(self.conflict, evidence=(Citation("e2", E2.source_ref, E2.text),))
        revising = replace(self.conflict, revises=self.first.finding_id)
        for bad in (one_sided, revising):
            with self.subTest(bad=bad), self.assertRaises(AnalysisError) as caught:
                self.analyze_third([self.first, bad])
            self.assertEqual(caught.exception.code, "invalid_evidence")


if __name__ == "__main__":
    unittest.main()

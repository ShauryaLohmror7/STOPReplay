import copy
import json
import tempfile
import unittest
from pathlib import Path

from stopreplay_analysis import ModelRefusal
from stopreplay_analysis.evaluation import ReferenceAdapter, evaluate, load_cases, save_report


class EvaluationReportTests(unittest.TestCase):
    def test_provenance_identifies_actual_cases_and_keeps_inputs(self):
        cases = load_cases()
        report = evaluate(ReferenceAdapter(cases), cases=cases)
        self.assertEqual(report["provenance"]["dataset_version"], "analysis-quality-v2")
        self.assertEqual(report["configured_runtime"]["provider"], "local-reference")
        self.assertEqual(report["cases"][0]["input_events"][0], cases[0]["steps"][0]["event"])
        self.assertTrue(report["started_at_utc"].endswith("+00:00"))
        changed = copy.deepcopy(cases)
        changed[0]["review_questions"].append("Additional review question")
        other = evaluate(ReferenceAdapter(changed), cases=changed)
        self.assertIsNone(other["provenance"]["dataset_version"])
        self.assertEqual(other["provenance"]["dataset_scope"], "custom_cases")
        self.assertNotEqual(report["provenance"]["evaluated_cases_sha256"],
                            other["provenance"]["evaluated_cases_sha256"])
        self.assertEqual(report["provenance"]["python_sources_sha256"],
                         other["provenance"]["python_sources_sha256"])

    def test_invalid_response_and_provider_errors_preserve_later_cases(self):
        cases = load_cases()[:2]
        for failure, code in [(None, "invalid_output"), ("not decoded JSON", "invalid_output"),
                              (TimeoutError("private detail"), "timeout"),
                              (ModelRefusal("private detail"), "refusal"),
                              (RuntimeError("private detail"), "provider_failure")]:
            with self.subTest(code=code, failure=type(failure).__name__):
                reference = ReferenceAdapter(cases)

                class Adapter:
                    metadata = reference.metadata

                    def generate(self, request):
                        if request.event.run_id == cases[0]["steps"][0]["event"]["run_id"]:
                            if isinstance(failure, Exception):
                                raise failure
                            return failure
                        return reference.generate(request)

                report = evaluate(Adapter(), cases=cases)
                self.assertEqual(report["cases"][0]["steps"][0]["issues"][0]["code"], code)
                self.assertEqual(report["cases"][0]["unprocessed_steps"], 1)
                self.assertTrue(report["cases"][1]["automatic_checks_passed"])
                self.assertIsNotNone(report["configured_runtime"])
                self.assertNotIn("private detail", json.dumps(report))

    def test_invalid_event_stops_only_its_case(self):
        cases = load_cases()[:2]
        reference = ReferenceAdapter(cases)
        cases[0]["steps"][0]["event"]["sequence"] = True
        report = evaluate(reference, cases=cases)
        self.assertEqual(report["cases"][0]["steps"][0]["issues"][0]["code"], "invalid_input")
        self.assertTrue(report["cases"][1]["automatic_checks_passed"])

    def test_empty_or_duplicate_cases_cannot_appear_as_success(self):
        cases = load_cases()
        for bad in [[], [dict(cases[0], steps=[])], [cases[0], cases[0]]]:
            with self.assertRaises(ValueError):
                evaluate(ReferenceAdapter(cases), cases=bad)

    def test_saved_failure_report_roundtrips_and_cannot_be_overwritten(self):
        cases = load_cases()[:2]
        adapter = ReferenceAdapter(cases)
        adapter.responses[next(iter(adapter.responses))] = None
        report = evaluate(adapter, cases=cases)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            save_report(report, path)
            self.assertEqual(json.loads(path.read_text()), report)
            with self.assertRaises(FileExistsError):
                save_report({"replacement": True}, path)
            self.assertEqual(json.loads(path.read_text()), report)

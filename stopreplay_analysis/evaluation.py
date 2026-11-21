"""Run synthetic analysis acceptance cases through any injected model adapter.

CLI reference mode checks the evaluation plumbing, not a real model's quality.
"""

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from . import Analyzer, AnalysisError, AnalysisRequest, Event, ModelAdapter, RuntimeMetadata

DATASET = Path(__file__).resolve().parent.parent / "fixtures" / "analysis-quality.json"


def load_cases() -> list[dict[str, Any]]:
    return json.loads(DATASET.read_text())["cases"]


class ReferenceAdapter:
    """Hand-authored examples used only to verify the evaluation harness."""

    metadata = RuntimeMetadata("local-reference", "quality-reference-v1", "hand-authored-v1")

    def __init__(self, cases: list[dict[str, Any]]):
        self.responses = {
            (step["event"]["run_id"], step["event"]["event_id"]): step["reference_response"]
            for case in cases for step in case["steps"]
        }

    def generate(self, request: AnalysisRequest) -> dict[str, Any]:
        raw = copy.deepcopy(self.responses[(request.event.run_id, request.event.event_id)])
        if raw["finding"] is not None and raw["finding"]["revises"] == "$previous_finding":
            raw["finding"]["revises"] = request.previous_findings[-1].finding_id
        return raw


def evaluate(adapter: ModelAdapter, *, cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Check structure/classification and return prose for separate semantic review.

    Expected answers and reviewer guidance are never passed to the model adapter.
    Each case gets an independent run. A failed step stops its case, not the suite.
    """
    if cases is None:
        cases = load_cases()
    reports = []
    for case in cases:
        events, findings, results = [], [], {}
        steps = []
        for step in case["steps"]:
            event = Event.from_dict(step["event"])
            report = {"event_id": event.event_id, "issues": [], "result": None}
            try:
                result = Analyzer(adapter).analyze_incremental(
                    event, analysis_id="evaluation-v1", previous_events=events, previous_findings=findings)
            except AnalysisError as error:
                report["issues"].append(error.to_dict())
                steps.append(report)
                break
            report["result"] = result.to_dict()
            expected = step["expect"]
            issues = report["issues"]

            def issue(message: str) -> None:
                issues.append({"code": "expectation_mismatch", "message": message})

            if result.outcome not in expected["outcomes"]:
                issue("Outcome is outside the accepted outcomes for this example.")
            finding = result.finding
            if finding is not None:
                if finding.kind not in expected["kinds"]:
                    issue("Observation/inference classification does not match this example.")
                if not set(expected["required_evidence"]).issubset({c.event_id for c in finding.evidence}):
                    issue("Finding omits evidence required by this example.")
                if expected["uncertainty_required"] and not finding.uncertainty:
                    issue("This example requires an explicit uncertainty explanation.")
                previous_id = expected["revises_event"]
                target = results.get(previous_id) if previous_id is not None else None
                target_id = target.finding.finding_id if target is not None and target.finding is not None else None
                if finding.revises != target_id:
                    issue("Revision does not target the expected earlier finding.")
            steps.append(report)
            if issues:
                break
            results[event.event_id] = result
            events.append(event)
            if finding is not None:
                findings.append(finding)
        passed = len(steps) == len(case["steps"]) and all(not step["issues"] for step in steps)
        reports.append({
            "case_id": case["case_id"], "automatic_checks_passed": passed,
            "steps": steps, "unprocessed_steps": len(case["steps"]) - len(steps),
            "semantic_review_status": "pending", "review_questions": case["review_questions"],
        })
    return {
        "synthetic": True,
        "evaluation_kind": "reference_self_check" if isinstance(adapter, ReferenceAdapter) else "adapter_evaluation",
        "model_quality_verified": False,
        "note": "Automatic checks do not establish semantic correctness. Review each statement against its sources.",
        "case_count": len(reports),
        "automatic_checks_passed": sum(report["automatic_checks_passed"] for report in reports),
        "cases": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, action="store_true",
                        help="Check hand-authored examples; does not evaluate a real model.")
    args = parser.parse_args()
    cases = load_cases()
    report = evaluate(ReferenceAdapter(cases), cases=cases)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["automatic_checks_passed"] == report["case_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

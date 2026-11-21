"""Run synthetic analysis acceptance cases through any injected model adapter.

CLI reference mode checks the evaluation plumbing, not a real model's quality.
"""

import argparse
import copy
import hashlib
import json
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import Analyzer, AnalysisError, AnalysisRequest, Event, ModelAdapter, RuntimeMetadata
from .engine import _runtime

DATASET = Path(__file__).resolve().parent.parent / "fixtures" / "analysis-quality.json"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _provenance(cases: list[dict[str, Any]]) -> dict[str, Any]:
    root = DATASET.parent.parent
    dataset = json.loads(DATASET.read_text())
    revision, dirty = None, None
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL,
            text=True, timeout=5).strip()
        dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain", "--", "stopreplay_analysis", "fixtures", "tests"],
            cwd=root, stderr=subprocess.DEVNULL, text=True, timeout=5).strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return {
        "dataset_version": dataset["dataset_version"] if cases == dataset["cases"] else None,
        "dataset_scope": "bundled" if cases == dataset["cases"] else "custom_cases",
        "evaluated_cases_sha256": _digest(cases),
        "code_revision": revision, "evaluation_files_dirty": dirty,
        "python_sources_sha256": _digest({p.name: p.read_text() for p in
                                          sorted((root / "stopreplay_analysis").glob("*.py"))}),
    }


def save_report(report: dict[str, Any], path: str | Path) -> None:
    """Save a complete JSON report, refusing to overwrite a previous run."""
    serialized = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(serialized)


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
    cases = copy.deepcopy(cases)
    if not cases or any(not case["steps"] for case in cases):
        raise ValueError("Evaluation requires nonempty cases and steps.")
    if len({case["case_id"] for case in cases}) != len(cases):
        raise ValueError("Evaluation case IDs must be unique.")
    provenance = _provenance(cases)
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        runtime = asdict(_runtime(adapter))
        runtime["parameters"] = json.loads(runtime.pop("parameters_json"))
    except AnalysisError:
        runtime = None
    reports = []
    for case in cases:
        events, findings, results = [], [], {}
        steps = []
        for step in case["steps"]:
            raw_event = step["event"]
            report = {"event_id": raw_event.get("event_id") if isinstance(raw_event, dict) else None,
                      "issues": [], "result": None}
            try:
                event = Event.from_dict(step["event"])
                result = Analyzer(adapter).analyze_incremental(
                    event, analysis_id="evaluation-v1", previous_events=events, previous_findings=findings)
            except AnalysisError as error:
                report["issues"].append(error.to_dict())
                steps.append(report)
                break
            # Reports use JSON arrays, while the in-memory analysis contract keeps tuples.
            report["result"] = json.loads(json.dumps(result.to_dict(), allow_nan=False))
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
            "input_events": [step["event"] for step in case["steps"]],
            "steps": steps, "unprocessed_steps": len(case["steps"]) - len(steps),
            "semantic_review_status": "pending", "review_questions": case["review_questions"],
        })
    return {
        "report_version": "analysis-evaluation-v2",
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance,
        "configured_runtime": runtime,
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
    parser.add_argument("--output", type=Path, help="Save JSON to a new file; existing files are never overwritten.")
    args = parser.parse_args()
    cases = load_cases()
    report = evaluate(ReferenceAdapter(cases), cases=cases)
    if args.output is not None:
        try:
            save_report(report, args.output)
        except OSError:
            parser.exit(2, "Could not save report: use a new file in an existing writable directory.\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["automatic_checks_passed"] == report["case_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

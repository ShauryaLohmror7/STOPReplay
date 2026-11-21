"""Pure analysis orchestration and evidence validation. No I/O or persistence."""

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .models import (
    AnalysisError, AnalysisRequest, AnalysisResult, Citation, Event, Finding,
    ModelAdapter, ModelRefusal, RuntimeMetadata, SCHEMA_VERSION,
)


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise AnalysisError(code, message)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _finding_id(event: Event, analysis_id: str, finding_index: int = 0) -> str:
    identity = json.dumps([SCHEMA_VERSION, event.run_id, analysis_id,
                           event.event_id, finding_index], separators=(",", ":"))
    return "f_" + hashlib.sha256(identity.encode()).hexdigest()


def _validate_evidence(finding: Finding, events: Mapping[str, Event]) -> None:
    _require(isinstance(finding.evidence, tuple) and bool(finding.evidence),
             "invalid_evidence", "A finding needs an immutable tuple of evidence.")
    seen = set()
    for citation in finding.evidence:
        _require(isinstance(citation, Citation), "invalid_evidence", "Malformed citation.")
        _require(_text(citation.event_id), "invalid_evidence", "Missing citation event ID.")
        event = events.get(citation.event_id)
        _require(event is not None, "invalid_evidence", "Citation does not resolve in this context.")
        _require(event.run_id == finding.run_id, "invalid_evidence", "Citation belongs to another run.")
        _require(event.sequence <= finding.sequence, "invalid_evidence", "Citation uses future evidence.")
        _require(citation.source_ref == event.source_ref, "invalid_evidence", "Citation source does not match event.")
        _require(_text(citation.quote) and citation.quote in event.text,
                 "invalid_evidence", "Citation quote must occur verbatim in its event text.")
        key = (citation.event_id, citation.source_ref, citation.quote)
        _require(key not in seen, "invalid_evidence", "Repeated citation.")
        seen.add(key)


def _validate_finding(finding: Finding) -> None:
    _require(isinstance(finding, Finding), "invalid_input", "History must contain Finding objects.")
    _require(all(_text(getattr(finding, key)) for key in
                 ("finding_id", "run_id", "analysis_id", "statement")),
             "invalid_output", "Finding identity and statement must be nonempty strings.")
    _require(type(finding.sequence) is int and finding.sequence > 0,
             "invalid_output", "Finding sequence must be a positive integer.")
    _require(type(finding.finding_index) is int and finding.finding_index == 0,
             "invalid_output", "Finding index must be integer zero in v1.")
    _require(finding.kind in ("observation", "inference"), "invalid_output", "Invalid finding kind.")
    _require(finding.status in ("supported", "unresolved"), "invalid_output", "Invalid finding status.")
    _require(finding.uncertainty is None or _text(finding.uncertainty),
             "invalid_output", "Uncertainty must be null or a nonempty explanation.")
    _require(finding.revises is None or _text(finding.revises),
             "invalid_revision", "Revision target must be null or a finding ID.")
    if finding.kind == "inference" or finding.status == "unresolved":
        _require(_text(finding.uncertainty), "invalid_output", "Inferences and conflicts need an uncertainty explanation.")


def _validate_context(request: AnalysisRequest) -> dict[str, Event]:
    request.event.validate()
    _require(_text(request.analysis_id), "invalid_input", "A caller-assigned analysis_id is required.")
    events: dict[str, Event] = {}
    sequences = set()
    for event in request.previous_events:
        _require(isinstance(event, Event), "invalid_input", "Context must contain Event objects.")
        event.validate()
        _require(event.run_id == request.event.run_id, "invalid_input", "Context contains another run.")
        _require(event.sequence <= request.event.sequence, "invalid_input", "Context contains future evidence.")
        _require(event.event_id not in events and event.sequence not in sequences,
                 "invalid_input", "Context must have unique event IDs and sequences.")
        events[event.event_id] = event
        sequences.add(event.sequence)
    existing = events.get(request.event.event_id)
    if existing is not None:
        _require(existing == request.event, "event_conflict", "Same event ID has different content.")
    else:
        _require(all(e.sequence < request.event.sequence for e in events.values()),
                 "invalid_input", "Incremental analysis requires strictly increasing sequence.")

    findings: dict[str, Finding] = {}
    events_by_sequence = {event.sequence: event for event in events.values()}
    revised = set()
    for finding in request.previous_findings:
        _validate_finding(finding)
        _require(finding.run_id == request.event.run_id and finding.analysis_id == request.analysis_id,
                 "invalid_input", "Finding history belongs to another run or analysis version.")
        _require(finding.finding_id not in findings, "invalid_input", "Duplicate finding ID in history.")
        _require(finding.sequence in sequences, "invalid_input", "Finding history has no event at its sequence.")
        _validate_evidence(finding, events)
        trigger = events_by_sequence[finding.sequence]
        _require(finding.finding_id == _finding_id(trigger, request.analysis_id, finding.finding_index),
                 "invalid_input", "History finding ID does not match its event and analysis identity.")
        _require(trigger.event_id in {citation.event_id for citation in finding.evidence},
                 "invalid_evidence", "History finding must cite its triggering event.")
        if finding.status == "unresolved":
            _require(finding.revises is None and len({c.event_id for c in finding.evidence}) >= 2,
                     "invalid_evidence", "Unresolved history needs both sides and cannot revise a finding.")
        if finding.revises is not None:
            target = findings.get(finding.revises)
            _require(target is not None and target.sequence < finding.sequence,
                     "invalid_revision", "History must include earlier revision targets in order.")
            _require(finding.revises not in revised, "invalid_revision", "History branches an already revised finding.")
            revised.add(finding.revises)
        findings[finding.finding_id] = finding
    return events


def _runtime(adapter: ModelAdapter) -> RuntimeMetadata:
    def reject_constant(value: str) -> None:
        raise ValueError("Nonstandard JSON constant")

    try:
        metadata = adapter.metadata
        valid = isinstance(metadata, RuntimeMetadata) and all(
            _text(getattr(metadata, key)) for key in ("provider", "model_version", "prompt_version"))
        parameters = json.loads(metadata.parameters_json, parse_constant=reject_constant)
        # Reject nonstandard NaN/Infinity too, including nested values.
        canonical = json.dumps(parameters, allow_nan=False, sort_keys=True)
        valid = valid and isinstance(parameters, dict)
    except (AttributeError, TypeError, ValueError):
        valid = False
    _require(valid, "invalid_config", "Adapter needs versioned runtime metadata and JSON object parameters.")
    return RuntimeMetadata(metadata.provider, metadata.model_version, metadata.prompt_version, canonical)


def _decode(raw: Any, request: AnalysisRequest, events: dict[str, Event],
            runtime: RuntimeMetadata) -> AnalysisResult:
    _require(isinstance(raw, Mapping) and set(raw) == {"outcome", "finding", "reason"},
             "invalid_output", "Model output must contain outcome, finding, and reason only.")
    outcome, payload, reason = raw["outcome"], raw["finding"], raw["reason"]
    _require(outcome in ("new", "revision", "conflict", "no_change"), "invalid_output", "Unknown outcome.")
    _require(_text(reason), "invalid_output", "An outcome needs an explanation.")
    finding = None
    if outcome == "no_change":
        _require(payload is None, "invalid_output", "No change cannot contain a finding.")
    else:
        keys = {"statement", "kind", "evidence", "revises", "uncertainty"}
        _require(isinstance(payload, Mapping) and set(payload) == keys,
                 "invalid_output", "Malformed finding fields.")
        citations = payload["evidence"]
        _require(isinstance(citations, list) and bool(citations), "invalid_output", "Evidence must be a nonempty list.")
        for citation in citations:
            _require(isinstance(citation, Mapping) and set(citation) == {"event_id", "source_ref", "quote"},
                     "invalid_output", "Malformed citation fields.")
        evidence = tuple(Citation(**citation) for citation in citations)
        # IDs belong to the analysis layer, not the model. One finding per event in v1.
        finding = Finding(
            finding_id=_finding_id(request.event, request.analysis_id),
            finding_index=0,
            run_id=request.event.run_id, analysis_id=request.analysis_id,
            sequence=request.event.sequence, statement=payload["statement"], kind=payload["kind"],
            status="unresolved" if outcome == "conflict" else "supported",
            evidence=evidence, revises=payload["revises"], uncertainty=payload["uncertainty"],
        )
        _validate_finding(finding)
        _validate_evidence(finding, events)
        _require(request.event.event_id in {c.event_id for c in evidence},
                 "invalid_evidence", "A change must cite the current event.")
        if outcome == "revision":
            targets = {f.finding_id: f for f in request.previous_findings}
            target = targets.get(finding.revises)
            _require(target is not None and target.sequence < finding.sequence,
                     "invalid_revision", "A revision needs an earlier finding in this analysis.")
            _require(finding.revises not in {f.revises for f in request.previous_findings},
                     "invalid_revision", "A revision must target an active finding.")
        else:
            _require(finding.revises is None, "invalid_revision", "Only a revision can replace a finding.")
        if outcome == "conflict":
            _require(len({c.event_id for c in evidence}) >= 2,
                     "invalid_evidence", "An unresolved conflict needs at least two distinct events.")
    return AnalysisResult(request.event.run_id, request.analysis_id, request.event.event_id,
                          request.event.sequence, outcome, finding, reason, runtime)


class Analyzer:
    def __init__(self, adapter: ModelAdapter, *, semantic_verifier=None):
        self.adapter = adapter
        self.semantic_verifier = semantic_verifier

    def analyze_incremental(self, event: Event, *, analysis_id: str,
                            previous_events: Sequence[Event] = (),
                            previous_findings: Sequence[Finding] = ()) -> AnalysisResult:
        _require(isinstance(event, Event), "invalid_input", "Expected an Event object.")
        request = AnalysisRequest(analysis_id, event, tuple(previous_events), tuple(previous_findings))
        events = _validate_context(request)
        if event.event_id in events:
            return AnalysisResult(event.run_id, analysis_id, event.event_id, event.sequence,
                                  "no_change", None, "Identical event already processed.", None)
        runtime = _runtime(self.adapter)
        try:
            raw = self.adapter.generate(request)
        except ModelRefusal:
            raise AnalysisError("refusal", "The model declined analysis.") from None
        except TimeoutError:
            raise AnalysisError("timeout", "The model adapter timed out.") from None
        except Exception:
            # Do not expose provider response bodies or configuration in public errors.
            raise AnalysisError("provider_failure", "The model adapter failed.") from None
        events[event.event_id] = event
        result = _decode(raw, request, events, runtime)
        if self.semantic_verifier is not None:
            from .guardrails import verify_result
            verify_result(request, result, self.semantic_verifier)
        return result

    def analyze_initial(self, events: Sequence[Event], *, analysis_id: str) -> tuple[AnalysisResult, ...]:
        """Analyze one run in sequence order; collapse identical fixture deliveries.

        This in-memory helper is not a database importer or resumable controller.
        Errors abort the call; no storage is changed. Model calls may have occurred.
        """
        _require(_text(analysis_id), "invalid_input", "A caller-assigned analysis_id is required.")
        unique: dict[str, Event] = {}
        for event in events:
            _require(isinstance(event, Event), "invalid_input", "Expected Event objects.")
            event.validate()
            if event.event_id in unique:
                _require(unique[event.event_id] == event, "event_conflict", "Same event ID has different content.")
            unique[event.event_id] = event
        _require(len({e.run_id for e in unique.values()}) <= 1, "invalid_input", "Initial analysis accepts one run.")
        _require(len({e.sequence for e in unique.values()}) == len(unique),
                 "invalid_input", "Different events cannot share a sequence.")
        previous_events: list[Event] = []
        findings: list[Finding] = []
        results = []
        for event in sorted(unique.values(), key=lambda e: e.sequence):
            result = self.analyze_incremental(event, analysis_id=analysis_id,
                                              previous_events=previous_events, previous_findings=findings)
            results.append(result)
            previous_events.append(event)
            if result.finding is not None:
                findings.append(result.finding)
        return tuple(results)

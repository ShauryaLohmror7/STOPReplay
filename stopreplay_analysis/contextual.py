"""Evidence-backed, read-only analysis projections; separate from storage v1.1.

Inputs are explicit structured annotations, not arbitrary personality inferences.
Semantic review is injected trusted code; unchecked annotations remain candidates.
"""

import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Callable

from .guardrails import SemanticVerdict
from .models import AnalysisError, Citation, Event
from .outcomes import OutcomeBatch

PROFILE_PREDICATES = frozenset({"role", "organization", "project", "talk", "co_presenter",
                               "colleague", "uses_tool", "event_registration"})
RELATION_PREDICATES = frozenset({"co_presenter", "colleague"})


def _require(condition, message):
    if not condition:
        raise AnalysisError("invalid_input", message)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _time(value):
    _require(isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None,
             "Use timezone-aware timestamps.")
    return value


def _events(events, run_id, as_of_sequence):
    _require(_text(run_id) and type(as_of_sequence) is int and as_of_sequence > 0, "Invalid view scope.")
    result, sequences = {}, set()
    for event in events:
        _require(isinstance(event, Event), "Expected normalized events.")
        event.validate()
        _require(event.run_id == run_id, "Events must belong to the requested run.")
        if event.event_id in result:
            _require(result[event.event_id] == event, "Conflicting event identity.")
            continue
        _require(event.sequence not in sequences, "Ambiguous event sequence.")
        sequences.add(event.sequence)
        result[event.event_id] = event
    # Callers hide records whose evidence is later than the view; they do not fail.
    return result


def _evidence(citation, events):
    _require(isinstance(citation, Citation), "Expected a citation.")
    _require(_text(citation.event_id), "Citation needs an event ID.")
    event = events.get(citation.event_id)
    _require(event is not None, "Citation does not resolve in this run.")
    _require(citation.source_ref == event.source_ref and _text(citation.quote)
             and citation.quote in event.text, "Citation must match its preserved event text.")
    return event


def _review(record, event, verifier):
    if verifier is None:
        return "pending"
    try:
        verdict = verifier(record, event)
    except Exception:
        return "verification_failed"
    if not isinstance(verdict, SemanticVerdict) or not _text(verdict.explanation):
        return "verification_failed"
    return "supported" if verdict.supported is True else "unsupported"


@dataclass(frozen=True)
class ProfileFact:
    fact_id: str
    subject: str
    predicate: str
    value: str
    evidence: Citation
    # Time of the underlying source fact, not the crawler's retrieval time.
    source_date: datetime | None = None
    kind: str = "observation"
    supersedes: str | None = None


def analyze_profiles(facts, events, *, run_id: str, as_of_sequence: int,
                     as_of_time: datetime, max_age_days: dict[str, int],
                     verifier: Callable | None = None) -> dict:
    """Build candidate profiles, explicit relationship edges, and claim eligibility.

    `eligible_with_attribution` is never permission to assert independently verified
    truth. Unknown freshness, inference, unresolved conflict or pending review blocks it.
    """
    now = _time(as_of_time)
    _require(isinstance(max_age_days, dict) and all(key in PROFILE_PREDICATES
             and type(value) is int and value >= 0 for key, value in max_age_days.items()),
             "Freshness policy must give nonnegative days for known predicates.")
    run_events = _events(events, run_id, as_of_sequence)
    rows, seen, ids = [], {}, set()
    for fact in facts:
        _require(isinstance(fact, ProfileFact), "Expected profile facts.")
        _require(all(_text(value) for value in (fact.fact_id, fact.subject, fact.value)), "Invalid profile fact.")
        _require(fact.predicate in PROFILE_PREDICATES, "Unsupported profile category.")
        _require(fact.kind in ("observation", "inference"), "Invalid fact kind.")
        event = _evidence(fact.evidence, run_events)
        _require(fact.fact_id not in ids, "Duplicate fact identity.")
        ids.add(fact.fact_id)
        if event.sequence > as_of_sequence:
            continue
        review = _review(fact, event, verifier)
        age = None
        if fact.source_date is None:
            freshness = "unknown"
        else:
            date = _time(fact.source_date)
            age = (now - date).total_seconds() / 86400
            freshness = ("future_source_date" if date > now else "unknown_policy"
                         if fact.predicate not in max_age_days else "fresh"
                         if now - date <= timedelta(days=max_age_days[fact.predicate]) else "stale")
        row = {"fact_id": fact.fact_id, "subject": fact.subject, "predicate": fact.predicate,
               "value": fact.value, "kind": fact.kind, "sequence": event.sequence,
               "evidence": asdict(fact.evidence), "source_date": fact.source_date.isoformat() if fact.source_date else None,
               "freshness": freshness, "age_days": age, "semantic_review": review,
               "supersedes": fact.supersedes, "superseded": False, "conflicting_fact_ids": []}
        seen[fact.fact_id] = row
        rows.append(row)
    # A newer record does not supersede an older one just because it arrived later.
    replaced = set()
    for row in rows:
        if row["supersedes"] is not None:
            target = seen.get(row["supersedes"])
            _require(target is not None and target["sequence"] < row["sequence"]
                     and (target["subject"], target["predicate"]) == (row["subject"], row["predicate"]),
                     "Fact revision needs an earlier matching target.")
            _require(row["supersedes"] not in replaced, "A fact cannot be revised twice.")
            if row["semantic_review"] == "supported":
                target["superseded"] = True
                replaced.add(row["supersedes"])
    grouped = defaultdict(list)
    for row in rows:
        if not row["superseded"]:
            grouped[(row["subject"], row["predicate"])].append(row)
    # Multiple projects/colleagues can coexist. Only role/organization/tool slots are
    # compared as potential disagreements, not automatically declared contradictions.
    for (_, predicate), group in grouped.items():
        if predicate in {"role", "organization", "uses_tool"}:
            for row in group:
                row["conflicting_fact_ids"] = [other["fact_id"] for other in group
                                                if other["value"] != row["value"]
                                                and other["semantic_review"] != "unsupported"]
    profiles, edges = defaultdict(list), []
    for row in rows:
        reasons = []
        if row["semantic_review"] != "supported": reasons.append("semantic_support_not_verified")
        if row["freshness"] != "fresh": reasons.append("freshness_not_established")
        if row["kind"] != "observation": reasons.append("inference_requires_qualification")
        if row["superseded"]: reasons.append("superseded")
        if row["conflicting_fact_ids"]: reasons.append("possible_conflicting_claims")
        row["assertability"] = "blocked" if reasons else "eligible_with_attribution"
        row["blocking_reasons"] = reasons
        profiles[row["subject"]].append(row)
        if row["predicate"] in RELATION_PREDICATES and not row["superseded"]:
            edges.append({"from": row["subject"], "to": row["value"], "relationship": row["predicate"],
                          "fact_id": row["fact_id"], "semantic_review": row["semantic_review"],
                          "freshness": row["freshness"], "evidence": row["evidence"]})
    return {"schema_version": "analysis-context-proposal-v1", "run_id": run_id,
            "as_of_sequence": as_of_sequence, "as_of_time": now.isoformat(),
            "freshness_policy_days": dict(max_age_days), "profiles": dict(profiles), "relationships": edges}


@dataclass(frozen=True)
class MethodUse:
    contact_id: str
    session_id: str
    family: str
    evidence: Citation


def cluster_methods(methods, events, *, run_id: str, session_id: str,
                    as_of_sequence: int, similarity_threshold: float = 0.8) -> dict:
    """Group declared method families and flag lexical repetition; never recommend a tactic."""
    _require(_text(session_id), "Session ID is required.")
    _require(type(similarity_threshold) in (int, float) and 0 < similarity_threshold <= 1,
             "Similarity threshold must be in (0, 1].")
    run_events = _events(events, run_id, as_of_sequence)
    groups, records, seen = defaultdict(list), [], set()
    for method in methods:
        _require(isinstance(method, MethodUse) and method.session_id == session_id,
                 "Method history must belong to this session.")
        _require(_text(method.contact_id) and _text(method.family), "Invalid method annotation.")
        _require(method.contact_id not in seen, "Duplicate contact annotation.")
        event = _evidence(method.evidence, run_events)
        seen.add(method.contact_id)
        if event.sequence > as_of_sequence:
            continue
        family = " ".join(method.family.casefold().split())
        groups[family].append(method.contact_id)
        tokens = set(re.findall(r"\w+", method.evidence.quote.casefold()))
        records.append((method, tokens, event.sequence))
    similar = []
    for index, (left, left_tokens, _) in enumerate(records):
        for right, right_tokens, _ in records[index + 1:]:
            score = len(left_tokens & right_tokens) / len(left_tokens | right_tokens) if left_tokens | right_tokens else 0
            if score >= similarity_threshold:
                similar.append({"contact_ids": [left.contact_id, right.contact_id], "lexical_similarity": score})
    return {"run_id": run_id, "session_id": session_id, "as_of_sequence": as_of_sequence,
            "declared_family_clusters": dict(groups), "similar_contacts": similar,
            "method": "declared labels plus token Jaccard; not semantic equivalence or effectiveness",
            "records": [{"contact_id": item.contact_id, "family": item.family,
                         "sequence": sequence, "evidence": asdict(item.evidence)} for item, _, sequence in records]}


@dataclass(frozen=True)
class SessionStatement:
    statement_id: str
    session_id: str
    category: str
    subject: str
    key: str
    value: str
    evidence: Citation
    supersedes: str | None = None


def track_session(statements, events, *, run_id: str, session_id: str,
                  as_of_sequence: int, verifier: Callable | None = None) -> dict:
    """Track explicit sender claims/commitments and flag possible inconsistencies."""
    _require(_text(session_id), "Session ID is required.")
    run_events = _events(events, run_id, as_of_sequence)
    rows, seen, ids, replaced = [], {}, set(), set()
    for item in statements:
        _require(isinstance(item, SessionStatement) and item.session_id == session_id,
                 "Statement belongs to another session.")
        _require(item.category in {"identity", "claim", "commitment"}
                 and all(_text(v) for v in (item.statement_id, item.subject, item.key, item.value)),
                 "Invalid session statement.")
        event = _evidence(item.evidence, run_events)
        _require(item.statement_id not in ids, "Duplicate statement identity.")
        ids.add(item.statement_id)
        if event.sequence > as_of_sequence:
            continue
        row = {**asdict(item), "sequence": event.sequence, "semantic_review": _review(item, event, verifier)}
        seen[item.statement_id] = row
        rows.append(row)
    for row in rows:
        if row["supersedes"] is not None:
            target = seen.get(row["supersedes"])
            _require(target is not None and target["sequence"] < row["sequence"]
                     and all(row[key] == target[key] for key in ("category", "subject", "key")),
                     "Statement revision requires an earlier matching target.")
            if row["semantic_review"] == "supported":
                _require(row["supersedes"] not in replaced, "Statement was already revised.")
                replaced.add(row["supersedes"])
    active = [row for row in rows if row["statement_id"] not in replaced]
    groups = defaultdict(list)
    for row in active:
        groups[(row["category"], row["subject"], row["key"])].append(row)
    conflicts = [{"category": key[0], "subject": key[1], "key": key[2],
                  "statement_ids": [r["statement_id"] for r in group], "status": "possible_inconsistency"}
                 for key, group in groups.items() if len({r["value"] for r in group}) > 1]
    return {"run_id": run_id, "session_id": session_id, "as_of_sequence": as_of_sequence,
            "history": rows, "active_statements": active, "possible_inconsistencies": conflicts,
            "note": "Recorded claims are not verified identities or fulfilled commitments. No cross-session carryover."}


def summarize_engagement(batch: OutcomeBatch, contacts: dict[str, dict], *,
                         available_sequences: dict[str, int], as_of_sequence: int) -> dict:
    """Count authenticated observations by explicit contact link, without inferring interest."""
    _require(isinstance(batch, OutcomeBatch) and isinstance(contacts, dict)
             and isinstance(available_sequences, dict) and type(as_of_sequence) is int and as_of_sequence > 0,
             "Invalid engagement input.")
    summary = {}
    for contact_id, metadata in contacts.items():
        _require(_text(contact_id) and isinstance(metadata, dict)
                 and metadata.get("session_id") == batch.session_id
                 and type(metadata.get("sequence")) is int and metadata["sequence"] > 0,
                 "Contact metadata needs this session and an availability sequence.")
        if metadata["sequence"] <= as_of_sequence:
            summary[contact_id] = {"counts": {}, "event_ids": [], "reply_word_count": 0,
                                   "topic": metadata.get("topic"), "topic_interest": None,
                                   "status": "no_observed_activity"}
    excluded, unassigned = [], []
    for outcome in batch.outcomes:
        sequence = available_sequences.get(outcome.event_id)
        _require(type(sequence) is int and sequence > 0, "Every outcome needs an availability sequence.")
        if sequence > as_of_sequence:
            continue
        if batch.verification != "authenticated_api" or outcome.verification != "authenticated_api":
            excluded.append(outcome.event_id)
            continue
        if outcome.contact_id not in summary:
            unassigned.append(outcome.event_id)
            continue
        _require(contacts[outcome.contact_id]["sequence"] <= sequence, "Outcome precedes its contact.")
        row = summary[outcome.contact_id]
        row["counts"][outcome.event_type] = row["counts"].get(outcome.event_type, 0) + 1
        row["event_ids"].append(outcome.event_id)
        row["reply_word_count"] += len(outcome.reply_text.split()) if outcome.reply_text else 0
        row["status"] = "observed_activity"
    return {"session_id": batch.session_id, "as_of_sequence": as_of_sequence, "contacts": summary,
            "excluded_unverified_event_ids": excluded, "unassigned_event_ids": unassigned,
            "note": "Counts/length are observations, not interest, trust, sentiment, hook effectiveness or a pivot recommendation."}

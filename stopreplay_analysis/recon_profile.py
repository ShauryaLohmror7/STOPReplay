"""Bridge Cem's recon `facts` rows into a provenance-resolved profile view.

This is NOT `analyze_profiles`. That function validates verbatim quotes against the
event stream; recon facts have no event and no quote span. They are already an
extraction that carries collection's own `assertable`/`confidence`/`sensitivity`
judgment. This bridge therefore PRESERVES that judgment rather than re-deriving it,
resolves each fact's source for attribution, and separates what may be used with
attribution from restricted material. It invents no quote and asserts no verified
truth: a public-source attribution is not independent verification.

Input rows are the dicts `stopreplay_db.Storage.get_facts` returns; `sources` maps
`source_ref` to the dict `get_source` returns. Both stay plain data so this module
needs no database. Pre-run recon uses source_run "recon".
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from .models import AnalysisError

SCHEMA_VERSION = "analysis-recon-proposal-v1"

# Mirrors the collection layer's CHECK constraints (stopreplay_collect/models.py).
CATEGORIES = {"role", "event", "project", "relationship", "interest",
              "contact", "credential", "other"}
# Facts at or above this sensitivity, and any credential fact, are never surfaced
# as usable here; they are collection's authorization gate, not analysis's to open.
RESTRICTED_SENSITIVITY = {"sensitive", "private"}
_SOURCE_FIELDS = ("source_ref", "url", "locator", "origin", "publisher", "excerpt")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AnalysisError("invalid_input", message)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _split_key(claim: str) -> tuple[str | None, str]:
    """Collection stores machine-findable attributes as `key: value`; prose facts
    (a role description) have no key. Only split on the first ': ' and only when the
    key is a bare token, so a sentence with a colon is left as its own value."""
    head, sep, tail = claim.partition(": ")
    if sep and head and tail.strip() and " " not in head.strip():
        return head.strip(), tail.strip()
    return None, claim.strip()


def _provenance(source_ref: str, sources: Mapping[str, Mapping[str, Any]]) -> dict:
    source = sources.get(source_ref)
    if source is None:
        # The fact is kept, but attribution is incomplete until the source resolves.
        return {"source_ref": source_ref, "resolved": False}
    row = {field: source.get(field) for field in _SOURCE_FIELDS}
    row["source_ref"] = source_ref
    row["resolved"] = True
    return row


def project_recon_facts(facts: Sequence[Mapping[str, Any]],
                        sources: Mapping[str, Mapping[str, Any]] | None = None, *,
                        source_run: str, subject: str | None = None) -> dict:
    """Group recon facts per subject with resolved provenance and collection's own
    assertability. A fact is `usable_with_attribution` only when collection marked it
    assertable, its status is active, and it is not restricted; everything else is
    reported with a reason, never silently dropped."""
    _require(_text(source_run), "A source_run is required.")
    sources = sources or {}
    _require(isinstance(sources, Mapping), "Sources must be a mapping of source_ref to row.")

    subjects: dict[str, dict] = {}
    seen: set = set()
    for fact in facts:
        _require(isinstance(fact, Mapping), "Expected fact row mappings.")
        fact_id = fact.get("id")
        _require(fact_id is not None and fact_id not in seen, "Facts need unique ids.")
        seen.add(fact_id)
        _require(fact.get("source_run") == source_run, "Fact belongs to another run.")
        _require(_text(fact.get("subject")) and _text(fact.get("claim")), "Malformed fact row.")
        _require(fact.get("category") in CATEGORIES, "Unsupported fact category.")
        _require(_text(fact.get("source_ref")), "Fact must cite a source_ref.")
        if subject is not None and fact["subject"] != subject:
            continue

        key, value = _split_key(fact["claim"])
        sensitivity = fact.get("sensitivity")
        restricted_reason = ("credential_category" if fact["category"] == "credential"
                             else "restricted_sensitivity" if sensitivity in RESTRICTED_SENSITIVITY
                             else None)
        provenance = _provenance(fact["source_ref"], sources)
        reasons = []
        if restricted_reason:
            reasons.append(restricted_reason)
        if fact.get("assertable") is not True:
            reasons.append("collection_not_assertable")
        if fact.get("status") != "active":
            reasons.append(f"status_{fact.get('status')}")
        if not provenance["resolved"]:
            reasons.append("source_unresolved")

        row = {
            "fact_id": fact_id, "category": fact["category"], "key": key, "value": value,
            "claim": fact["claim"], "assertable": fact.get("assertable"),
            "assertable_why": fact.get("assertable_why"), "confidence": fact.get("confidence"),
            "sensitivity": sensitivity, "status": fact.get("status"),
            "corroboration_count": len(fact.get("corroboration") or []),
            "source": provenance,
            "usable_with_attribution": not reasons,
            "withheld_reasons": reasons,
        }
        bucket = subjects.setdefault(fact["subject"], {
            "identity": {}, "attributes": [], "restricted": [], "usable_with_attribution": []})
        if restricted_reason:
            bucket["restricted"].append(row)
        elif key is not None:
            # Machine-findable identity attributes (full_name, *_profile, company_domain).
            bucket["identity"].setdefault(key, []).append(row)
        else:
            bucket["attributes"].append(row)
        if row["usable_with_attribution"]:
            bucket["usable_with_attribution"].append(row)

    return {"schema_version": SCHEMA_VERSION, "source_run": source_run,
            "subject_filter": subject, "subjects": subjects,
            "note": ("Attribution to a public source is not independent verification. "
                     "Restricted and non-assertable facts are reported, not forwarded as usable.")}

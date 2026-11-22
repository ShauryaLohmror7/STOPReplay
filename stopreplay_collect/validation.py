"""Validation and the central collection guardrails.

These run in the pipeline before anything is persisted, so every adapter is held
to the same rules regardless of its source. The sensitivity gate enforces the
brief: sensitive/private fields and credential facts are only accepted when the
request is explicitly marked as synthetic, organiser-authorised data.
"""
from __future__ import annotations

from .models import (
    CATEGORIES,
    FACT_STATUSES,
    RESTRICTED_SENSITIVITY,
    SENSITIVITIES,
    SOURCE_ORIGINS,
    DraftFact,
    DraftSource,
    ResearchRequest,
)


def validate_source(source: DraftSource) -> list[str]:
    errors: list[str] = []
    if not source.source_ref:
        errors.append("source_ref is required")
    if source.origin not in SOURCE_ORIGINS:
        errors.append(f"invalid origin {source.origin!r}")
    if source.origin == "inferred" and not source.locator:
        errors.append("an inferred source must name its underlying evidence in locator")
    if not (source.excerpt or source.file_ref):
        errors.append("a source must preserve an excerpt or a file_ref")
    return errors


def validate_fact(fact: DraftFact, request: ResearchRequest) -> list[str]:
    errors: list[str] = []
    if not fact.subject:
        errors.append("subject is required")
    if not fact.claim:
        errors.append("claim is required")
    if not fact.source_ref:
        errors.append("source_ref is required")
    if fact.category not in CATEGORIES:
        errors.append(f"invalid category {fact.category!r}")
    if fact.sensitivity not in SENSITIVITIES:
        errors.append(f"invalid sensitivity {fact.sensitivity!r}")
    if fact.status not in FACT_STATUSES:
        errors.append(f"invalid status {fact.status!r}")
    if fact.confidence is not None and not (0.0 <= fact.confidence <= 1.0):
        errors.append("confidence must be between 0 and 1")

    # Guardrail: restricted material requires explicit synthetic authorisation.
    restricted = fact.sensitivity in RESTRICTED_SENSITIVITY or fact.category == "credential"
    if restricted and not request.synthetic_authorized:
        errors.append(
            "sensitive/private/credential facts require an explicitly "
            "synthetic_authorized request"
        )
    return errors

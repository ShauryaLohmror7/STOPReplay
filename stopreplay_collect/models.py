"""Shared collection types: the research request, draft source/fact records an
adapter emits, the adapter's raw output, and the structured import report.

Draft records are the universal structure every adapter produces. The pipeline
(not the adapter) registers sources and persists facts, so guardrails and
reporting are enforced in one place.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

# Enum sets mirror the database CHECK constraints.
CATEGORIES = {"role", "event", "project", "relationship", "interest",
              "contact", "credential", "other"}
SENSITIVITIES = {"public", "semi_public", "sensitive", "private"}
FACT_STATUSES = {"active", "stale", "refuted", "superseded"}
SOURCE_ORIGINS = {"public_web", "public_talk", "company_site", "social_post",
                  "profile_bio", "github", "public_agenda", "file_upload",
                  "simulator_event", "inferred"}

# Facts at or above this sensitivity, and any credential fact, may only be
# persisted when the request is explicitly marked synthetic_authorized.
RESTRICTED_SENSITIVITY = {"sensitive", "private"}


@dataclass
class ResearchRequest:
    source_run: str                      # "recon" for pre-run OSINT, else run id
    subject: str                         # target id the request concerns
    query: str | None = None
    synthetic_authorized: bool = False   # gate for sensitive/private/credential
    limit: int | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class DraftSource:
    source_ref: str
    origin: str
    url: str | None = None
    file_ref: str | None = None
    publisher: str | None = None
    locator: str | None = None
    excerpt: str | None = None
    content_sha256: str | None = None    # pipeline fills from excerpt if omitted
    observed_on: date | None = None
    retrieved_on: date | None = None
    simulator_ref: dict | None = None

    def as_dict(self, run_id: str) -> dict:
        return {
            "run_id": run_id, "source_ref": self.source_ref, "origin": self.origin,
            "url": self.url, "file_ref": self.file_ref, "publisher": self.publisher,
            "locator": self.locator, "excerpt": self.excerpt,
            "content_sha256": self.content_sha256, "observed_on": self.observed_on,
            "retrieved_on": self.retrieved_on, "simulator_ref": self.simulator_ref,
        }


@dataclass
class DraftFact:
    subject: str
    claim: str
    category: str
    source_ref: str
    confidence: float | None = None
    assertable: bool | None = None
    assertable_why: str | None = None
    sensitivity: str = "public"
    corroboration: list[str] = field(default_factory=list)
    enables: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    collected_on: date | None = None
    status: str = "active"

    def as_dict(self, source_run: str) -> dict:
        return {
            "subject": self.subject, "claim": self.claim, "category": self.category,
            "source_run": source_run, "source_ref": self.source_ref,
            "confidence": self.confidence, "assertable": self.assertable,
            "assertable_why": self.assertable_why, "sensitivity": self.sensitivity,
            "corroboration": self.corroboration, "enables": self.enables,
            "entities": self.entities, "collected_on": self.collected_on,
            "status": self.status,
        }


@dataclass
class CollectionOutput:
    """What an adapter returns: drafts plus any per-record failures it hit while
    retrieving or extracting (kept separate from storage outcomes)."""
    sources: list[DraftSource] = field(default_factory=list)
    facts: list[DraftFact] = field(default_factory=list)
    retrieval_failures: list[dict] = field(default_factory=list)
    extraction_failures: list[dict] = field(default_factory=list)


@dataclass
class ImportReport:
    adapter: str
    source_run: str
    sources_registered: int = 0
    accepted: list[dict] = field(default_factory=list)
    duplicates: list[dict] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)            # validation failures
    conflicting: list[dict] = field(default_factory=list)         # source/content conflicts
    retrieval_failures: list[dict] = field(default_factory=list)
    extraction_failures: list[dict] = field(default_factory=list)
    storage_failures: list[dict] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        return {
            "sources_registered": self.sources_registered,
            "accepted": len(self.accepted),
            "duplicates": len(self.duplicates),
            "rejected": len(self.rejected),
            "conflicting": len(self.conflicting),
            "retrieval_failures": len(self.retrieval_failures),
            "extraction_failures": len(self.extraction_failures),
            "storage_failures": len(self.storage_failures),
        }

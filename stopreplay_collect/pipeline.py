"""Collection pipeline: runs an adapter, then registers sources and persists
facts through the storage interface, applying validation, the sensitivity gate,
dedup, and conflict handling uniformly. Produces one structured ImportReport.

Adapters never touch the database directly; everything goes through here.
"""
from __future__ import annotations

from stopreplay_db import SourceConflict, StorageError, content_hash
from stopreplay_db.storage import Storage

from .base import CollectionAdapter
from .models import DraftFact, ImportReport, ResearchRequest
from .validation import validate_fact, validate_source


class CollectionPipeline:
    def __init__(self, storage: Storage):
        self.storage = storage

    def run(self, adapter: CollectionAdapter, request: ResearchRequest) -> ImportReport:
        report = ImportReport(adapter=adapter.name, source_run=request.source_run)

        try:
            output = adapter.collect(request)
        except Exception as exc:  # retrieval of the whole batch failed
            report.retrieval_failures.append({"error": f"{type(exc).__name__}: {exc}"})
            return report

        report.retrieval_failures.extend(output.retrieval_failures)
        report.extraction_failures.extend(output.extraction_failures)

        registered: set[str] = set()
        for source in output.sources:
            if source.content_sha256 is None and source.excerpt is not None:
                source.content_sha256 = content_hash(source.excerpt)
            errors = validate_source(source)
            if errors:
                report.rejected.append({"source_ref": source.source_ref, "errors": errors})
                continue
            try:
                outcome = self.storage.register_source(source.as_dict(request.source_run))
                registered.add(source.source_ref)
                if outcome == "inserted":
                    report.sources_registered += 1
            except SourceConflict as exc:
                report.conflicting.append({"source_ref": source.source_ref, "error": str(exc)})
            except StorageError as exc:
                report.storage_failures.append({"source_ref": source.source_ref, "error": str(exc)})

        for fact in output.facts:
            errors = validate_fact(fact, request)
            if not self._source_resolvable(request.source_run, fact.source_ref, registered):
                errors.append(f"unresolved source_ref {fact.source_ref!r}")
            if errors:
                report.rejected.append({"subject": fact.subject, "claim": fact.claim,
                                        "errors": errors})
                continue
            if self._is_duplicate(request.source_run, fact):
                report.duplicates.append({"subject": fact.subject, "claim": fact.claim})
                continue
            try:
                fact_id = self.storage.insert_fact(fact.as_dict(request.source_run))
                report.accepted.append({"fact_id": fact_id, "subject": fact.subject,
                                        "claim": fact.claim, "source_ref": fact.source_ref})
            except StorageError as exc:
                report.storage_failures.append({"claim": fact.claim, "error": str(exc)})

        return report

    def _source_resolvable(self, source_run: str, source_ref: str,
                           registered: set[str]) -> bool:
        if source_ref in registered:
            return True
        return self.storage.get_source(source_run, source_ref) is not None

    def _is_duplicate(self, source_run: str, fact: DraftFact) -> bool:
        existing = self.storage.get_facts(source_run, subject=fact.subject,
                                          category=fact.category)
        return any(e["claim"] == fact.claim and e["source_ref"] == fact.source_ref
                   for e in existing)

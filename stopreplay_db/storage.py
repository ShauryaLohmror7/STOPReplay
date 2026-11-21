"""Server-side storage interface for STOPReplay.

All database access goes through this class. Collection adapters and the
controller call these methods; they do not touch tables directly. Mutating
operations are PL/pgSQL functions (atomic, DB-owned integrity); reads are
parameterized SELECTs. Database SQLSTATE signals become typed StorageErrors.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

import psycopg
from psycopg.types.json import Json

from .errors import translate
from .hashing import canonical_finding_hash

_SOURCE_COLS = (
    "run_id", "source_ref", "origin", "url", "file_ref", "publisher",
    "locator", "excerpt", "content_sha256", "observed_on", "retrieved_on",
    "simulator_ref",
)


class Storage:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    # -- low-level helpers ---------------------------------------------------
    def _scalar(self, sql: str, params: Sequence[Any]) -> Any:
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                return next(iter(row.values())) if row else None
        except psycopg.Error as exc:
            raise translate(exc) from None

    def _rows(self, sql: str, params: Sequence[Any]) -> list[dict]:
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        except psycopg.Error as exc:
            raise translate(exc) from None

    # -- sources -------------------------------------------------------------
    def register_source(self, source: Mapping[str, Any]) -> str:
        """'inserted' | 'exists'; raises SourceConflict on same key, new content."""
        params = [source.get(c) for c in _SOURCE_COLS]
        params[-1] = Json(source["simulator_ref"]) if source.get("simulator_ref") is not None else None
        return self._scalar(
            "select register_source(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::date,%s::date,%s::jsonb)",
            params,
        )

    def get_source(self, run_id: str, source_ref: str) -> dict | None:
        rows = self._rows(
            "select * from sources where run_id=%s and source_ref=%s",
            (run_id, source_ref),
        )
        return rows[0] if rows else None

    def get_sources(self, run_id: str) -> list[dict]:
        return self._rows(
            "select run_id, source_ref, origin, url, publisher, locator, excerpt "
            "from sources where run_id=%s order by source_ref",
            (run_id,),
        )

    # -- events --------------------------------------------------------------
    def import_event(self, event: Mapping[str, Any]) -> str:
        """'inserted' | 'duplicate'; raises EventConflict on same id, new content."""
        return self._scalar(
            "select import_event(%s,%s,%s,%s,%s,%s)",
            (event["run_id"], event["event_id"], event["sequence"],
             event["source_ref"], event["text"], event["content_hash"]),
        )

    def get_events(self, run_id: str) -> list[dict]:
        return self._rows(
            "select run_id, event_id, sequence, source_ref, text, content_hash "
            "from events where run_id=%s order by sequence, event_id",
            (run_id,),
        )

    # -- facts ---------------------------------------------------------------
    def insert_fact(self, fact: Mapping[str, Any]) -> str:
        cols = ("subject", "claim", "category", "source_run", "source_ref",
                "corroboration", "collected_on", "confidence", "assertable",
                "assertable_why", "sensitivity", "enables", "entities",
                "status", "superseded_by")
        array_cols = {"corroboration", "enables", "entities"}
        placeholders = ",".join(["%s"] * len(cols))
        params = []
        for c in cols:
            value = fact.get(c)
            if value is None and c in array_cols:
                value = []  # NOT NULL text[] columns default to empty, never NULL
            params.append(value)
        return self._scalar(
            f"insert into facts ({','.join(cols)}) values ({placeholders}) returning id",
            params,
        )

    def get_facts(self, source_run: str, subject: str | None = None,
                  category: str | None = None) -> list[dict]:
        sql = "select * from facts where source_run=%s"
        params: list[Any] = [source_run]
        if subject is not None:
            sql += " and subject=%s"
            params.append(subject)
        if category is not None:
            sql += " and category=%s"
            params.append(category)
        sql += " order by collected_on nulls last, id"
        return self._rows(sql, params)

    # -- analysis commit -----------------------------------------------------
    def current_checkpoint(self, run_id: str, analysis_id: str) -> int:
        return self._scalar(
            "select coalesce(max(turn_no),0) from turns "
            "where run_id=%s and analysis_id=%s",
            (run_id, analysis_id),
        )

    def commit_turn(self, run_id: str, analysis_id: str, turn_no: int,
                    event_id: str, result: Mapping[str, Any],
                    finding: Mapping[str, Any] | None = None,
                    expected_checkpoint: int = 0) -> dict:
        """Atomic result + finding + evidence + turn. Storage computes the
        finding's canonical_hash and preserves evidence order as ordinals."""
        p_finding = None
        if finding is not None:
            f = dict(finding)
            f.setdefault("finding_index", 0)
            f["canonical_hash"] = canonical_finding_hash(f)
            p_finding = Json(f)
        return self._scalar(
            "select commit_turn(%s::text,%s::text,%s::int,%s::text,"
            "%s::jsonb,%s::jsonb,%s::int)",
            (run_id, analysis_id, turn_no, event_id, Json(dict(result)),
             p_finding, expected_checkpoint),
        )

    # -- historical reads ----------------------------------------------------
    def _evidence_for(self, finding_ids: Sequence[str]) -> dict[str, list[dict]]:
        if not finding_ids:
            return {}
        rows = self._rows(
            "select finding_id, ordinal, event_id, source_ref, quote, "
            "quote_start, quote_end from finding_evidence "
            "where finding_id = any(%s) order by finding_id, ordinal",
            (list(finding_ids),),
        )
        out: dict[str, list[dict]] = {}
        for r in rows:
            out.setdefault(r["finding_id"], []).append({
                "event_id": r["event_id"], "source_ref": r["source_ref"],
                "quote": r["quote"], "quote_start": r["quote_start"],
                "quote_end": r["quote_end"],
            })
        return out

    def _attach_evidence(self, findings: list[dict]) -> list[dict]:
        ev = self._evidence_for([f["finding_id"] for f in findings])
        for f in findings:
            f["evidence"] = ev.get(f["finding_id"], [])
        return findings

    def get_analysis_context(self, run_id: str, analysis_id: str,
                             before_sequence: int) -> dict:
        """Earlier events and findings (including superseded) that analysis of a
        new event at `before_sequence` may use. no_change results add no finding."""
        events = self._rows(
            "select run_id, event_id, sequence, source_ref, text "
            "from events where run_id=%s and sequence < %s "
            "order by sequence, event_id",
            (run_id, before_sequence),
        )
        findings = self._rows(
            "select finding_id, finding_index, run_id, analysis_id, event_id, "
            "sequence, statement, kind, status, uncertainty, revises "
            "from findings where run_id=%s and analysis_id=%s and sequence < %s "
            "order by sequence, finding_index",
            (run_id, analysis_id, before_sequence),
        )
        return {
            "run_id": run_id,
            "analysis_id": analysis_id,
            "before_sequence": before_sequence,
            "events": events,
            "findings": self._attach_evidence(findings),
        }

    def get_results(self, run_id: str, analysis_id: str) -> list[dict]:
        results = self._rows(
            "select run_id, analysis_id, event_id, sequence, outcome, reason, "
            "runtime, schema_version from analysis_results "
            "where run_id=%s and analysis_id=%s order by sequence, event_id",
            (run_id, analysis_id),
        )
        findings = self._rows(
            "select finding_id, finding_index, run_id, analysis_id, event_id, "
            "sequence, statement, kind, status, uncertainty, revises "
            "from findings where run_id=%s and analysis_id=%s",
            (run_id, analysis_id),
        )
        by_event = {f["event_id"]: f for f in self._attach_evidence(findings)}
        for r in results:
            r["finding"] = by_event.get(r["event_id"])
        return results

    def get_timeline(self, run_id: str, analysis_id: str, as_of_turn: int) -> list[dict]:
        """Committed turns up to `as_of_turn`. Supersession is computed within
        this historical view only, so earlier turns never show future knowledge."""
        turns = self._rows(
            "select turn_no, event_id, finding_id, committed_at from turns "
            "where run_id=%s and analysis_id=%s and turn_no <= %s order by turn_no",
            (run_id, analysis_id, as_of_turn),
        )
        finding_ids = [t["finding_id"] for t in turns if t["finding_id"]]
        findings = {}
        if finding_ids:
            rows = self._rows(
                "select finding_id, finding_index, event_id, sequence, statement, "
                "kind, status, uncertainty, revises from findings "
                "where finding_id = any(%s)",
                (finding_ids,),
            )
            findings = {f["finding_id"]: f for f in self._attach_evidence(rows)}
        superseded = {
            f["revises"] for f in findings.values() if f.get("revises")
        }
        timeline = []
        for t in turns:
            f = findings.get(t["finding_id"]) if t["finding_id"] else None
            timeline.append({
                "turn_no": t["turn_no"],
                "event_id": t["event_id"],
                "committed_at": t["committed_at"],
                "finding": f,
                "superseded": bool(f and f["finding_id"] in superseded),
            })
        return timeline

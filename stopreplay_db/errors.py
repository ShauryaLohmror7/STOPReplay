"""Storage errors, mapped from the database's custom SQLSTATE signals.

The SQL functions raise SQLSTATE 'STC0x' codes; `translate` turns a psycopg
error carrying one of those codes into the matching typed exception so callers
never parse messages. Every error exposes a stable `.code` string.
"""
from __future__ import annotations

import psycopg


class StorageError(Exception):
    code = "storage_error"


class SourceConflict(StorageError):
    code = "source_conflict"


class EventConflict(StorageError):
    code = "event_conflict"


class HistoryConflict(StorageError):
    code = "history_conflict"


class StaleCheckpoint(StorageError):
    code = "stale_checkpoint"


class InvalidEvidence(StorageError):
    code = "invalid_evidence"


class AppendOnlyViolation(StorageError):
    code = "append_only_violation"


SQLSTATE_MAP = {
    "STC01": SourceConflict,
    "STC02": EventConflict,
    "STC03": HistoryConflict,
    "STC04": StaleCheckpoint,
    "STC05": InvalidEvidence,
    "STC06": AppendOnlyViolation,
}


def translate(exc: psycopg.Error) -> Exception:
    """Return the typed StorageError for a psycopg error, or the error itself."""
    cls = SQLSTATE_MAP.get(getattr(exc, "sqlstate", None))
    if cls is None:
        return exc
    message = str(exc).strip() or cls.code
    return cls(message)

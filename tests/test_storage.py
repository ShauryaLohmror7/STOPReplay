"""Storage-layer acceptance tests against a real Postgres.

Covers the README milestone (Room A/B) plus sources, facts, analysis results,
findings/evidence, turns, append-only, and historical reads.
"""
from __future__ import annotations

import psycopg
import pytest

from stopreplay_db import (
    EventConflict,
    HistoryConflict,
    InvalidEvidence,
    SourceConflict,
    StaleCheckpoint,
    content_hash,
    import_room_fixture,
)
from stopreplay_db.fixture import RUN_ID

ANALYSIS = "room-demo-v1"


def _runtime():
    return {"provider": "local-fake", "model_version": "room-fixture-v1",
            "prompt_version": "room-fixture-v1", "parameters": {}}


def _finding(event_id, seq, statement, source_ref, quote, revises=None, fid=None):
    return {
        "finding_id": fid or f"f_{event_id}", "run_id": RUN_ID,
        "analysis_id": ANALYSIS, "event_id": event_id, "finding_index": 0,
        "sequence": seq, "statement": statement, "kind": "observation",
        "status": "supported", "uncertainty": None, "revises": revises,
        "evidence": [{"event_id": event_id, "source_ref": source_ref, "quote": quote}],
    }


def _result(seq, outcome):
    return {"sequence": seq, "outcome": outcome, "reason": "fixture",
            "runtime": _runtime(), "schema_version": "analysis-proposal-v1.1"}


# -- sources ----------------------------------------------------------------
def test_source_idempotent_and_conflict(storage):
    src = {"run_id": RUN_ID, "source_ref": "agenda-v1", "origin": "public_agenda",
           "excerpt": "The demo is in Room A.",
           "content_sha256": content_hash("The demo is in Room A.")}
    assert storage.register_source(src) == "inserted"
    assert storage.register_source(src) == "exists"
    clash = dict(src, content_sha256=content_hash("different bytes"))
    with pytest.raises(SourceConflict):
        storage.register_source(clash)
    assert storage.get_source(RUN_ID, "agenda-v1")["excerpt"] == "The demo is in Room A."


# -- room fixture / events --------------------------------------------------
def test_room_fixture_two_events_dedup(storage):
    report = import_room_fixture(storage)
    assert report["logical_events"] == 2
    assert report["events"] == {"inserted": 2, "duplicate": 1}
    events = storage.get_events(RUN_ID)
    assert [e["event_id"] for e in events] == ["e1", "e2"]
    assert [e["sequence"] for e in events] == [1, 2]


def test_room_fixture_repeatable(storage):
    first = import_room_fixture(storage)
    second = import_room_fixture(storage)
    assert first["logical_events"] == second["logical_events"] == 2
    assert len(storage.get_events(RUN_ID)) == 2


def test_event_conflict_same_id_different_text(storage):
    import_room_fixture(storage)
    with pytest.raises(EventConflict):
        storage.import_event({
            "run_id": RUN_ID, "event_id": "e2", "sequence": 2,
            "source_ref": "agenda-v2", "text": "The demo is in Room C.",
            "content_hash": content_hash("The demo is in Room C."),
        })


# -- facts ------------------------------------------------------------------
def test_fact_insert_get_and_constraints(storage):
    import_room_fixture(storage)
    fid = storage.insert_fact({
        "subject": "julius", "claim": "Co-CEO of revel8", "category": "role",
        "source_run": RUN_ID, "source_ref": "agenda-v1", "confidence": 0.9,
        "assertable": True, "sensitivity": "public", "status": "active",
    })
    assert fid
    got = storage.get_facts(RUN_ID, subject="julius")
    assert len(got) == 1 and got[0]["category"] == "role"

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        storage.insert_fact({"subject": "x", "claim": "y", "category": "role",
                             "source_run": RUN_ID, "source_ref": "nope"})
    with pytest.raises(psycopg.errors.CheckViolation):
        storage.insert_fact({"subject": "x", "claim": "y", "category": "role",
                             "source_run": RUN_ID, "source_ref": "agenda-v1",
                             "confidence": 1.5})


# -- analysis: new + revision + timeline ------------------------------------
def test_commit_new_then_revision_with_timeline(storage):
    import_room_fixture(storage)
    storage.commit_turn(RUN_ID, ANALYSIS, 1, "e1", _result(1, "new"),
                        _finding("e1", 1, "Room A.", "agenda-v1", "The demo is in Room A."),
                        expected_checkpoint=0)
    storage.commit_turn(RUN_ID, ANALYSIS, 2, "e2", _result(2, "revision"),
                        _finding("e2", 2, "Room B.", "agenda-v2",
                                 "Correction: the demo is in Room B.", revises="f_e1"),
                        expected_checkpoint=1)

    full = storage.get_timeline(RUN_ID, ANALYSIS, as_of_turn=2)
    assert [t["superseded"] for t in full] == [True, False]

    early = storage.get_timeline(RUN_ID, ANALYSIS, as_of_turn=1)
    assert len(early) == 1 and early[0]["superseded"] is False


def test_analysis_context_hides_future(storage):
    import_room_fixture(storage)
    storage.commit_turn(RUN_ID, ANALYSIS, 1, "e1", _result(1, "new"),
                        _finding("e1", 1, "Room A.", "agenda-v1", "The demo is in Room A."),
                        expected_checkpoint=0)
    ctx = storage.get_analysis_context(RUN_ID, ANALYSIS, before_sequence=2)
    assert [e["event_id"] for e in ctx["events"]] == ["e1"]
    assert [f["finding_id"] for f in ctx["findings"]] == ["f_e1"]


# -- analysis: no_change, conflicts, checkpoint, evidence -------------------
def test_no_change_result_has_no_finding(storage):
    import_room_fixture(storage)
    storage.commit_turn(RUN_ID, ANALYSIS, 1, "e1", _result(1, "no_change"),
                        finding=None, expected_checkpoint=0)
    results = storage.get_results(RUN_ID, ANALYSIS)
    assert len(results) == 1
    assert results[0]["outcome"] == "no_change"
    assert results[0]["finding"] is None
    assert results[0]["runtime"] is not None


def test_stale_checkpoint(storage):
    import_room_fixture(storage)
    storage.commit_turn(RUN_ID, ANALYSIS, 1, "e1", _result(1, "new"),
                        _finding("e1", 1, "Room A.", "agenda-v1", "The demo is in Room A."),
                        expected_checkpoint=0)
    with pytest.raises(StaleCheckpoint):
        storage.commit_turn(RUN_ID, ANALYSIS, 2, "e2", _result(2, "revision"),
                            _finding("e2", 2, "Room B.", "agenda-v2",
                                     "Correction: the demo is in Room B.", revises="f_e1"),
                            expected_checkpoint=0)


def test_idempotent_replay_same_turn(storage):
    import_room_fixture(storage)
    args = (RUN_ID, ANALYSIS, 1, "e1", _result(1, "new"),
            _finding("e1", 1, "Room A.", "agenda-v1", "The demo is in Room A."))
    assert storage.commit_turn(*args, expected_checkpoint=0)["status"] == "committed"
    assert storage.commit_turn(*args, expected_checkpoint=0)["status"] == "already_committed"
    assert len(storage.get_timeline(RUN_ID, ANALYSIS, 9)) == 1


def test_history_conflict_same_finding_id_new_content(storage):
    import_room_fixture(storage)
    storage.commit_turn(RUN_ID, ANALYSIS, 1, "e1", _result(1, "new"),
                        _finding("e1", 1, "Room A.", "agenda-v1", "The demo is in Room A."),
                        expected_checkpoint=0)
    # reuse finding id f_e1 under a new event, different content -> history_conflict
    clash = _finding("e2", 2, "DIFFERENT.", "agenda-v2",
                     "Correction: the demo is in Room B.", fid="f_e1")
    with pytest.raises(HistoryConflict):
        storage.commit_turn(RUN_ID, ANALYSIS, 2, "e2", _result(2, "new"),
                            clash, expected_checkpoint=1)


def test_evidence_quote_must_exist(storage):
    import_room_fixture(storage)
    bad = _finding("e1", 1, "Room A.", "agenda-v1", "quote not in the event text")
    with pytest.raises(InvalidEvidence):
        storage.commit_turn(RUN_ID, ANALYSIS, 1, "e1", _result(1, "new"), bad,
                            expected_checkpoint=0)


# -- append-only ------------------------------------------------------------
def test_append_only_blocks_update(storage):
    import_room_fixture(storage)
    with pytest.raises(psycopg.Error) as ei:
        storage.conn.execute("update events set text='x' where run_id=%s", (RUN_ID,))
    assert ei.value.sqlstate == "STC06"

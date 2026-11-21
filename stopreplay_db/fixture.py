"""Room A / Room B synthetic fixture importer (README milestone).

Registers the two sources (run 'demo') then imports e1, e2 and a duplicate of
e2. This is synthetic development data for correction + dedup behaviour, not a
simulator result. It needs no revel8 Team API key and no external source.
"""
from __future__ import annotations

from typing import Any

from .hashing import content_hash
from .storage import Storage

RUN_ID = "demo"

SOURCES = [
    {
        "run_id": RUN_ID, "source_ref": "agenda-v1", "origin": "public_agenda",
        "publisher": "synthetic", "locator": "agenda v1",
        "excerpt": "The demo is in Room A.",
        "content_sha256": content_hash("The demo is in Room A."),
    },
    {
        "run_id": RUN_ID, "source_ref": "agenda-v2", "origin": "public_agenda",
        "publisher": "synthetic", "locator": "agenda v2",
        "excerpt": "Correction: the demo is in Room B.",
        "content_sha256": content_hash("Correction: the demo is in Room B."),
    },
]

DELIVERIES = [
    {"event_id": "e1", "sequence": 1, "source_ref": "agenda-v1", "text": "The demo is in Room A."},
    {"event_id": "e2", "sequence": 2, "source_ref": "agenda-v2", "text": "Correction: the demo is in Room B."},
    {"event_id": "e2", "sequence": 2, "source_ref": "agenda-v2", "text": "Correction: the demo is in Room B."},
]


def import_room_fixture(storage: Storage) -> dict[str, Any]:
    """Run the fixture and return an import report."""
    report: dict[str, Any] = {
        "sources": {"inserted": 0, "exists": 0},
        "events": {"inserted": 0, "duplicate": 0},
        "deliveries": [],
    }
    for src in SOURCES:
        outcome = storage.register_source(src)
        report["sources"][outcome] = report["sources"].get(outcome, 0) + 1

    for delivery in DELIVERIES:
        event = {
            "run_id": RUN_ID,
            "event_id": delivery["event_id"],
            "sequence": delivery["sequence"],
            "source_ref": delivery["source_ref"],
            "text": delivery["text"],
            "content_hash": content_hash(delivery["text"]),
        }
        outcome = storage.import_event(event)
        report["events"][outcome] = report["events"].get(outcome, 0) + 1
        report["deliveries"].append({"event_id": event["event_id"], "outcome": outcome})

    report["logical_events"] = len(storage.get_events(RUN_ID))
    return report

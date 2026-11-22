"""Deterministic content hashes.

- `content_hash` hashes preserved source text / event text (dedup + conflict).
- `canonical_finding_hash` hashes a finding's *content* (not its identity) so
  storage can tell an idempotent re-commit from a history conflict. The finding
  id, run, analysis and event are identity (enforced by row keys) and are
  excluded; the hashed body is the content that must not silently change.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def content_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_finding_hash(finding: Mapping[str, Any]) -> str:
    body = {
        "finding_index": finding.get("finding_index", 0),
        "sequence": finding["sequence"],
        "statement": finding["statement"],
        "kind": finding["kind"],
        "status": finding["status"],
        "uncertainty": finding.get("uncertainty"),
        "revises": finding.get("revises"),
        "evidence": [
            {
                "event_id": e["event_id"],
                "source_ref": e["source_ref"],
                "quote": e["quote"],
                "quote_start": e.get("quote_start"),
                "quote_end": e.get("quote_end"),
            }
            for e in finding.get("evidence", [])
        ],
    }
    encoded = json.dumps(body, separators=(",", ":"), sort_keys=True, ensure_ascii=True)
    return "h_" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()

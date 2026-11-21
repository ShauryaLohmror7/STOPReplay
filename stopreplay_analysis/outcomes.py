"""Read-only Target API observation mapping. No message or session mutations.

TLS and bearer authentication establish transport provenance, not semantic truth
of reply text. Recorded JSON is always unverified, even if it claims otherwise.
"""

import hashlib
import http.client
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from .models import AnalysisError

API_HOST = "target-api.apps.01.cf.eu01.stackit.cloud"
DOCS_URL = "https://" + API_HOST + "/docs.md"
REDACTED_SECRET = "(entered, not shown)"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


def _require(condition, message):
    if not condition:
        raise AnalysisError("invalid_input", message)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


@dataclass(frozen=True)
class ObservedOutcome:
    event_id: str
    session_id: str
    event_type: str
    contact_id: str | None
    contact_kind: str | None
    verification: str
    source_ref: str
    payload_sha256: str
    field_names: tuple[str, ...] = ()
    redacted_fields: tuple[str, ...] = ()
    reply_text: str | None = None
    objective_evidence: str | None = None
    official_incident: None = None


@dataclass(frozen=True)
class OutcomeBatch:
    session_id: str
    verification: str
    retrieved_at: str | None
    response_sha256: str
    outcomes: tuple[ObservedOutcome, ...]

    def to_dict(self):
        return json.loads(json.dumps(asdict(self)))


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _session(session_id):
    _require(isinstance(session_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", session_id),
             "Invalid simulator session ID.")


def _map(payload, session_id, verification, retrieved_at=None):
    _session(session_id)
    _require(isinstance(payload, dict) and isinstance(payload.get("events"), list),
             "Expected an events response object.")
    seen, outcomes = {}, []
    for event in payload["events"]:
        _require(isinstance(event, dict) and _text(event.get("id")) and _text(event.get("type")),
                 "Simulator event needs an ID and type.")
        _require(event.get("session_id", session_id) == session_id, "Event belongs to another session.")
        digest = hashlib.sha256(_canonical(event)).hexdigest()
        if event["id"] in seen:
            _require(seen[event["id"]] == digest, "Conflicting simulator event identity.")
            continue
        seen[event["id"]] = digest
        links = [(key, event[key]) for key in ("message_id", "in_reply_to", "conversation_id") if key in event]
        _require(all(_text(value) for _, value in links), "Malformed contact identity.")
        _require(len({("conversation" if key == "conversation_id" else "message", value)
                      for key, value in links}) <= 1, "Ambiguous contact identity.")
        contact_kind = ("conversation" if links[0][0] == "conversation_id" else "message") if links else None
        fields, hidden, reply, objective = (), (), None, None
        if event["type"] == "page.submitted":
            fields_value, values = event.get("fields"), event.get("values")
            _require(_text(event.get("page_id")) and isinstance(fields_value, list)
                     and all(_text(f) for f in fields_value) and len(set(fields_value)) == len(fields_value)
                     and isinstance(values, dict) and set(values) == set(fields_value)
                     and all(isinstance(v, str) for v in values.values()), "Malformed submission event.")
            fields = tuple(fields_value)
            hidden = tuple(f for f in fields if values[f] == REDACTED_SECRET)
            # Field names alone never prove a secret was entered. Preserve API redaction semantics.
            if hidden and verification == "authenticated_api":
                objective = "credentials"
        elif event["type"] == "reply":
            _require(isinstance(event.get("body"), str) and _text(event.get("channel")), "Malformed reply event.")
            reply = event["body"]
        elif event["type"] == "link.opened":
            _require(_text(event.get("url")), "Malformed link-open event.")
        # Attachment event fields beyond id/type are not specified in the docs; do not invent them.
        supported = event["type"] in {"reply", "link.opened", "page.submitted", "attachment.opened"}
        outcomes.append(ObservedOutcome(
            event["id"], session_id, event["type"], links[0][1] if links else None, contact_kind,
            verification if supported else "unmapped", f"target-api:{session_id}:{event['id']}", digest,
            fields, hidden, reply, objective))
    return OutcomeBatch(session_id, verification, retrieved_at,
                        hashlib.sha256(_canonical(payload)).hexdigest(), tuple(outcomes))


def map_recorded_events(payload: dict, *, session_id: str) -> OutcomeBatch:
    """Inspect exports/fixtures without claiming their origin is authenticated."""
    return _map(payload, session_id, "unverified_recording")


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def read_authenticated_outcomes(*, session_id: str, team_key: str, timeout: float = 30) -> OutcomeBatch:
    """GET events from the fixed HTTPS origin. No redirects, writes or retries.

    Call only from trusted server-side code. No payload flag or model response can
    select authenticated status through the public recorded-events mapper.
    """
    _session(session_id)
    _require(_text(team_key) and "\r" not in team_key and "\n" not in team_key, "Invalid API credential.")
    _require(type(timeout) in (int, float) and 0 < timeout <= 120, "Invalid read timeout.")
    connection = http.client.HTTPSConnection(API_HOST, timeout=timeout)
    try:
        connection.request("GET", f"/v1/sessions/{session_id}/events",
                           headers={"Authorization": "Bearer " + team_key, "Accept": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise AnalysisError("provider_failure", "Authenticated event read failed; no outcomes accepted.")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        _require(len(raw) <= MAX_RESPONSE_BYTES, "Event response exceeds the supported size.")
        payload = json.loads(raw, object_pairs_hook=_strict_object,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Invalid JSON constant")))
        return _map(payload, session_id, "authenticated_api", datetime.now(timezone.utc).isoformat())
    except AnalysisError:
        raise
    except Exception:
        raise AnalysisError("provider_failure", "Event read or decoding failed; no outcomes accepted.") from None
    finally:
        connection.close()

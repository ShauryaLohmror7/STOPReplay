"""Conservative event interpretation shared by execution and recorded replay.

Objective evidence is not an official incident or a score. A recording cannot
authenticate itself, even when its JSON contains a verification flag.
"""

from stopreplay_analysis.outcomes import REDACTED_SECRET


def summarize_events(events, *, trusted_transport=False, synthetic=False, session_id=None,
                     contact_id=None, contact_kind=None):
    if not isinstance(events, list):
        raise ValueError("Simulator events must be a list.")
    if contact_id is not None and (not isinstance(contact_id, str) or not contact_id.strip()
                                   or contact_kind not in {"message", "conversation"}):
        raise ValueError("A valid contact identity and kind are required.")
    observations, objectives, evidence_ids, information = [], [], [], []
    seen = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        if session_id and event.get("session_id", session_id) != session_id:
            raise ValueError("Response event belongs to a different session.")
        if contact_id is not None:
            for field, kind in (("message_id", "message"), ("in_reply_to", "message"),
                                ("conversation_id", "conversation")):
                if field in event and (kind != contact_kind or event[field] != contact_id):
                    raise ValueError("Response event belongs to a different contact.")
        event_id = event.get("id")
        if isinstance(event_id, str):
            if event_id in seen:
                if event != seen[event_id]:
                    raise ValueError("Conflicting event identity in simulator response.")
                continue
            seen[event_id] = event
        kind = event.get("type")
        objective = None
        if kind == "link.opened":
            observations.append("Link open recorded")
        elif kind == "attachment.opened":
            observations.append("Attachment open recorded")
            objective = "action"
        elif kind == "page.submitted":
            observations.append("Form submission recorded")
            fields, values = event.get("fields"), event.get("values")
            valid = (isinstance(event.get("page_id"), str) and bool(event["page_id"])
                     and isinstance(fields, list) and bool(fields)
                     and all(isinstance(f, str) for f in fields)
                     and len(fields) == len(set(fields))
                     and isinstance(values, dict) and set(fields) == set(values)
                     and all(isinstance(v, str) for v in values.values()))
            if valid and any(values[f] == REDACTED_SECRET for f in fields):
                observations.append("Secret-field submission recorded")
                if trusted_transport or synthetic:
                    objective = "credentials"
            if valid:
                basic = {"name", "email", "company", "job_title", "phone", "username"}
                for field in fields:
                    information_kind = ("redacted_secret" if values[field] == REDACTED_SECRET else
                            "basic_detail" if field.lower().replace(" ", "_") in basic else
                            "unclassified_information")
                    information.append({"event_id": event_id, "field": field, "kind": information_kind,
                                        "disclosure_established": False,
                                        "needs_publicness_review": information_kind == "unclassified_information"})
        elif kind == "reply":
            observations.append("Reply recorded; disclosure not established")
            information.append({"event_id": event_id, "kind": "unclassified_reply",
                                "disclosure_established": False, "needs_publicness_review": True})
        if objective and isinstance(event_id, str) and event_id and (trusted_transport or synthetic):
            objectives.append(objective)
            evidence_ids.append(event["id"])
    return {
        "observations": list(dict.fromkeys(observations)),
        "objective_evidence": list(dict.fromkeys(objectives)),
        "evidence_event_ids": list(dict.fromkeys(evidence_ids)),
        "verified_objective": bool(objectives) and (trusted_transport or synthetic),
        "official_incident": None,
        "information_observations": information,
        "verification": ("synthetic_fixture" if synthetic else
                         "authenticated_api" if trusted_transport else "unverified_recording"),
    }

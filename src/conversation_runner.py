"""Journal every call start/utterance before submission; one call is one touch."""
from datetime import datetime, timedelta
import json
import uuid

from src.api.target_client import TargetClient, TargetAPIError
from src.contact_validation import validate_contact
from src.run_journal import write_snapshot
from src.session_evidence import summarize_events
from src.draft_grounding import prompt_history


def run_conversation(controller, profile, hook, story, lane, state, path):
    pending = state["pending"]
    request = pending["request"]
    api = controller.api
    if not isinstance(api, TargetClient):
        raise ValueError("Conversation execution requires the simulator client.")
    if "conversation" not in pending:
        controller.progress(f"Starting {request['channel']}; waiting for simulator (120-second request timeout).")
        started = api.start_conversation(
            state["session_id"], profile.subject_id, request["channel"],
            request["sender_address"], request["sender_name"],
            sent_at=request.get("story_time"), idempotency_key=pending["idempotency_key"])
        cid = started.get("conversation_id")
        if (not isinstance(cid, str) or not cid or type(started.get("touches_used")) is not int
                or started["touches_used"] != state["touches_used"] + 1):
            raise ValueError("Invalid conversation identity or contact count.")
        pending["conversation"] = {"id": cid, "start_response": started, "dialogue": [],
                                   "utterance": None, "ended": started.get("status") != "answered"}
        write_snapshot(path, state)
    call = pending["conversation"]
    dialogue = call["dialogue"]
    while not call["ended"] and not call.get("stop_reason") and len(dialogue) < 10:
        heard = dialogue[-1]["response"].get("persona_says") if dialogue else call["start_response"].get("persona_says")
        if controller.classifier.classify("", heard) == "REJECTION":
            call["stop_reason"] = "explicit_rejection"
            break
        if call["utterance"] is None:
            sent_at = request.get("story_time")
            if sent_at:
                sent_at = (datetime.fromisoformat(sent_at) + timedelta(seconds=30 * (len(dialogue) + 1))).isoformat()
            context = json.dumps({"prior_contacts": prompt_history(state["turns"]),
                                  "conversation": [{"say": d["say"], "sent_at": d.get("sent_at"),
                                                    "response": d["response"]} for d in dialogue],
                                  "persona_says": heard, "sent_at": sent_at,
                                  "utterances_remaining": 10 - len(dialogue)}, ensure_ascii=False)
            draft = controller.drafter.draft_contact(hook, profile, turn_no=len(state["turns"]) + 1,
                                                     context=context, lane_id=lane, story=story,
                                                     source_metadata=controller.selector.source_metadata)
            if len(draft["body"]) > 4000:
                raise ValueError("Conversation utterance exceeds the API's 4000 character limit.")
            validate_contact(draft["body"], request["sender_address"], profile, hook.landing_page_url)
            call["utterance"] = {
                "say": draft["body"], "sent_at": sent_at,
                "attachments": [{"filename": draft["attachment"]}] if draft.get("attachment") else None,
                "idempotency_key": str(uuid.uuid4()), "grounding": draft.get("grounding")}
            write_snapshot(path, state)
        utterance = call["utterance"]
        controller.progress(f"Sending call utterance {len(dialogue) + 1}/10; waiting for simulator.")
        response = api.send_conversation_turn(call["id"], **{k: v for k, v in utterance.items() if k != "grounding"})
        if type(response.get("turns_used")) is not int or response["turns_used"] != len(dialogue) + 1:
            raise ValueError("Unexpected conversation turn count; reconcile saved intent.")
        if type(response.get("ended")) is not bool:
            raise ValueError("Conversation response lacks an ended flag.")
        evidence = summarize_events(response.get("events", []), trusted_transport=True,
                                    session_id=state["session_id"], contact_id=call["id"],
                                    contact_kind="conversation")
        dialogue.append({**utterance, "response": response})
        call.update(utterance=None, ended=response["ended"])
        if evidence["verified_objective"]:
            call["stop_reason"] = "objective_evidence"
        write_snapshot(path, state)
        if call.get("stop_reason"):
            break
    if not call["ended"]:
        try:
            api.end_conversation(call["id"])
        except TargetAPIError as exc:
            if exc.status_code != 409:  # An already-ended call needs no second end.
                raise
        call["ended"] = True
        write_snapshot(path, state)
    events = [e for line in dialogue for e in line["response"].get("events", [])]
    # Preserve the real conversation ID in the legacy contact identity field.
    return {"message_id": call["id"], "conversation_id": call["id"],
            "touches_used": call["start_response"]["touches_used"],
            "events": events, "event_type": "conversation",
            "reply": dialogue[-1]["response"].get("persona_says") if dialogue else call["start_response"].get("persona_says"),
            "dialogue": dialogue, "opening": call["start_response"],
            "conversation_stop": call.get("stop_reason"),
            "story_time_end": dialogue[-1]["sent_at"] if dialogue else request.get("story_time")}

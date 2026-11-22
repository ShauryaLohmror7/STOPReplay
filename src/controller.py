"""Simulator-only execution with evidence-based stopping and durable contact logs.

The local journal preserves submission intent and raw responses. It is separate
from the database's analysis history; no database schema is changed here.
"""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import os
import re
import uuid

from src.models.schemas import TargetProfile, Hook, Persona, Turn
from src.orchestrator.strategy_planner import StrategySelector, LANES_CATALOG
from src.orchestrator.drafter import MessageDrafter
from src.orchestrator.pushback_handler import ResponseClassifier
from src.api.mock_client import MockSimulatorClient
from src.api.target_client import TargetClient, TargetAPIError
from src.craft.landing_pages import build_landing_page, get_fields_for_lane
from src.craft.story import build_story
from src.run_journal import write_snapshot, journal_lock
from src.session_evidence import summarize_events
from src.contact_validation import validate_contact
from src.runtime.adapter import ModelAdapter
from src.contact_policy import (LIVE_CHANNELS, channel_plan, choose_channel,
                                timing_plan, contact_time, sender_address)
from src.draft_grounding import fact_ledger, prompt_history

LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs", "runs")


def _now():
    return datetime.now(timezone.utc).isoformat()


class RunController:
    def __init__(self, api_client=None, strategy_selector=None, drafter=None, classifier=None, event_sink=None,
                 *, channel_mode="adaptive", timing="none", story_start=None, progress=None):
        self.api = api_client or MockSimulatorClient()
        self.selector = strategy_selector or StrategySelector()
        self.drafter = drafter or MessageDrafter(
            ModelAdapter(mock_mode=True) if isinstance(self.api, MockSimulatorClient) else None)
        self.classifier = classifier or ResponseClassifier()
        self.committed_turns = []
        self.event_sink = event_sink
        self.progress = progress or (lambda message: None)
        if channel_mode not in {"adaptive", "coverage"}:
            raise ValueError("Unknown channel selection mode.")
        self.channel_mode = channel_mode
        self.timing = timing_plan(timing, story_start)

    @staticmethod
    def _reply_requests_nda(reply):
        text = (reply or "").lower().replace("’", "'")
        if re.search(r"\b(no|not|never|won't|don't|cannot|can't|refuse)\b", text):
            return False
        return bool(re.search(r"\b(nda|non-disclosure agreement)\b", text)
                    and re.search(r"\b(send|sign|fine|happy|accept|agree|please|need)\b", text))

    def execute_run(self, profile: TargetProfile, practice=True, *, resume_path=None):
        directory = os.path.dirname(os.path.abspath(resume_path)) if resume_path else LOGS_DIR
        with journal_lock(directory):
            return self._execute_run(profile, practice, resume_path=resume_path)

    def _execute_run(self, profile, practice, *, resume_path=None):
        synthetic = isinstance(self.api, MockSimulatorClient)
        mode = "mock" if synthetic else "practice" if practice else "eval"
        if not practice and synthetic:
            raise ValueError("Scoring execution cannot use a mock simulator.")
        if not practice and getattr(getattr(self.drafter, "adapter", None), "mock_mode", False):
            raise ValueError("Scoring execution requires a configured model adapter.")
        self.committed_turns = []
        if resume_path:
            with open(resume_path) as stream:
                state = json.load(stream)
            if (state.get("journal_version") != 1 or state.get("target_id") != profile.subject_id
                    or state.get("mode") != mode or synthetic):
                raise ValueError("Resume requires a matching live journal, target, and mode.")
            path = resume_path
            if not isinstance(self.api, TargetClient):
                raise ValueError("Resume requires the idempotent simulator client.")
            session = self.api.get_session(state["session_id"])
            if state["status"] == "completed":
                return self._result(state, profile)
            # A pending request may have landed. Only its identical body/key may
            # be resubmitted. Other count drift requires read-only reconciliation.
            expected = state["touches_used"]
            allowed = {expected, expected + 1} if state.get("pending") else {expected}
            local_completion = (not state.get("pending") and
                                (state["incident_reached"] or expected >= state["touch_budget"]))
            pending_at_limit = (state.get("pending") and session.get("touches_used") == expected + 1
                                and expected + 1 >= state["touch_budget"])
            if (session.get("touches_used") not in allowed or
                    (session.get("status") != "active" and not local_completion and not pending_at_limit)):
                raise ValueError("Session changed or ended; inspect API history before resuming.")
            if state.get("storage_enabled") and self.event_sink is None:
                raise ValueError("Resume requires the original storage sink to preserve recorded history.")
        else:
            assessment = self.selector.assess(profile)
            lane = assessment["selected_lane"]
            hook = self.selector.build_hook(lane, profile)
            story = build_story(lane, profile)
            self.progress(f"Checking available channels for {mode} mode.")
            available = self.api.list_channels()
            if synthetic:
                available = [c for c in available if c not in LIVE_CHANNELS]
            channels = channel_plan(available, hook.channel)
            story["sender_phone"] = "+49 30 55501099"  # Fictional simulator sender identity.
            story["sender_handle"] = "@" + story["sender_email"].replace("@", ".")
            if self.timing["start"]:
                from datetime import timedelta
                base = datetime.fromisoformat(self.timing["start"])
                story["year"] = str(base.year)
                if "deadline" in story:
                    story["deadline"] = (base + timedelta(days=90)).strftime("%B %d, %Y")
                story["timing_strategy"] = self.timing["strategy"]
            validate_contact("Preflight", story["sender_email"], profile, hook.landing_page_url)
            if not practice:
                from pathlib import Path
                for previous_path in Path(LOGS_DIR).glob("*.json"):
                    with previous_path.open() as stream:
                        previous = json.load(stream)
                    if (previous.get("mode") == "eval" and previous.get("target_id") == profile.subject_id
                            and (previous.get("touches_used", 0) > 0 or previous.get("pending"))):
                        raise ValueError("This target already has a local scoring session. Resume its journal; do not start another.")
            self.progress(f"Opening {mode} session for {profile.subject_id}.")
            session = self.api.start_session(profile.subject_id, practice=practice)
            sid = session["session_id"]
            if not re.fullmatch(r"[A-Za-z0-9_-]+", sid):
                raise ValueError("Invalid simulator session identity.")
            path = os.path.join(LOGS_DIR, f"{sid}.json")
            if os.path.exists(path):
                raise ValueError("Session already has a journal; use resume instead of overwriting it.")
            state = {
                "journal_version": 1, "session_id": sid, "target_id": profile.subject_id,
                "profile": asdict(profile), "mode": mode, "started_at": _now(),
                "lane_id": lane, "hook": asdict(hook), "story": story,
                "touch_budget": session.get("touch_budget", 30 if practice else 10),
                "touches_used": session.get("touches_used", 0), "turns": [],
                "incident_reached": False, "official_incident": None,
                "winning_event": None, "status": "running", "pending": None,
                "nda_pivot_done": False, "page_registered": False,
                "topic_assessment": assessment, "topic_as_of": assessment["as_of"],
                "topic_switches": 0,
                "source_metadata": self.selector.source_metadata,
                "storage_enabled": self.event_sink is not None,
                "storage_run": "journal:" + sid if self.event_sink else None,
                "channel_plan": channels, "channel_mode": self.channel_mode,
                "timing_plan": self.timing,
            }
            write_snapshot(path, state)
        self.progress(f"Session {state['session_id']} ({mode}); journal: {os.path.abspath(path)}")
        try:
            return self._continue(profile, state, path, practice, synthetic)
        except (Exception, KeyboardInterrupt) as exc:
            state["status"] = "interrupted"
            state["failure"] = {"type": type(exc).__name__, "at": _now()}
            from src.draft_grounding import DraftReviewError
            if isinstance(exc, DraftReviewError):
                state["failure"]["issue_codes"] = exc.issue_codes
            # Do not echo provider error bodies or credentials into the journal.
            write_snapshot(path, state)
            self.progress(f"Session interrupted ({type(exc).__name__}); journal preserved for recovery.")
            raise

    def _continue(self, profile, state, path, practice, synthetic):
        from copy import deepcopy
        state["status"] = "running"
        state.pop("failure", None)
        history = state["turns"]
        if "source_metadata" in state:
            self.selector.source_metadata = state["source_metadata"]
        if history and self.event_sink:
            self.event_sink(state)
        hook_data = deepcopy(state["hook"])
        hook_data["persona"] = Persona(**hook_data["persona"])
        hook = Hook(**hook_data)
        story, lane = state["story"], state["lane_id"]
        # Old journals keep their saved two-channel behavior and untimed story.
        channels = state.get("channel_plan", ["email", "linkedin_message"])
        timing = state.get("timing_plan", {"strategy": "none", "start": None})
        sid = state["session_id"]

        while (state["pending"] or state["touches_used"] < state["touch_budget"]) and not state["incident_reached"]:
            pending = state["pending"]
            if pending is None:
                reply = history[-1].get("reply") if history else None
                reaction = self.classifier.classify(history[-1]["sent"], reply) if history else "INITIAL"
                assessment = self.selector.assess(profile, history, as_of=state.get("topic_as_of"))
                state["topic_assessment"] = assessment
                from src.orchestrator.topic_ranking import TOPIC_REJECTION
                # One evidence-supported topic revision after an explicit relevance
                # objection. Keep the sender and all prior commitments unchanged.
                chosen = assessment["selected_lane"]
                supported = next((c for c in assessment["candidates"]
                                  if c["lane_id"] == chosen and c["score"] > 0 and c["evidence"]), None)
                professional = {"sales", "product", "engineering", "creative", "consulting"}
                compatible = (LANES_CATALOG.get(lane, {}).get("domain") in professional
                              and LANES_CATALOG.get(chosen, {}).get("domain") in professional
                              and not LANES_CATALOG.get(chosen, {}).get("landing_page"))
                if (reply and TOPIC_REJECTION.search(reply) and supported and chosen != lane and compatible
                        and not state["nda_pivot_done"] and state.get("topic_switches", 0) < 1):
                    revised = self.selector.build_hook(chosen, profile)
                    revised.persona = hook.persona
                    hook, lane = revised, chosen
                    story["attachment"] = hook.attachment
                    story["landing_url"] = hook.landing_page_url
                    story["topic_revision"] = "Explain the change of topic explicitly; retain earlier identity and commitments."
                    state["topic_switches"] = state.get("topic_switches", 0) + 1
                    state["page_registered"] = False
                next_channel = choose_channel(channels, history, state.get("channel_mode", "adaptive"))
                if next_channel is None:
                    state["stop_reason"] = "silence_limit"
                    break
                hook.channel = next_channel
                if reaction == ResponseClassifier.REJECTION:
                    state["stop_reason"] = "explicit_rejection"
                    break
                if not state["nda_pivot_done"] and story.get("nda_filename") and self._reply_requests_nda(reply):
                    # Preserve the agreed story instead of resetting its details.
                    lane = "NDA_FOLLOWUP"
                    hook = Hook(id=f"hook_nda_{profile.subject_id}", subject=profile.subject_id,
                                pretext="Mutual NDA for vendor evaluation",
                                persona=Persona(story["colleague_name"], "Procurement", story["org"],
                                                "Colleague introduced in this session"),
                                ask=story["nda_filename"], win_type="action", channel="email",
                                attachment=story["nda_filename"])
                    story["sender_name"] = story["colleague_name"]
                    story["sender_email"] = story["colleague_email"]
                    story["sender_role"] = hook.persona.role
                    state["nda_pivot_done"] = True
                    hook.channel = "email" if "email" in channels else next_channel
                if reaction == ResponseClassifier.PUSHBACK and not state["nda_pivot_done"]:
                    hook.win_type = "disclosure"
                    hook.ask = "Could you explain how your team handles this internally?"
                    hook.attachment = None
                    story["attachment"] = None
                # Full recorded context keeps questions, earlier answers and
                # sender changes available. Replies remain untrusted evidence.
                sent_at = contact_time(timing, history)
                context = json.dumps({"reaction": reaction, "prior_contacts": prompt_history(history),
                                      "remaining_contacts": state["touch_budget"] - state["touches_used"],
                                      "topic_assessment": assessment, "sent_at": sent_at},
                                     ensure_ascii=False)
                state.update(hook=asdict(hook), story=story, lane_id=lane)
                write_snapshot(path, state)
                self.progress(f"Preparing contact {state['touches_used'] + 1}/{state['touch_budget']} on {hook.channel}.")
                if hook.landing_page_url and not state["page_registered"]:
                    self.progress("Registering simulator landing page; no contact is spent.")
                    self.api.register_landing_page(
                        session_id=sid, url=hook.landing_page_url,
                        title=hook.landing_page_title or "Portal",
                        fields=get_fields_for_lane(lane), html=build_landing_page(lane, story))
                    state["page_registered"] = True
                    write_snapshot(path, state)
                excluded_ids = {f["fact_id"] for f in assessment["excluded_facts"]}
                draft_profile = replace(profile, facts=[f for f in profile.facts if f.id not in excluded_ids])
                if hook.channel in LIVE_CHANNELS:
                    # The first utterance is drafted after hearing the greeting.
                    draft = {"body": "", "subject": None, "attachment": None}
                else:
                    draft = self.drafter.draft_contact(hook, draft_profile, turn_no=len(history) + 1,
                                                      context=context, lane_id=lane, story=story,
                                                      source_metadata=self.selector.source_metadata)
                sender_name = story.get("sender_name") or hook.persona.name
                address = sender_address(hook.channel, story)
                if hook.channel not in LIVE_CHANNELS:
                    validate_contact(draft["body"], address, profile, hook.landing_page_url)
                request = dict(session_id=sid, channel=hook.channel,
                               sender_name=sender_name, sender_address=address,
                               message=draft["body"], subject=draft.get("subject"),
                               attachment=draft.get("attachment"), to_target_id=profile.subject_id,
                               story_time=sent_at)
                ledger = fact_ledger(draft_profile, hook, self.selector.source_metadata)
                pending = {"request": request, "idempotency_key": str(uuid.uuid4()),
                           "prepared_at": _now(), "reaction": reaction,
                           "grounding": draft.get("grounding"),
                           "evidence_context": {"available_facts": ledger,
                               "sources": {f["source_ref"]: self.selector.source_metadata.get(f["source_ref"])
                                           for f in ledger} if self.selector.source_metadata else {},
                               "scenario_details": dict(story)}}
                state.update(pending=pending, hook=asdict(hook), story=story, lane_id=lane)
                write_snapshot(path, state)  # intent is durable before sending
            request = pending["request"]
            try:
                if request["channel"] in LIVE_CHANNELS:
                    from src.conversation_runner import run_conversation
                    allowed_ids = {f["id"] for f in pending["evidence_context"]["available_facts"]}
                    draft_profile = replace(profile, facts=[f for f in profile.facts if f.id in allowed_ids])
                    response = run_conversation(self, draft_profile, hook, story, lane, state, path)
                elif isinstance(self.api, TargetClient):
                    self.progress(f"Sending {request['channel']} contact; waiting for simulator (120-second request timeout).")
                    response = self.api.send_contact(**request, idempotency_key=pending["idempotency_key"])
                else:
                    response = self.api.send_contact(**request)
            except TargetAPIError as exc:
                # Definitive failures reached nobody; uncertain transport/server
                # failures retain the exact intent for idempotent recovery.
                if request["channel"] not in LIVE_CHANNELS and exc.status_code in (400, 401, 403, 404, 409, 413, 415, 422):
                    state["pending"] = None
                raise
            message_id = response.get("message_id")
            touches = response.get("touches_used")
            if (not isinstance(message_id, str) or not message_id.strip()
                    or type(touches) is not int or touches != state["touches_used"] + 1):
                raise ValueError("Unexpected contact identity/count; reconcile the pending request.")
            events = response.get("events", [])
            evidence = summarize_events(events, trusted_transport=isinstance(self.api, TargetClient),
                                        synthetic=synthetic, session_id=sid, contact_id=message_id,
                                        contact_kind="conversation" if request["channel"] in LIVE_CHANNELS else "message")
            turn = {
                "turn": len(history) + 1, "message_id": message_id,
                "sent": ("\n".join(d["say"] for d in response["dialogue"])
                         if "dialogue" in response else request["message"]),
                "sent_subject": request.get("subject"),
                "sent_channel": request["channel"], "attachment": request.get("attachment"),
                "sender": {"name": request["sender_name"], "address": request["sender_address"]},
                "reply": response.get("reply"), "events": events,
                "event_type": response.get("event_type"), "timestamp": _now(),
                "sent_at": request.get("story_time"),
                "story_time_end": response.get("story_time_end", request.get("story_time")),
                "conversation_id": response.get("conversation_id"),
                "dialogue": response.get("dialogue", []), "opening": response.get("opening"),
                "grounding": pending.get("grounding"), "evidence_context": pending.get("evidence_context"),
                "touches_used": touches, "reaction_before_send": pending["reaction"],
                "idempotency_key": pending["idempotency_key"], "lane_id": lane,
                "topic_assessment": state.get("topic_assessment"), **evidence,
            }
            history.append(turn)
            state.update(touches_used=touches, pending=None)
            if evidence["verified_objective"]:
                state["incident_reached"] = True  # compatibility: local evidence, not jury outcome
                state["winning_event"] = next((e["type"] for e in events
                                               if e.get("id") in evidence["evidence_event_ids"]), None)
                state["stop_reason"] = "objective_evidence"
            write_snapshot(path, state)
            self.progress(f"Recorded contact {touches}/{state['touch_budget']}: {response.get('event_type') or 'response'}.")
            if self.event_sink:
                self.event_sink(state)
            self.committed_turns.append(Turn(sid, "analysis_v1", turn["turn"], message_id, turn["timestamp"]))
        state["status"] = "completed"
        state.setdefault("stop_reason", "contact_budget")
        write_snapshot(path, state)
        self.progress(f"Session finished: {state['stop_reason']}; {state['touches_used']} contacts used.")
        return self._result(state, profile)

    @staticmethod
    def _result(state, profile):
        return {"session_id": state["session_id"], "target": profile.name,
                "lane_used": state["lane_id"], "touches_used": state["touches_used"],
                "touch_budget": state["touch_budget"], "incident_reached": state["incident_reached"],
                "incident_type": state["winning_event"], "history": state["turns"],
                "mode": state["mode"], "official_incident": None, "stop_reason": state.get("stop_reason")}

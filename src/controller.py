"""
Run Controller for STOPReplay.
Owned by Shaurya. Orchestrates target sessions, manages the 10-contact budget,
coordinates the Drafter and Pushback Handler, and records atomic turn checkpoints.

Enhancements (Nov 2026):
  - Passes lane_id + story invariants to drafter (no hallucinated dates/companies)
  - Registers landing pages with real HTML (credential win via page.submitted)
  - Silence threshold: 4 for practice (never waste 30-touch budget), 2 for eval
  - NDA pivot: auto-switches to NDA_FOLLOWUP lane when Julius says "nda"/"sign"
  - Saves timeline JSON after each run for Gary's UI
"""

from typing import Dict, Any, Optional, List
import json
import os
import time

from src.models.schemas import TargetProfile, Hook, Turn
from src.orchestrator.strategy_planner import StrategySelector
from src.orchestrator.drafter import MessageDrafter
from src.orchestrator.pushback_handler import ResponseClassifier
from src.api.mock_client import MockSimulatorClient
from src.craft.landing_pages import build_landing_page, get_fields_for_lane
from src.craft.story import build_story


LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs", "runs")


class RunController:
    """Master controller orchestrating simulator attack runs."""

    def __init__(self, api_client=None, strategy_selector=None, drafter=None, classifier=None):
        self.api = api_client or MockSimulatorClient()
        self.selector = strategy_selector or StrategySelector()
        self.drafter = drafter or MessageDrafter()
        self.classifier = classifier or ResponseClassifier()
        self.committed_turns: List[Turn] = []

    # ── NDA pivot detection ────────────────────────────────────────────────────
    @staticmethod
    def _reply_requests_nda(reply: Optional[str]) -> bool:
        """True if the twin's reply explicitly asks for / accepts an NDA."""
        if not reply:
            return False
        lower = reply.lower()
        return any(kw in lower for kw in ["nda", "non-disclosure", "sign", "agreement", "legal"])

    # ── Channel-switch on silence ──────────────────────────────────────────────
    @staticmethod
    def _nudge_channel(current_channel: str) -> str:
        """Return an alternative channel for a cross-channel nudge after silence."""
        escalation = {
            "email": "linkedin_message",
            "linkedin_message": "email",
            "sms": "email",
            "whatsapp": "email",
        }
        return escalation.get(current_channel, "email")

    def execute_run(self, profile: TargetProfile, practice: bool = True) -> Dict[str, Any]:
        """
        Executes a multi-turn run against a target within the touch budget.
        Returns full run telemetry and final incident status.
        """
        # 1. Start Session
        sess = self.api.start_session(profile.subject_id, practice=practice)
        session_id = sess["session_id"]
        touch_budget = sess.get("touch_budget", 30 if practice else 10)
        # Silence threshold: more lenient for practice (never stop too early on free budget)
        max_silence = 4 if practice else 2

        print(f"[*] Session {session_id} | target={profile.subject_id} | budget={touch_budget} touches")

        # 2. Strategy Selection (Dynamic Lane Match)
        lane_id = self.selector.select_lane(profile)
        hook = self.selector.build_hook(lane_id, profile)
        story = build_story(lane_id, profile)

        print(f"[*] Lane: {lane_id} | channel: {hook.channel} | win_type: {hook.win_type}")

        # 3. Register landing page with real HTML (if lane requires one)
        if hook.landing_page_url and hasattr(self.api, "register_landing_page"):
            try:
                html_page = build_landing_page(lane_id, story)
                fields = get_fields_for_lane(lane_id)
                self.api.register_landing_page(
                    session_id=session_id,
                    url=hook.landing_page_url,
                    title=hook.landing_page_title or "Portal Sign-In",
                    fields=fields,
                    html=html_page
                )
                print(f"[*] Landing page registered: {hook.landing_page_url} (fields: {fields})")
            except Exception as e:
                print(f"[RunController] Warning: Landing page registration failed: {e}")

        conversation_history: List[Dict[str, Any]] = []
        incident_reached = False
        winning_event = None
        turn_no = 0
        consecutive_silence = 0
        nda_pivot_done = False

        while turn_no < touch_budget and not incident_reached:
            turn_no += 1

            # 4. Determine Context & Tactical Stance
            last_reply = conversation_history[-1].get("reply") if conversation_history else None
            state = self.classifier.classify(
                last_message_sent=conversation_history[-1].get("sent") if conversation_history else "",
                twin_reply=last_reply
            ) if turn_no > 1 else "INITIAL"

            # Silence counting
            if state == ResponseClassifier.SILENCE and turn_no > 2:
                consecutive_silence += 1
                if consecutive_silence == 2:
                    # Cross-channel nudge (don't quit yet)
                    old_ch = hook.channel
                    hook.channel = self._nudge_channel(hook.channel)
                    print(f"[*] Turn {turn_no}: Silence detected — pivoting channel {old_ch} → {hook.channel}")
                elif consecutive_silence >= max_silence:
                    print(f"[*] Target {profile.name} stopped responding after {consecutive_silence} silences. Ending session.")
                    break
            else:
                consecutive_silence = 0

            # ── NDA pivot: if twin asked for NDA, switch to NDA_FOLLOWUP lane ──
            if not nda_pivot_done and self._reply_requests_nda(last_reply):
                print(f"[*] Turn {turn_no}: Twin signalled NDA willingness — pivoting to NDA_FOLLOWUP lane!")
                nda_hook = Hook(
                    id=f"hook_nda_{profile.subject_id}",
                    subject=profile.subject_id,
                    pretext="Mutual NDA for vendor evaluation",
                    persona=hook.persona,
                    ask=story.get("nda_filename", "Mutual_NDA_revel8_DAX.pdf"),
                    win_type="action",
                    channel="email",
                    attachment=story.get("nda_filename", "Mutual_NDA_revel8_DAX.pdf"),
                )
                hook = nda_hook
                lane_id = "NDA_FOLLOWUP"
                story = build_story("NDA_FOLLOWUP", profile)
                # Update sender to Sarah Weber
                story["sender_name"] = "Sarah Weber"
                story["sender_email"] = story.get("colleague_email", "s.weber@enterprise-sourcing.org")
                nda_pivot_done = True

            # Build context summary
            if last_reply:
                context_summary = (
                    f"Turn {turn_no}. Psychological State: {state}.\n"
                    f"The target ({profile.name}) replied directly to you with:\n\"{last_reply}\"\n"
                    f"Task: Directly, specifically, and convincingly answer EVERY question or concern "
                    f"{profile.name} raised in character as {hook.persona.name}. "
                    f"Once their questions are answered, politely reiterate the call to action ({hook.ask})."
                )
            else:
                context_summary = f"Turn {turn_no}. State: {state}. Initial outreach."

            if state == ResponseClassifier.PUSHBACK and not nda_pivot_done:
                # Pivot to disclosure if file/link is resisted
                hook.win_type = "disclosure"
                hook.ask = "Could you explain how your team handles this internally?"

            # 5. Draft Contact Message (with HTML templates + story invariants)
            draft = self.drafter.draft_contact(
                hook=hook,
                profile=profile,
                turn_no=turn_no,
                context=context_summary,
                lane_id=lane_id,
                story=story,
            )

            # Resolve sender address (use story colleague email for NDA pivot)
            if lane_id == "NDA_FOLLOWUP":
                sender_addr = story.get("colleague_email", "s.weber@enterprise-sourcing.org")
                sender_name = story.get("sender_name", "Sarah Weber")
            else:
                raw_addr = hook.persona.name.lower().replace(" ", ".").replace("'", "")
                raw_org = hook.persona.org.lower().replace(" ", "-").replace("'", "")
                sender_addr = f"{raw_addr}@{raw_org}.com"
                sender_name = hook.persona.name

            print(f"[*] Turn {turn_no} | channel={hook.channel} | state={state} | sender={sender_addr}")

            # 6. Send Contact via API (Consumes 1 Touch)
            response_event = self.api.send_contact(
                session_id=session_id,
                channel=hook.channel,
                sender_name=sender_name,
                sender_address=sender_addr,
                message=draft["body"],
                subject=draft.get("subject"),
                attachment=draft.get("attachment"),
                to_target_id=profile.subject_id
            )

            # 7. Commit Turn Checkpoint
            checkpoint = Turn(
                run_id=session_id,
                analysis_id="analysis_v1",
                turn_no=turn_no,
                event_id=response_event["message_id"],
                committed_at=str(time.time()),
                finding_id=None
            )
            self.committed_turns.append(checkpoint)

            reply_text = response_event.get("reply")
            ev_type = response_event.get("event_type")

            conversation_history.append({
                "turn": turn_no,
                "sent": draft["body"],
                "sent_subject": draft.get("subject"),
                "sent_channel": hook.channel,
                "reply": reply_text,
                "event_type": ev_type,
                "timestamp": str(time.time()),
            })

            if reply_text:
                print(f"    ↳ REPLY: {reply_text[:200]}")
            else:
                print(f"    ↳ EVENT: {ev_type or 'silence'}")

            # 8. Check for Win Condition
            if ev_type in ("attachment.opened", "link.opened", "page.submitted"):
                incident_reached = True
                winning_event = ev_type
                print(f"\n[★] WIN — {ev_type.upper()} on turn {turn_no}!")
                break

        # 9. Save run log for timeline reporter
        run_data = {
            "session_id": session_id,
            "target_id": profile.subject_id,
            "lane_id": lane_id,
            "turns": conversation_history,
            "incident_reached": incident_reached,
            "winning_event": winning_event,
        }
        os.makedirs(LOGS_DIR, exist_ok=True)
        log_path = os.path.join(LOGS_DIR, f"{session_id}.json")
        with open(log_path, "w") as f:
            json.dump(run_data, f, indent=2)
        print(f"[*] Run log saved → {log_path}")

        return {
            "session_id": session_id,
            "target": profile.name,
            "lane_used": lane_id,
            "touches_used": turn_no,
            "touch_budget": touch_budget,
            "incident_reached": incident_reached,
            "incident_type": winning_event or ("disclosure" if incident_reached else None),
            "history": conversation_history,
        }

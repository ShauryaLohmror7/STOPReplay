"""
Run Controller for STOPReplay.
Owned by Shaurya. Orchestrates target sessions, manages the 10-contact budget,
coordinates the Drafter and Pushback Handler, and records atomic turn checkpoints.
"""

from typing import Dict, Any, Optional, List
import time
from src.models.schemas import TargetProfile, Hook, Turn
from src.orchestrator.strategy_planner import StrategySelector
from src.orchestrator.drafter import MessageDrafter
from src.orchestrator.pushback_handler import ResponseClassifier
from src.api.mock_client import MockSimulatorClient


class RunController:
    """Master controller orchestrating simulator attack runs."""

    def __init__(self, api_client=None, strategy_selector=None, drafter=None, classifier=None):
        self.api = api_client or MockSimulatorClient()
        self.selector = strategy_selector or StrategySelector()
        self.drafter = drafter or MessageDrafter()
        self.classifier = classifier or ResponseClassifier()
        self.committed_turns: List[Turn] = []

    def execute_run(self, profile: TargetProfile, practice: bool = True) -> Dict[str, Any]:
        """
        Executes a multi-turn run against a target within the 10-contact budget.
        Returns full run telemetry and final incident status.
        """
        # 1. Start Session
        sess = self.api.start_session(profile.subject_id, practice=practice)
        session_id = sess["session_id"]
        touch_budget = sess["touch_budget"]

        # 2. Strategy Selection (Dynamic Lane Match)
        lane_id = self.selector.select_lane(profile)
        hook = self.selector.build_hook(lane_id, profile)

        conversation_history: List[Dict[str, Any]] = []
        incident_reached = False
        winning_event = None
        turn_no = 0

        while turn_no < touch_budget and not incident_reached:
            turn_no += 1

            # 3. Determine Context & Tactical Stance
            last_reply = conversation_history[-1].get("reply") if conversation_history else None
            state = self.classifier.classify(
                last_message_sent=conversation_history[-1].get("sent") if conversation_history else "",
                twin_reply=last_reply
            ) if turn_no > 1 else "INITIAL"

            context_summary = f"Turn {turn_no}. Prior twin reaction: {state}."
            if state == ResponseClassifier.PUSHBACK:
                # Pivot to disclosure if file/link is resisted
                hook.win_type = "disclosure"
                hook.ask = "Could you explain how your team handles this internally?"

            # 4. Draft Contact Message
            draft = self.drafter.draft_contact(
                hook=hook,
                profile=profile,
                turn_no=turn_no,
                context=context_summary
            )

            # 5. Send Contact via API (Consumes 1 Touch)
            response_event = self.api.send_contact(
                session_id=session_id,
                channel=hook.channel,
                sender_name=hook.persona.name,
                sender_address=f"{hook.persona.name.lower().replace(' ', '.')}@{hook.persona.org.lower().replace(' ', '-')}.org",
                message=draft["body"],
                subject=draft.get("subject"),
                attachment=draft.get("attachment")
            )

            # 6. Commit Turn Checkpoint
            checkpoint = Turn(
                run_id=session_id,
                analysis_id="analysis_v1",
                turn_no=turn_no,
                event_id=response_event["message_id"],
                committed_at=str(time.time()),
                finding_id=None
            )
            self.committed_turns.append(checkpoint)

            conversation_history.append({
                "turn": turn_no,
                "sent": draft["body"],
                "reply": response_event.get("reply"),
                "event_type": response_event.get("event_type")
            })

            # 7. Check for Incident
            ev_type = response_event.get("event_type")
            if ev_type in ["attachment.opened", "link.opened", "page.submitted"]:
                incident_reached = True
                winning_event = ev_type
                break

        return {
            "session_id": session_id,
            "target": profile.name,
            "lane_used": lane_id,
            "touches_used": turn_no,
            "touch_budget": touch_budget,
            "incident_reached": incident_reached,
            "incident_type": winning_event or ("disclosure" if incident_reached else None),
            "history": conversation_history
        }

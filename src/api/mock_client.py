"""
Mock Simulator Client for offline testing and rehearsal.
Implements the exact same interface as TargetClient, with simulated AI twin responses
and zero external network requests.
"""

from typing import List, Dict, Any, Optional
import uuid
import time


class MockSimulatorClient:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.landing_pages: Dict[str, str] = {}
        self.events_log: Dict[str, List[Dict[str, Any]]] = {}

    def list_channels(self) -> List[str]:
        return [
            "email", "sms", "whatsapp", "signal", "telegram", "imessage",
            "slack", "teams_chat", "discord", "linkedin_message",
            "linkedin_connection_request", "calendar_invite", "phone_call"
        ]

    def start_session(self, target_id: str, practice: bool = True) -> Dict[str, Any]:
        sid = f"mock_sess_{uuid.uuid4().hex[:8]}"
        self.sessions[sid] = {
            "session_id": sid,
            "target": target_id,
            "mode": "practice" if practice else "scoring",
            "touches_used": 0,
            "touch_budget": 30 if practice else 10,
            "active": True
        }
        self.events_log[sid] = []
        return self.sessions[sid]

    def send_contact(
        self,
        session_id: str,
        channel: str,
        sender_name: str,
        sender_address: str,
        message: str,
        subject: Optional[str] = None,
        attachment: Optional[str] = None,
        story_time: Optional[str] = None
    ) -> Dict[str, Any]:
        sess = self.sessions.get(session_id)
        if not sess:
            raise ValueError(f"Session {session_id} not found")

        sess["touches_used"] += 1
        msg_id = f"msg_{uuid.uuid4().hex[:6]}"

        # Simulate Twin response logic
        reply_text = "Thanks for reaching out! Let me take a look at the details."
        event_type = "reply"

        if attachment:
            event_type = "attachment.opened"
            reply_text = f"I have opened and reviewed {attachment}. Looks promising!"
        elif "http" in message:
            event_type = "link.opened"

        ev = {
            "message_id": msg_id,
            "session_id": session_id,
            "event_type": event_type,
            "reply": reply_text,
            "timestamp": time.time(),
            "touches_used": sess["touches_used"]
        }
        self.events_log[session_id].append(ev)
        return ev

    def get_session_events(self, session_id: str) -> List[Dict[str, Any]]:
        return self.events_log.get(session_id, [])

    def register_landing_page(self, path: str, domain: str, html_content: str) -> Dict[str, Any]:
        url = f"https://{domain.rstrip('/')}/{path.lstrip('/')}"
        self.landing_pages[url] = html_content
        return {"status": "registered", "url": url}

"""
Mock Simulator Client for offline testing and rehearsal.
Implements the controller's basic contact interface with deterministic fixture
responses and zero external network requests. It does not predict effectiveness
or implement the live client's idempotent recovery protocol.
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
        story_time: Optional[str] = None,
        to_target_id: Optional[str] = None
    ) -> Dict[str, Any]:
        sess = self.sessions.get(session_id)
        if not sess:
            raise ValueError(f"Session {session_id} not found")

        sess["touches_used"] += 1
        msg_id = f"msg_{uuid.uuid4().hex[:6]}"

        # Simulate Twin response logic
        reply_text = "Thanks for reaching out! Let me take a look at the details."
        event_type = "reply"

        events: List[Dict[str, Any]] = []

        if attachment:
            event_type = "attachment.opened"
            reply_text = f"I have opened and reviewed {attachment}. Looks promising!"
            events.append({"id": f"e_{uuid.uuid4().hex[:6]}", "type": "attachment.opened", "filename": attachment})
        elif "http" in message:
            event_type = "link.opened"
            events.append({"id": f"e_{uuid.uuid4().hex[:6]}", "type": "link.opened", "url": "https://portal-verify.org"})

        ev = {
            "message_id": msg_id,
            "session_id": session_id,
            "event_type": event_type,
            "reply": reply_text,
            "events": events,
            "timestamp": time.time(),
            "touches_used": sess["touches_used"]
        }
        self.events_log[session_id].append(ev)
        return ev

    def get_session_events(self, session_id: str) -> List[Dict[str, Any]]:
        return self.events_log.get(session_id, [])

    def register_landing_page(
        self,
        session_id: str = "",
        url: Optional[str] = None,
        title: Optional[str] = None,
        fields: Optional[List[str]] = None,
        html: Optional[str] = None,
        text: Optional[str] = None,
        path: Optional[str] = None,
        domain: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        final_url = url or f"https://{str(domain).rstrip('/')}/{str(path).lstrip('/')}"
        self.landing_pages[final_url] = html or text or "mock landing page"
        return {"status": "registered", "url": final_url, "page_id": f"p_{uuid.uuid4().hex[:8]}"}

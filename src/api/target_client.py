"""
Target API Client for the revel8 Simulation Engine.
Base URL: https://target-api.apps.01.cf.eu01.stackit.cloud/v1
Authentication: Bearer <TEAM_KEY>
Uses the organizer protocol captured in docs/api_docs_live.md.
"""

from __future__ import annotations
import os
import json
import uuid
import time
import urllib.request
import urllib.error
from urllib.parse import urlsplit
from typing import Optional, Dict, Any, List

TARGET_API_BASE = os.getenv("TARGET_API_URL", "https://target-api.apps.01.cf.eu01.stackit.cloud/v1")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class TargetAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class TargetClient:
    """Production client for revel8's Target API."""

    def __init__(self, api_base: Optional[str] = None, team_key: Optional[str] = None):
        self.base_url = (api_base or TARGET_API_BASE).rstrip("/")
        parsed = urlsplit(self.base_url)
        if (parsed.scheme != "https" or parsed.netloc != "target-api.apps.01.cf.eu01.stackit.cloud"
                or parsed.path != "/v1" or parsed.query or parsed.fragment):
            raise ValueError("Only the documented HTTPS simulator API is supported.")
        self.team_key = team_key or os.getenv("REVEL8_TEAM_KEY", os.getenv("TARGET_API_KEY", ""))

    def _headers(self, idempotency_key: Optional[str] = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.team_key:
            headers["Authorization"] = f"Bearer {self.team_key}"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def _request(
        self, method, endpoint, payload=None, idempotency_key=None, timeout=120
    ):
        """Bounded retries only for reads or a durably keyed contact."""
        safe_retry = method == "GET" or bool(idempotency_key)
        for attempt in range(3):
            try:
                return self._request_once(method, endpoint, payload, idempotency_key, timeout)
            except TargetAPIError as exc:
                transient = exc.status_code in (None, 429, 502, 503, 504)
                if not safe_retry or not transient or attempt == 2:
                    raise
                time.sleep(2 ** (attempt + 1))

    def _request_once(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        timeout: int = 120
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            headers=self._headers(idempotency_key),
            method=method
        )

        try:
            with urllib.request.build_opener(_NoRedirect).open(req, timeout=timeout) as resp:
                res_body = resp.read().decode("utf-8")
                return json.loads(res_body) if res_body else {}
        except urllib.error.HTTPError as e:
            raise TargetAPIError(f"Simulator request failed (HTTP {e.code}).", status_code=e.code) from None
        except urllib.error.URLError as e:
            raise TargetAPIError("Simulator transport failed.") from None
        except TimeoutError:
            raise TargetAPIError("Simulator request timed out.") from None

    def list_scenarios(self) -> List[Dict[str, Any]]:
        """GET /v1/scenarios"""
        return self._request("GET", "/scenarios")

    def list_channels(self) -> List[str]:
        """GET /v1/channels"""
        res = self._request("GET", "/channels")
        if isinstance(res, list):
            return res
        return res.get("channels", []) if isinstance(res, dict) else []

    def start_session(self, scenario_or_target: str = "practice", practice: bool = True) -> Dict[str, Any]:
        """POST /v1/sessions"""
        scenario_id = scenario_or_target if scenario_or_target in ("practice", "eval") else ("practice" if practice else "eval")
        payload = {"scenario_id": scenario_id}
        res = self._request("POST", "/sessions", payload)
        if "touch_budget" not in res:
            res["touch_budget"] = 30 if scenario_id == "practice" else 10
        if "touches_used" not in res:
            res["touches_used"] = 0
        return res

    def send_message(
        self,
        session_id: str,
        to_target_id: str,
        channel: str,
        sender_name: str,
        sender_address: str,
        body: str,
        subject: Optional[str] = None,
        attachments: Optional[List[Any]] = None,
        sent_at: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """POST /v1/sessions/{session_id}/messages"""
        payload = {
            "to": to_target_id,
            "channel": channel,
            "from": {
                "name": sender_name,
                "address": sender_address
            },
            "body": body
        }
        if subject:
            payload["subject"] = subject
        if attachments:
            payload["attachments"] = attachments
        if sent_at:
            payload["sent_at"] = sent_at

        key = idempotency_key or str(uuid.uuid4())
        return self._request("POST", f"/sessions/{session_id}/messages", payload, idempotency_key=key, timeout=120)

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
        to_target_id: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Unified contact method called by RunController.
        Dispatches to send_message and maps revel8's return events into normalized format.
        """
        if not to_target_id:
            raise ValueError("An explicit scenario target ID is required.")
        target = to_target_id
        # The documented string form denotes an uploaded asset ID. Declared
        # files use a filename object; no real file is uploaded or executed.
        attachments = [{"filename": attachment}] if attachment else None

        api_res = self.send_message(
            session_id=session_id,
            to_target_id=target,
            channel=channel,
            sender_name=sender_name,
            sender_address=sender_address,
            body=message,
            subject=subject,
            attachments=attachments,
            sent_at=story_time,
            idempotency_key=idempotency_key
        )

        events = api_res.get("events", [])
        reply_text = None
        dominant_event_type = None

        for ev in events:
            ev_type = ev.get("type")
            if ev_type in ("attachment.opened", "link.opened", "page.submitted"):
                dominant_event_type = ev_type
            elif ev_type == "reply" and not reply_text:
                reply_text = ev.get("body")
                if not dominant_event_type:
                    dominant_event_type = "reply"

        if not dominant_event_type:
            dominant_event_type = "silence" if not events else events[0].get("type")

        return {
            "message_id": api_res.get("message_id"),
            "session_id": session_id,
            "touches_used": api_res.get("touches_used"),
            "events": events,
            "event_type": dominant_event_type,
            "reply": reply_text
        }

    def get_session_events(self, session_id: str) -> List[Dict[str, Any]]:
        """GET /v1/sessions/{session_id}/events"""
        res = self._request("GET", f"/sessions/{session_id}/events")
        return res.get("events", []) if isinstance(res, dict) else []

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/sessions/{session_id}")

    def list_sessions(self):
        return self._request("GET", "/sessions")

    def register_landing_page(
        self,
        session_id: str,
        url: str,
        title: str,
        fields: List[str],
        html: Optional[str] = None,
        text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        POST /v1/sessions/{session_id}/pages
        Registers a simulated landing page before sending a message linking to it.
        """
        payload = {
            "url": url,
            "title": title,
            "fields": fields
        }
        if html:
            payload["html"] = html
        elif text:
            payload["text"] = text
        else:
            payload["text"] = "Sign in to access your portal."

        return self._request("POST", f"/sessions/{session_id}/pages", payload)

    def start_conversation(
        self,
        session_id: str,
        to_target_id: str,
        channel: str,
        caller_address: str,
        caller_name: Optional[str] = None,
        sent_at: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        POST /v1/sessions/{session_id}/conversations
        Initiates a live exchange (phone_call, video_call, teams_call, live_chat).
        Costs exactly 1 touch for up to 10 dialogue turns!
        """
        sender = {"address": caller_address}
        if caller_name:
            sender["name"] = caller_name
        payload = {
            "to": to_target_id,
            "channel": channel,
            "from": sender
        }
        if channel not in {"phone_call", "video_call", "teams_call", "live_chat"}:
            raise ValueError("Unsupported conversation channel.")
        if sent_at:
            payload["sent_at"] = sent_at
        return self._request("POST", f"/sessions/{session_id}/conversations", payload,
                             idempotency_key=idempotency_key, timeout=120)

    def send_conversation_turn(self, conversation_id: str, say: str, *, sent_at=None,
                               attachments=None, idempotency_key=None) -> Dict[str, Any]:
        """
        POST /v1/conversations/{conversation_id}/turns
        Sends one line of speech in a live conversation.
        """
        payload = {"say": say}
        if sent_at:
            payload["sent_at"] = sent_at
        if attachments:
            payload["attachments"] = attachments
        return self._request("POST", f"/conversations/{conversation_id}/turns", payload,
                             idempotency_key=idempotency_key, timeout=120)

    def end_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """POST /v1/conversations/{conversation_id}/end"""
        return self._request("POST", f"/conversations/{conversation_id}/end")

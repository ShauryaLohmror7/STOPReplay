"""
Target API Client for the revel8 Simulation Engine.
Base URL: https://target-api.apps.01.cf.eu01.stackit.cloud/v1
Authentication: Bearer <TEAM_KEY>
"""

from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

TARGET_API_BASE = os.getenv("TARGET_API_URL", "https://target-api.apps.01.cf.eu01.stackit.cloud/v1")


class TargetAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class TargetClient:
    """Client for communicating with revel8's Target API."""

    def __init__(self, api_base: Optional[str] = None, team_key: Optional[str] = None):
        self.base_url = (api_base or TARGET_API_BASE).rstrip("/")
        self.team_key = team_key or os.getenv("REVEL8_TEAM_KEY", os.getenv("TARGET_API_KEY", ""))

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.team_key:
            headers["Authorization"] = f"Bearer {self.team_key}"
        return headers

    def _request(self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_body = resp.read().decode("utf-8")
                return json.loads(res_body) if res_body else {}
        except urllib.error.HTTPError as e:
            err_text = e.read().decode("utf-8")
            raise TargetAPIError(f"HTTP {e.code} on {method} {url}: {err_text}", status_code=e.code)
        except urllib.error.URLError as e:
            raise TargetAPIError(f"Network error on {method} {url}: {e.reason}")

    def list_channels(self) -> List[str]:
        """GET /v1/channels"""
        res = self._request("GET", "/channels")
        return res.get("channels", [])

    def start_session(self, target_id: str, practice: bool = True) -> Dict[str, Any]:
        """POST /v1/sessions"""
        payload = {"target": target_id, "mode": "practice" if practice else "scoring"}
        return self._request("POST", "/sessions", payload)

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
        """POST /v1/sessions/{session_id}/contact"""
        payload = {
            "channel": channel,
            "sender": {
                "name": sender_name,
                "address": sender_address
            },
            "body": message
        }
        if subject:
            payload["subject"] = subject
        if attachment:
            payload["attachment"] = attachment
        if story_time:
            payload["story_time"] = story_time

        return self._request("POST", f"/sessions/{session_id}/contact", payload)

    def get_session_events(self, session_id: str) -> List[Dict[str, Any]]:
        """GET /v1/sessions/{session_id}/events"""
        res = self._request("GET", f"/sessions/{session_id}/events")
        return res.get("events", [])

    def register_landing_page(self, path: str, domain: str, html_content: str) -> Dict[str, Any]:
        """POST /v1/landing_pages"""
        payload = {"path": path, "domain": domain, "html": html_content}
        return self._request("POST", "/landing_pages", payload)

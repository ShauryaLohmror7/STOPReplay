"""
Timeline & Disclosure Reporter for STOPReplay.
Reads a raw session JSON from logs/runs/{session_id}.json and produces:
  - logs/runs/{session_id}_timeline.json  (Gary's UI format)
  - Prints a human-readable disclosure summary to stdout

Disclosure Classification Logic:
  - reply containing "nda" / "sign" / "agreement"  → Legal Process Disclosed
  - reply containing seats / enterprise / "4,500"   → Business Scope Leaked
  - reply containing "team" / "solutions" / "sales" → Org Structure Leaked
  - attachment.opened event                          → Action Win ✓
  - page.submitted event                             → Credential Win ✓
  - link.opened event                                → Link Engagement

Usage:
    python -m src.reporting s_c00cecfdaf
    python -m src.reporting s_c00cecfdaf --print-only
"""

from __future__ import annotations
import sys
import json
import os
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs", "runs")

# Keyword → disclosure category mappings
_DISCLOSURE_RULES: List[tuple] = [
    (["attachment.opened"], "🏆 Action Win — Attachment Opened"),
    (["page.submitted"], "🏆 Credential Win — Form Submitted"),
    (["link.opened"], "🔗 Link Engagement — URL Clicked"),
    (["nda", "sign", "agreement", "legal", "contract"], "⚖️ Legal Process Disclosed"),
    (["4,500", "4500", "seats", "enterprise", "deployment", "workforce"],
     "📊 Business Scope Leaked"),
    (["solutions team", "sales team", "account exec", "dedicated team", "loop in"],
     "🏢 Internal Org Structure Leaked"),
    (["email", "voice", "deepfake", "simulation", "sweet spot", "capabilities"],
     "💡 Product Capabilities Disclosed"),
    (["automotive", "logistics", "financial", "industry", "sector"],
     "🏭 Client Industry Confirmed"),
    (["december", "deadline", "submit", "timeline", "evaluation"],
     "📅 Timeline / Procurement Process Disclosed"),
]


def _classify_reply(text: str, event_type: Optional[str] = None) -> List[str]:
    """Return list of disclosure category strings for a given twin reply."""
    categories = []
    text_lower = (text or "").lower()
    # First check event types (wins)
    for keywords, label in _DISCLOSURE_RULES:
        if event_type and event_type in keywords:
            categories.append(label)
            continue
        if any(kw in text_lower for kw in keywords):
            categories.append(label)
    return list(dict.fromkeys(categories))  # deduplicate, preserve order


def _extract_turns(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalize session JSON into a list of turn dicts."""
    # Try known top-level keys
    for key in ("turns", "events", "messages"):
        if key in raw and isinstance(raw[key], list):
            return raw[key]
    return []


def build_timeline(session_id: str, raw: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Build a timeline object from a session log dict or by loading from disk.
    Returns a dict matching Gary's fixtures/reporting.expected.json format.
    """
    if raw is None:
        path = os.path.join(LOGS_DIR, f"{session_id}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Session log not found: {path}")
        with open(path) as f:
            raw = json.load(f)

    turns = _extract_turns(raw)
    target_id = raw.get("target_id", raw.get("subject_id", "unknown"))
    session_start = raw.get("started_at", raw.get("created_at",
                              datetime.now(timezone.utc).isoformat()))

    timeline_turns = []
    for i, turn in enumerate(turns, start=1):
        # Support both old and new log formats
        sent_msg = turn.get("sent") or turn.get("message", {})
        if isinstance(sent_msg, dict):
            attacker_body = sent_msg.get("body", sent_msg.get("text", ""))
            attacker_subject = sent_msg.get("subject")
            attacker_channel = sent_msg.get("channel", raw.get("channel", "email"))
        else:
            attacker_body = str(sent_msg)
            attacker_subject = None
            attacker_channel = raw.get("channel", "email")

        reply_body = turn.get("reply") or turn.get("twin_reply", "")
        event_type = turn.get("event_type") or turn.get("type", "silence")
        events = turn.get("events", [])

        # Collect all event types for classification
        all_event_types = [ev.get("type", "") for ev in events if isinstance(ev, dict)]
        win_event = next((e for e in all_event_types
                          if e in ("attachment.opened", "page.submitted", "link.opened")), None)

        disclosures = _classify_reply(reply_body, win_event or event_type)
        is_win = any(w in " ".join(disclosures) for w in ("Win", "Engagement"))

        ts = turn.get("timestamp") or turn.get("sent_at") or f"turn_{i:02d}"

        timeline_turns.append({
            "turn_no": i,
            "timestamp": ts,
            "attacker": {
                "channel": attacker_channel,
                "subject": attacker_subject,
                "body": attacker_body,
            },
            "twin_reply": reply_body or None,
            "event_type": event_type,
            "win_event": win_event,
            "is_win": is_win,
            "disclosures": disclosures,
        })

    # Aggregate summary
    total_disclosures = [d for t in timeline_turns for d in t["disclosures"]]
    win_turns = [t for t in timeline_turns if t["is_win"]]

    return {
        "session_id": session_id,
        "target_id": target_id,
        "started_at": session_start,
        "total_turns": len(timeline_turns),
        "objectives_hit": [t["win_event"] for t in win_turns if t["win_event"]],
        "incident_reached": bool(win_turns),
        "timeline": timeline_turns,
        "disclosure_summary": list(dict.fromkeys(total_disclosures)),
    }


def save_timeline(session_id: str, timeline: Dict[str, Any]) -> str:
    """Save timeline JSON to logs/runs/{session_id}_timeline.json. Returns path."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    path = os.path.join(LOGS_DIR, f"{session_id}_timeline.json")
    with open(path, "w") as f:
        json.dump(timeline, f, indent=2)
    return path


def print_timeline(timeline: Dict[str, Any]) -> None:
    """Pretty-print the timeline to stdout."""
    sid = timeline["session_id"]
    target = timeline["target_id"]
    print(f"\n{'═'*64}")
    print(f"  SESSION: {sid}  |  TARGET: {target}")
    print(f"  Turns: {timeline['total_turns']}  |  Incident: {'✅ YES' if timeline['incident_reached'] else '❌ No'}")
    print(f"{'═'*64}\n")

    for t in timeline["timeline"]:
        turn = t["turn_no"]
        ts = t["timestamp"]
        ch = t["attacker"]["channel"].upper()
        subj = f" [{t['attacker']['subject']}]" if t["attacker"].get("subject") else ""
        body_preview = (t["attacker"]["body"] or "")[:100].replace("\n", " ")
        reply_preview = (t["twin_reply"] or "(no reply / silence)")[:120].replace("\n", " ")

        print(f"  TURN {turn:02d}  {ts}  [{ch}]{subj}")
        print(f"  ┌ ATTACKER: {body_preview}{'…' if len(t['attacker']['body'] or '') > 100 else ''}")
        print(f"  └ TWIN:     {reply_preview}")
        if t["disclosures"]:
            for d in t["disclosures"]:
                print(f"      ➤ {d}")
        if t["win_event"]:
            print(f"      ★ WIN EVENT: {t['win_event'].upper()}")
        print()

    print(f"  DISCLOSURE SUMMARY:")
    for d in timeline["disclosure_summary"]:
        print(f"    • {d}")
    print(f"\n  Objectives hit: {timeline['objectives_hit'] or 'None yet'}\n")


def main():
    parser = argparse.ArgumentParser(description="STOPReplay Timeline Reporter")
    parser.add_argument("session_id", help="Session ID, e.g. s_c00cecfdaf")
    parser.add_argument("--print-only", action="store_true",
                        help="Only print to stdout, do not save timeline JSON")
    args = parser.parse_args()

    try:
        timeline = build_timeline(args.session_id)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print_timeline(timeline)

    if not args.print_only:
        path = save_timeline(args.session_id, timeline)
        print(f"  Timeline saved → {path}\n")


if __name__ == "__main__":
    main()

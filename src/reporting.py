"""
Timeline & Disclosure Reporter for STOPReplay.
Reads a raw session JSON from logs/runs/{session_id}.json and produces:
  - logs/runs/{session_id}_timeline.json  (Gary's UI format)
  - Prints a human-readable disclosure summary to stdout

Recorded replies are not automatically classified as internal disclosures.
Official outcomes are unavailable in local exports.

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

from src.session_evidence import summarize_events
from src.run_journal import write_snapshot


def _classify_reply(text: str, event_type: Optional[str] = None) -> List[str]:
    """Compatibility helper: reply words are never proof of disclosure."""
    return summarize_events([{"type": event_type}])["observations"]


def _extract_turns(raw):
    for key in ("turns", "messages"):
        if isinstance(raw.get(key), list):
            return raw[key]
    # An events-only export has no outgoing bodies. Group by contact, preserving
    # order; never invent missing messages or count each event as a new contact.
    grouped = {}
    for event in raw.get("events", []):
        if not isinstance(event, dict):
            continue
        contact = event.get("message_id") or event.get("in_reply_to") or event.get("conversation_id")
        key = contact or "unassigned_events"
        turn = grouped.setdefault(key, {"events": [], "contact_id": contact,
                                       "outgoing_available": False})
        turn["events"].append(event)
    return list(grouped.values())


def build_timeline(session_id: str, raw: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Read-only projection. Missing values stay unknown; exports are unverified."""
    if raw is None:
        with open(os.path.join(LOGS_DIR, f"{session_id}.json")) as stream:
            raw = json.load(stream)
    timeline = []
    for i, turn in enumerate(_extract_turns(raw), 1):
        sent = turn.get("sent", turn.get("message"))
        message = sent if isinstance(sent, dict) else {"body": sent}
        events = turn.get("events", [])
        if not events and turn.get("event_type"):
            # Old logs cannot recover event identities or submitted field values.
            events = [{"type": turn["event_type"]}]
        replies = [e for e in events if isinstance(e, dict) and e.get("type") == "reply"]
        reply = turn.get("reply") or turn.get("twin_reply")
        if reply is None and replies:
            reply = "\n\n".join(e.get("body", "") for e in replies)
        evidence = summarize_events(events)
        timeline.append({
            "turn_no": turn.get("turn", i),
            "timestamp": turn.get("timestamp") or turn.get("sent_at"),
            "sent_at": turn.get("sent_at"),
            "story_time_end": turn.get("story_time_end"),
            "conversation_id": turn.get("conversation_id"),
            "conversation_stop": turn.get("conversation_stop"),
            "dialogue": turn.get("dialogue", []),
            "opening": turn.get("opening"),
            "grounding": turn.get("grounding"),
            "evidence_context": turn.get("evidence_context"),
            "contact_id": turn.get("message_id") or turn.get("contact_id"),
            "outgoing_available": sent is not None,
            "attacker": {
                "channel": turn.get("sent_channel", message.get("channel", raw.get("channel"))),
                "subject": turn.get("sent_subject", message.get("subject")),
                "body": message.get("body", message.get("text")),
                "sender": turn.get("sender", message.get("from")),
                "attachment": turn.get("attachment"),
            },
            "twin_reply": reply,
            "reply_channels": list(dict.fromkeys(e.get("channel") for e in replies if e.get("channel"))),
            "event_type": turn.get("event_type"),
            "events": events,
            "win_event": None,
            "is_win": False,
            "disclosures": [],
            "topic_assessment": turn.get("topic_assessment"),
            **evidence,
        })
    return {
        "session_id": session_id,
        "target_id": raw.get("target_id", raw.get("subject_id", "unknown")),
        "started_at": raw.get("started_at", raw.get("created_at")),
        "mode": raw.get("mode", "unknown"),
        "verification": "unverified_recording",
        "total_turns": len(timeline),
        "touches_used": raw.get("touches_used"),
        "objectives_hit": [],
        "incident_reached": None,
        "official_incident": None,
        "timeline": timeline,
        "disclosure_summary": [],
        "topic_assessment": raw.get("topic_assessment"),
        "own_angle_status": "unverified",
        "channel_plan": raw.get("channel_plan"),
        "channels_used": list(dict.fromkeys(t["attacker"]["channel"] for t in timeline)),
        "timing_plan": raw.get("timing_plan"),
        "note": "Recorded observations only. Official outcome and disclosure counts unavailable.",
    }


def save_timeline(session_id: str, timeline: Dict[str, Any]) -> str:
    """Save timeline JSON to logs/runs/{session_id}_timeline.json. Returns path."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    path = os.path.join(LOGS_DIR, f"{session_id}_timeline.json")
    write_snapshot(path, timeline)
    return path


def print_timeline(timeline: Dict[str, Any]) -> None:
    """Pretty-print the timeline to stdout."""
    sid = timeline["session_id"]
    target = timeline["target_id"]
    print(f"\n{'═'*64}")
    print(f"  SESSION: {sid}  |  TARGET: {target}")
    print(f"  Turns: {timeline['total_turns']}  |  Official outcome: unavailable")
    print(f"{'═'*64}\n")

    for t in timeline["timeline"]:
        turn = t["turn_no"]
        ts = t["timestamp"]
        ch = (t["attacker"]["channel"] or "unknown").upper()
        subj = f" [{t['attacker']['subject']}]" if t["attacker"].get("subject") else ""
        body_preview = (t["attacker"]["body"] or "")[:100].replace("\n", " ")
        reply_preview = (t["twin_reply"] or "(no reply / silence)")[:120].replace("\n", " ")

        print(f"  TURN {turn:02d}  {ts}  [{ch}]{subj}")
        print(f"  ┌ ATTACKER: {body_preview}{'…' if len(t['attacker']['body'] or '') > 100 else ''}")
        print(f"  └ TWIN:     {reply_preview}")
        if t["observations"]:
            for d in t["observations"]:
                print(f"      ➤ {d}")
        if t["win_event"]:
            print(f"      ★ WIN EVENT: {t['win_event'].upper()}")
        print()

    print(f"  DISCLOSURE SUMMARY:")
    for d in timeline["disclosure_summary"]:
        print(f"    • {d}")
    print("\n  Official objectives: unavailable; see recorded observations above.\n")


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

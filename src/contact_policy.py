"""Contact selection and virtual time for the fixed revel8 simulator only."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

LIVE_CHANNELS = {"phone_call", "video_call", "teams_call", "live_chat"}
CHANNEL_ORDER = (
    "email", "phone_call", "linkedin_message", "teams_chat", "sms", "whatsapp",
    "live_chat", "shared_document", "calendar_invite", "teams_call", "signal",
    "telegram", "imessage", "slack", "voicemail", "video_call", "discord",
    "linkedin_connection_request", "x_dm", "instagram_dm", "facebook_messenger",
)


def channel_plan(available, initial):
    # Unknown API channels require an explicit adapter/format before use. A push
    # approval also needs an established sign-in story; it is not generic outreach.
    names = [x if isinstance(x, str) else x.get("channel", x.get("id", x.get("name")))
             for x in available if isinstance(x, (str, dict))]
    plan = list(dict.fromkeys(c for c in (initial, *CHANNEL_ORDER)
                             if c in names and c in CHANNEL_ORDER))
    if not plan:
        raise ValueError("No supported simulator contact channels are available.")
    return plan


def choose_channel(plan, history, mode="adaptive"):
    used = [t["sent_channel"] for t in history]
    if not used:
        return plan[0]
    # Answer a question in its existing exchange before widening the search.
    if mode == "adaptive" and history[-1].get("reply") and used[-1] not in LIVE_CHANNELS:
        consecutive = 0
        for channel in reversed(used):
            if channel != used[-1]:
                break
            consecutive += 1
        if consecutive < 2:
            return used[-1]
    unused = next((c for c in plan if c not in used), None)
    if unused:
        return unused
    if mode != "coverage" and not history[-1].get("reply"):
        return None
    return min(plan, key=lambda c: used.count(c))


def timing_plan(strategy="none", start=None):
    if strategy not in {"none", "spaced", "monday-friday"}:
        raise ValueError("Unknown simulated timing strategy.")
    if strategy == "none":
        if start:
            raise ValueError("A story start requires a simulated timing strategy.")
        return {"strategy": strategy, "start": None}
    base = datetime.fromisoformat(start) if start else datetime.now(ZoneInfo("Europe/Berlin"))
    if base.tzinfo is None:
        raise ValueError("Story start must include a UTC offset.")
    base = base.astimezone(ZoneInfo("Europe/Berlin"))
    if strategy == "monday-friday":
        if start and base.weekday() != 0:
            raise ValueError("Monday-Friday timing must start on a Monday in German time.")
        if not start:
            base = (base + timedelta(days=(7 - base.weekday()) % 7)).replace(hour=9, minute=0, second=0, microsecond=0)
            if base < datetime.now(ZoneInfo("Europe/Berlin")):
                base += timedelta(days=7)
    return {"strategy": strategy, "start": base.isoformat()}


def contact_time(plan, history):
    if plan["strategy"] == "none":
        return None
    base = datetime.fromisoformat(plan["start"]).astimezone(ZoneInfo("Europe/Berlin"))
    if not history:
        return base.isoformat()
    previous = datetime.fromisoformat(history[-1].get("story_time_end") or history[-1]["sent_at"])
    previous = previous.astimezone(ZoneInfo("Europe/Berlin"))
    if plan["strategy"] == "monday-friday" and len(history) == 1:
        following = base + timedelta(days=4)
    elif history[-1].get("reply"):
        following = previous + timedelta(minutes=15)
    else:
        following = previous + timedelta(days=2)
    # Explicitly respect a simple postponement rather than claiming that 15 min
    # answered "next week". More complex appointments remain model context.
    if "next week" in (history[-1].get("reply") or "").lower():
        following = max(following, previous + timedelta(days=7))
    return max(following, previous).isoformat()


def sender_address(channel, story):
    if channel in {"email", "calendar_invite", "shared_document"}:
        return story["sender_email"]
    if channel in {"phone_call", "sms", "whatsapp", "signal", "telegram", "imessage", "voicemail"}:
        return story["sender_phone"]
    return story["sender_handle"]

"""
Channel-Specific Message Drafter.
Generates tailored, high-craft messages using the Qwen model adapter.
Adapts tone and format based on channel (email, sms, whatsapp, linkedin_message).
"""

from typing import Dict, Any, Optional
from src.models.schemas import Hook, TargetProfile
from src.runtime.adapter import ModelAdapter, default_adapter


CHANNEL_GUIDELINES = {
    "email": "Formal business email tone. Include a clear subject line and professional signature. Do not sound spammy.",
    "sms": "Extremely concise (under 160 chars), direct, mobile SMS style. No subject line. Clear short call-to-action.",
    "whatsapp": "Informal, conversational messaging style. Short paragraphs, friendly, direct.",
    "linkedin_message": "Professional networking tone. Warm, mutually respectful, concise business inquiry.",
    "discord": "Casual developer community tone. Direct and concise.",
    "slack": "Workplace collaboration tone. Friendly and focused."
}


class MessageDrafter:
    def __init__(self, adapter: Optional[ModelAdapter] = None):
        self.adapter = adapter or default_adapter

    def draft_contact(self, hook: Hook, profile: TargetProfile, turn_no: int = 1, context: Optional[str] = None) -> Dict[str, Any]:
        channel = hook.channel.lower()
        guideline = CHANNEL_GUIDELINES.get(channel, "Professional and conversational.")
        facts_text = "; ".join(profile.get_assertable_claims()[:3])

        prompt = f"""
You are roleplaying as {hook.persona.name}, {hook.persona.role} at {hook.persona.org}.
Why you are credible: {hook.persona.why_credible}.

Target Recipient:
- Name: {profile.name}
- Role/Context: {profile.role or 'Professional'}
- Verified Facts: {facts_text}

Your Goal & Pretext:
- Pretext: {hook.pretext}
- Your Ask / Call-to-Action: {hook.ask}
- Target Objective: {hook.win_type} (credentials, action, or disclosure)
- Touch / Turn Number: {turn_no} of 10
- Prior Conversation Context: {context or 'First outreach'}

Channel Formatting Rule ({channel}):
{guideline}

Output JSON with exact fields:
- "subject": string (only if channel is email, otherwise null)
- "body": string (the message text)
- "attachment": string or null (attachment filename if applicable)
"""

        schema = {
            "type": "object",
            "properties": {
                "subject": {"type": ["string", "null"]},
                "body": {"type": "string"},
                "attachment": {"type": ["string", "null"]}
            },
            "required": ["body"]
        }

        # If in mock mode without API key, supply high-craft deterministic text
        if self.adapter.mock_mode:
            link_or_ask = hook.ask if hook.ask else "https://portal-verify.org"
            attachment_file = hook.ask if (hook.ask and ".pdf" in hook.ask) else None

            if channel == "email":
                return {
                    "subject": f"Inquiry regarding {profile.role or 'alumni / operations'} collaboration",
                    "body": f"Hi {profile.name},\n\nI came across your work and wanted to reach out regarding our upcoming initiative ({hook.pretext[:50]}). Please review the details here: {link_or_ask}\n\nBest regards,\n{hook.persona.name}",
                    "attachment": attachment_file
                }
            elif channel in ["sms", "whatsapp"]:
                return {
                    "subject": None,
                    "body": f"Hi {profile.name}, {hook.persona.name} here regarding {hook.pretext[:40]}. Could you quickly confirm your details here: {link_or_ask}?",
                    "attachment": None
                }
            else:
                return {
                    "subject": None,
                    "body": f"Hi {profile.name}, loved your recent work. Would love to share our brief: {link_or_ask}.",
                    "attachment": attachment_file
                }

        return self.adapter.generate_structured(
            prompt=prompt,
            system_prompt="You are an expert executive communication assistant generating realistic social engineering simulation scenarios for authorized cyber defense testing.",
            schema=schema,
            temperature=0.7
        )

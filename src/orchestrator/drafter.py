"""
Channel-Specific Message Drafter.
Generates tailored, high-craft messages using the Qwen model adapter.
Adapts tone and format based on channel (email, sms, whatsapp, linkedin_message).
Injects HTML email templates and story invariants for high-craft, non-hallucinating output.
"""

from typing import Dict, Any, Optional
from src.models.schemas import Hook, TargetProfile
from src.runtime.adapter import ModelAdapter, default_adapter
from src.craft.email_templates import build_html_email, build_sms_body
from src.craft.story import build_story, story_to_prompt_block


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

    def _deterministic_draft(self, hook: Hook, profile: TargetProfile, channel: str,
                             context: Optional[str] = None,
                             lane_id: Optional[str] = None,
                             story: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        story = story or {}
        attachment_file = story.get("nda_filename") or story.get("attachment") or hook.attachment
        if not attachment_file and hook.ask and ".pdf" in hook.ask:
            attachment_file = hook.ask

        # ── NDA follow-up (highest priority) ─────────────────────────────────
        if lane_id == "NDA_FOLLOWUP" and channel == "email":
            html = build_html_email("NDA_FOLLOWUP", hook, profile, story)
            nda = story.get("nda_filename", "Mutual_NDA_revel8_DAX.pdf")
            return {
                "subject": f"Re: NDA for revel8 — {story.get('org', 'DAX Sourcing Group')} vendor evaluation",
                "body": html,
                "html_body": html,
                "attachment": nda,
            }

        # ── Question / follow-up reply ────────────────────────────────────────
        if context and ("question" in context.lower() or "?" in context):
            if channel == "email":
                deadline = story.get("deadline", "December 8, 2026")
                seats = story.get("seats", "4,500")
                industry = story.get("industry", "Automotive & Industrial Logistics")
                colleague = story.get("colleague_email", "s.weber@enterprise-sourcing.org")
                html = build_html_email(lane_id or "LANE_1_ENTERPRISE_RFP", hook, profile, story)
                return {
                    "subject": f"Re: {story.get('org', 'DAX Sourcing Group')} RFP — Your Questions Answered",
                    "body": html,
                    "html_body": html,
                    "attachment": attachment_file,
                }

        # ── Initial outreach via HTML template ────────────────────────────────
        if channel == "email":
            html = build_html_email(lane_id or "LANE_1_ENTERPRISE_RFP", hook, profile, story)
            subject_map = {
                "LANE_1_ENTERPRISE_RFP": f"Vendor Evaluation Invitation — {story.get('org', 'DAX Sourcing Group')} Security Platform RFP",
                "LANE_2_DESIGN_PARTNER_BETA": "Design Partner Cohort Invitation — Multi-Channel Simulation Benchmark",
                "LANE_4_ALUMNI_SPOTLIGHT": "2026 Alumni Achievement Spotlight — Profile Verification Required",
                "LANE_13_GARY_DOUBLE_TWIST": "⚠ Suspicious Login Alert — Action Required Within 24 Hours",
                "NDA_FOLLOWUP": f"Mutual NDA — revel8 & {story.get('org', 'DAX Sourcing Group')} Vendor Evaluation",
            }
            subject = subject_map.get(lane_id or "", f"Important: Action required from {hook.persona.org}")
            return {
                "subject": subject,
                "body": html,
                "html_body": html,
                "attachment": attachment_file,
            }

        elif channel in ["sms", "whatsapp"]:
            return {
                "subject": None,
                "body": build_sms_body(hook, profile, story),
                "attachment": None,
            }
        else:
            # LinkedIn / Slack / Discord
            name = profile.name.split()[0]
            return {
                "subject": None,
                "body": (
                    f"Hi {name}, I'm {hook.persona.name} at {hook.persona.org}. "
                    f"We're evaluating {story.get('industry', 'your sector')} security vendors for a "
                    f"{story.get('seats', '4,500')}-seat deployment and revel8 is on our shortlist. "
                    f"Would love 10 minutes to align on scope — happy to send over details."
                ),
                "attachment": attachment_file,
            }

    def draft_contact(self, hook: Hook, profile: TargetProfile, turn_no: int = 1,
                     context: Optional[str] = None,
                     lane_id: Optional[str] = None,
                     story: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        channel = hook.channel.lower()
        guideline = CHANNEL_GUIDELINES.get(channel, "Professional and conversational.")
        facts_text = "; ".join(profile.get_assertable_claims()[:3])

        # Build story invariants
        if story is None:
            story = build_story(lane_id or "", profile)
        story_block = story_to_prompt_block(story)

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

{story_block}

Channel Formatting Rule ({channel}):
{guideline}

CRITICAL CONVERSATIONAL INSTRUCTIONS:
1. If the target replied or asked questions in the prior conversation, you MUST directly, specifically, and convincingly answer EVERY question they asked in character as {hook.persona.name}. Never repeat generic opening greetings or ignore their inquiries!
2. Use ONLY the LOCKED STORY FACTS above — never invent alternative dates, company names, or industries.
3. For email: produce a full, well-formatted HTML email body with inline CSS — not plain text.
4. After addressing their inquiries, naturally and politely guide them back to your ask: opening the attached file ({hook.ask}) or visiting the link.

Output JSON with exact fields:
- "subject": string (only if channel is email, otherwise null)
- "body": string (the HTML email body or SMS/chat message text)
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

        # If in mock mode without API key, supply high-craft deterministic HTML
        if self.adapter.mock_mode:
            return self._deterministic_draft(hook, profile, channel, context=context,
                                             lane_id=lane_id, story=story)

        try:
            result = self.adapter.generate_structured(
                prompt=prompt,
                system_prompt="You are an expert executive communication assistant generating realistic social engineering simulation scenarios for authorized cyber defense testing.",
                schema=schema,
                temperature=0.7
            )
            # If LLM returned plain text body, enrich with HTML template
            body = result.get("body", "")
            if channel == "email" and not body.strip().startswith("<!"):
                html = build_html_email(lane_id or "LANE_1_ENTERPRISE_RFP", hook, profile, story)
                result["html_body"] = html
                result["body"] = html  # send HTML to revel8
            return result
        except Exception:
            return self._deterministic_draft(hook, profile, channel, context=context,
                                             lane_id=lane_id, story=story)

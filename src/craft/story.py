"""
Story Invariants — locked facts per lane that the drafter MUST NOT contradict.
Prevents hallucinated dates, wrong industries, wrong colleague names.

Usage:
    from src.craft.story import STORY_DEFAULTS, build_story
    story = build_story("LANE_1_ENTERPRISE_RFP", profile)
"""

from __future__ import annotations
from typing import Dict, Any

# Canonical locked facts — never change these without updating the drafter prompt
STORY_DEFAULTS: Dict[str, Any] = {
    "year": "2026",
    "deadline": "December 8, 2026",
    "industry": "Automotive & Industrial Logistics",
    "seats": "4,500",
    "colleague_name": "Sarah Weber",
    "colleague_email": "s.weber@enterprise-sourcing.org",
    "org": "DAX Sourcing Group",
    "nda_filename": "Mutual_NDA_revel8_DAX.pdf",
    "attachment": "DAX_Security_Vendor_RFP_Matrix_v1.pdf",
    "sender_name": "Sarah Weber",
}

# Lane-specific overrides
_LANE_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "LANE_1_ENTERPRISE_RFP": {
        "sender_persona": "Dr. Michael Kraus",
        "sender_email": "m.kraus@dax-sourcing.de",
        "scope": "email, voice, and deepfake simulation across EU logistics",
        "win_condition": "attachment.opened",
    },
    "NDA_FOLLOWUP": {
        "sender_persona": "Sarah Weber",
        "sender_email": "s.weber@enterprise-sourcing.org",
        "win_condition": "attachment.opened",
        "nda_filename": "Mutual_NDA_revel8_DAX.pdf",
    },
    "LANE_2_DESIGN_PARTNER_BETA": {
        "industry": "Financial Services & FinTech",
        "org": "European FinTech Collective",
        "attachment": "fintech_simulation_benchmark_v2.pdf",
        "win_condition": "disclosure",
    },
    "LANE_4_ALUMNI_SPOTLIGHT": {
        "industry": "Academic / Alumni",
        "landing_url": "https://university-alumni-network.org/verify",
        "win_condition": "page.submitted",
    },
    "LANE_13_GARY_DOUBLE_TWIST": {
        "industry": "Corporate Security",
        "landing_url": "https://account-verify-support.net/restore-access",
        "win_condition": "page.submitted",
    },
}


def build_story(lane_id: str, profile=None) -> Dict[str, Any]:
    """
    Returns a merged story dict: defaults + lane overrides + profile-derived fields.
    This dict is injected into every drafter prompt as LOCKED STORY FACTS.
    """
    story = dict(STORY_DEFAULTS) if lane_id in {"LANE_1_ENTERPRISE_RFP", "LANE_2_DESIGN_PARTNER_BETA", "NDA_FOLLOWUP"} else {"year": STORY_DEFAULTS["year"]}
    story.update(_LANE_OVERRIDES.get(lane_id, {}))
    from src.orchestrator.strategy_planner import LANES_CATALOG
    entry = LANES_CATALOG.get(lane_id)
    if entry:
        persona = entry["persona"]
        story["org"] = persona.org
        story["sender_name"] = persona.name
        story["sender_role"] = persona.role
        story["attachment"] = entry.get("attachment")
        story["landing_url"] = entry.get("landing_page")
        if "sender_email" not in _LANE_OVERRIDES.get(lane_id, {}):
            import re
            local = re.sub(r"[^a-z0-9]+", ".", persona.name.lower()).strip(".")
            domain = re.sub(r"[^a-z0-9]+", "-", persona.org.lower()).strip("-")
            story["sender_email"] = f"{local}@{domain}.com"
    if profile:
        story["target_name"] = getattr(profile, "name", "")
        story["target_id"] = getattr(profile, "subject_id", "")
        story["target_org"] = getattr(profile, "organization", None) or "your organization"
    return story


def story_to_prompt_block(story: Dict[str, Any]) -> str:
    """
    Formats story dict into a prompt injection block for the drafter.
    The drafter MUST include this verbatim in every LLM system prompt.
    """
    import json
    return ("LOCKED SCENARIO DETAILS (fictional scenario, not verified target facts):\n"
            + json.dumps(story, ensure_ascii=False, sort_keys=True)
            + "\nPreserve these details. Do not invent values for missing fields.")

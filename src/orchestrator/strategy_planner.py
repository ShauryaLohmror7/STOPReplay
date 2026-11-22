"""
Dynamic Strategy Selector and Attack Planner.
Translates verified facts into Attack Lanes defined in ATTACK_LANES.md.
Completely dynamic — NO hardcoded founder strings.
"""

from typing import List, Dict, Any, Optional
from src.models.schemas import TargetProfile, Fact, Hook, Persona


# Metadata for the 12 Attack Lanes
LANES_CATALOG: Dict[str, Dict[str, Any]] = {
    "LANE_1_ENTERPRISE_RFP": {
        "title": "Enterprise Procurement RFP Matrix",
        "domain": "sales",
        "win_type": "action",
        "primary_channel": "email",
        "persona": Persona("Dr. Michael Kraus", "Head of Enterprise Sourcing", "DAX Sourcing Group", "Large enterprise procurement buyer"),
        "attachment": "DAX_Security_Vendor_RFP_Matrix_v1.pdf"
    },
    "LANE_2_DESIGN_PARTNER_BETA": {
        "title": "Design Partner Latency Cohort",
        "domain": "product",
        "win_type": "disclosure",
        "primary_channel": "linkedin_message",
        "persona": Persona("Sarah Vogel", "VP Product Innovation", "European FinTech Collective", "Innovation director testing multi-channel security"),
        "attachment": "fintech_simulation_benchmark_v2.pdf"
    },
    "LANE_3_CVE_ASYNC_LEAK": {
        "title": "Async Websocket Thread Leak Advisory",
        "domain": "engineering",
        "win_type": "action",
        "primary_channel": "email",
        "persona": Persona("Alexej Berg", "Security Researcher", "Runtime Reliability Labs", "Open-source contributor and async benchmark maintainer"),
        "attachment": "websocket_leak_poc.pdf"
    },
    "LANE_4_ALUMNI_SPOTLIGHT": {
        "title": "Alumni Spotlight & Directory Verification",
        "domain": "academic",
        "win_type": "credential",
        "primary_channel": "email",
        "persona": Persona("Dr. Claudia Richter", "Director of Alumni Affairs", "University Alumni Foundation", "Official alumni journal coordinator"),
        "landing_page": "https://university-alumni-network.org/verify",
        "landing_title": "Alumni Directory Verification Portal",
        "landing_fields": ["email", "password", "graduation_year"]
    },
    "LANE_5_SPORTS_ROSTER": {
        "title": "Sports League Timing & Bib Roster",
        "domain": "sports",
        "win_type": "action",
        "primary_channel": "whatsapp",
        "persona": Persona("Florian Meier", "Event Coordinator", "Munich Endurance League", "Race timing coordinator"),
        "attachment": "wave_start_roster_v2.pdf"
    },
    "LANE_6_PROFESSIONAL_CPD_AUDIT": {
        "title": "Continuing Professional Education Audit",
        "domain": "compliance",
        "win_type": "credential",
        "primary_channel": "email",
        "persona": Persona("Accreditation Registrar", "Compliance Officer", "European Professional Standards Registry", "Official certification auditor"),
        "landing_page": "https://professional-standards-board.org/cpd-audit/login",
        "landing_title": "CPD Standards Compliance Portal",
        "landing_fields": ["credential_id", "email", "password"]
    },
    "LANE_7_CIVIC_STREET_PETITION": {
        "title": "Municipal Street Works & Resident Feedback",
        "domain": "civic",
        "win_type": "action",
        "primary_channel": "email",
        "persona": Persona("District Advisory Council", "Civic Ombudsman", "Urban Planning Authority", "Municipal public works notification"),
        "attachment": "street_works_planning_notice.pdf"
    },
    "LANE_8_FORMER_COLLEAGUE": {
        "title": "Former Colleague Culture & Stack Reconnect",
        "domain": "relationship",
        "win_type": "disclosure",
        "primary_channel": "linkedin_message",
        "persona": Persona("Lukas Brandt", "Senior Consultant", "Former Colleague", "Worked at previous employer 3 years ago"),
        "attachment": None
    },
    "LANE_9_CREATIVE_CONTRIBUTOR_RELEASE": {
        "title": "Educational Contributor Licensing Agreement",
        "domain": "creative",
        "win_type": "action",
        "primary_channel": "email",
        "persona": Persona("Elena Rostova", "Senior Editor", "European Media Publishing Group", "Anthology commissioning editor"),
        "attachment": "contributor_licensing_agreement_draft.pdf"
    },
    "LANE_10_SPECIALIST_ADVISORY": {
        "title": "High-Hourly Private Equity Consultation",
        "domain": "consulting",
        "win_type": "credential",
        "primary_channel": "linkedin_message",
        "persona": Persona("Hannah Bergmann", "Research Director", "AlphaSearch Expert Network", "Matching PE investors with domain specialists"),
        "landing_page": "https://expert-network-onboarding.com/advisor",
        "landing_title": "AlphaSearch Expert Network Advisor Portal",
        "landing_fields": ["email", "password", "iban"]
    },
    "LANE_11_CONSUMER_SETTLEMENT": {
        "title": "Consumer Disruption Restitution Claim",
        "domain": "consumer",
        "win_type": "credential",
        "primary_channel": "sms",
        "persona": Persona("Claims Administrator", "Legal Settlement Officer", "EU Passenger Compensation Bureau", "Court-appointed claim administrator"),
        "landing_page": "https://eu-consumer-settlement-portal.net/claims",
        "landing_title": "EU Consumer Compensation Bureau",
        "landing_fields": ["claimant_name", "email", "iban", "pin"]
    },
    "LANE_12_PRIORITY_COURIER": {
        "title": "Priority Courier Parcel Gate Code Reschedule",
        "domain": "general",
        "win_type": "credential",
        "primary_channel": "sms",
        "persona": Persona("CityExpress Logistics", "Automated Dispatch System", "CityExpress Courier", "Local courier delivery dispatch"),
        "landing_page": "https://cityexpress-dispatch-hub.net/track",
        "landing_title": "CityExpress Logistics Parcel Reschedule",
        "landing_fields": ["door_code", "email", "password"]
    },
    "LANE_13_GARY_DOUBLE_TWIST": {
        "title": "Gary's Double Twist: Quarantined Suspicious Login Alert",
        "domain": "security_twist",
        "win_type": "credential",
        "primary_channel": "email",
        "persona": Persona("IT Security Incident Desk", "Automated SecOps", "Corporate Cloud Security Center", "External corporate identity provider"),
        "landing_page": "https://account-verify-support.net/restore-access",
        "landing_title": "Cloud Security Defense: Restore Access",
        "landing_fields": ["email", "password", "verification_code"]
    },
    "LANE_14_SECURITY_TRAINING_REWARD": {
        "title": "Mandatory Cyber Security Training & Bonus Voucher",
        "domain": "employee_compliance",
        "win_type": "credential",
        "primary_channel": "email",
        "persona": Persona("Corporate HR & Compliance", "Training Administrator", "Employee Engagement Team", "Internal corporate perks and training portal"),
        "landing_page": "https://employee-perks-reward-portal.com/bonus-claim",
        "landing_title": "Employee Engagement Perks Portal",
        "landing_fields": ["employee_id", "company_email", "password"]
    }
}


class StrategySelector:
    """Selects the best attack lane dynamically based on target facts."""

    def __init__(self, source_metadata=None):
        self.source_metadata = source_metadata

    def assess(self, profile, history=(), *, as_of=None):
        from src.orchestrator.topic_ranking import rank_topics
        return rank_topics(profile, source_metadata=self.source_metadata, history=history, as_of=as_of)

    def select_lane(self, profile: TargetProfile) -> str:
        return self.assess(profile)["selected_lane"]

    def build_hook(self, lane_id: str, profile: TargetProfile) -> Hook:
        catalog_entry = LANES_CATALOG[lane_id]
        assessment = self.assess(profile)
        candidate = next((c for c in assessment["candidates"] if c["lane_id"] == lane_id), None)
        evidence = candidate["evidence"] if candidate else []
        facts_summary = "; ".join(e["claim"] for e in evidence[:3])

        return Hook(
            id=f"hook_{lane_id.lower()}_{profile.subject_id}",
            subject=profile.subject_id,
            pretext=f"{catalog_entry['title']} tailored for {profile.name}. Available public-source claims: {facts_summary}",
            persona=catalog_entry["persona"],
            ask=catalog_entry.get("attachment") or catalog_entry.get("landing_page") or "Internal disclosure inquiry",
            win_type=catalog_entry["win_type"],
            channel=catalog_entry["primary_channel"],
            required_facts=[e["fact_id"] for e in evidence],
            ramp=1,
            status="active",
            landing_page_url=catalog_entry.get("landing_page"),
            landing_page_fields=catalog_entry.get("landing_fields", ["email", "password"]),
            landing_page_title=catalog_entry.get("landing_title", catalog_entry["title"]),
            attachment=catalog_entry.get("attachment")
        )

"""
Data Bridge connecting Shaurya's Attack Controller with:
1. Cem's Database layer (stopreplay_db.Storage)
2. Adrian's OSINT Collection & Portal Generator (stopreplay_collect.portal)

Supports both live Supabase connection (when DATABASE_URL is configured)
and offline baseline facts fallback for unit tests and local simulation.
"""

from __future__ import annotations
import os
from typing import List, Dict, Any, Optional

from src.models.schemas import Fact, TargetProfile
from stopreplay_collect.portal import generate_login_portal

# Pre-populated OSINT baseline facts from Adrian & Cem's collection handoff
FOUNDER_BASELINES = {
    "julius": {
        "name": "Julius Muth",
        "role": "Co-Founder & Co-CEO (Sales / Go-To-Market)",
        "org": "revel8",
        "claims": [
            ("role", "Co-Founder & Co-CEO heading sales and go-to-market at revel8"),
            ("event", "Presented keynote on enterprise workforce simulation at Bits & Pretzels"),
            ("credential", "Stanford University Graduate School of Business alumni"),
            ("interest", "B2B enterprise cybersecurity procurement and DAX company pilots"),
            ("contact", "julius@revel8.ai (target_email)"),
            ("other", "https://revel8.ai/assets/logo.png (company_logo)")
        ]
    },
    "tom": {
        "name": "Tom Müller",
        "role": "Co-Founder & Co-CEO (Product)",
        "org": "revel8",
        "claims": [
            ("role", "Co-Founder & Co-CEO heading product and UX design at revel8"),
            ("event", "Featured speaker on multi-channel threat simulation on YouTube podcasts"),
            ("project", "Co-authored arXiv research paper on generative behavioral attack simulations"),
            ("interest", "Sub-second LLM inference latency and synthetic prompt defenses"),
            ("contact", "tom@revel8.ai (target_email)")
        ]
    },
    "robert": {
        "name": "Robert Seilbeck",
        "role": "Co-Founder & CTO",
        "org": "revel8",
        "claims": [
            ("role", "Co-Founder & CTO heading engineering architecture at revel8"),
            ("project", "Active maintainer of async Python orchestration frameworks on GitHub"),
            ("event", "Presented ACM research paper on real-time agentic streaming loops"),
            ("contact", "Munich, Germany office (location)"),
            ("contact", "robert@revel8.ai (target_email)")
        ]
    }
}


class DataBridge:
    """Bridges OSINT extraction, Supabase persistence, and the attack engine."""

    def __init__(self, db_storage=None):
        self.storage = db_storage
        if not self.storage and os.getenv("DATABASE_URL"):
            try:
                from stopreplay_db import Storage, db
                conn = db.connect()
                self.storage = Storage(conn)
            except Exception:
                self.storage = None

    def get_target_profile(self, target_id: str, source_run: str = "recon") -> TargetProfile:
        """
        Loads facts from Cem's database (or baseline fallback), generates
        an authentic landing page via Adrian's portal generator, and returns
        a consolidated TargetProfile.
        """
        raw_facts: List[Dict[str, Any]] = []

        # 1. Try querying live Supabase database
        if self.storage:
            try:
                raw_facts = self.storage.get_facts(source_run=source_run, subject=target_id)
            except Exception:
                raw_facts = []

        # 2. If no DB or empty, load baseline facts
        if not raw_facts and target_id.lower() in FOUNDER_BASELINES:
            meta = FOUNDER_BASELINES[target_id.lower()]
            facts_list = []
            for i, (cat, claim) in enumerate(meta["claims"]):
                facts_list.append(Fact(
                    id=f"fact_{target_id}_{i+1}",
                    subject=target_id,
                    claim=claim,
                    category=cat,
                    source_run=source_run,
                    source_ref=f"baseline-{target_id}",
                    assertable=True
                ))
            profile = TargetProfile(
                subject_id=target_id,
                name=meta["name"],
                role=meta["role"],
                organization=meta["org"],
                facts=facts_list
            )
            portal = generate_login_portal([f.to_dict() for f in facts_list])
            profile.organization = meta["org"]
            return profile

        # 3. Convert DB rows to Fact schemas
        facts_list = []
        name = target_id.capitalize()
        role = "Professional"
        for row in raw_facts:
            facts_list.append(Fact(
                id=str(row.get("id")),
                subject=row.get("subject", target_id),
                claim=row.get("claim", ""),
                category=row.get("category", "other"),
                source_run=row.get("source_run", source_run),
                source_ref=row.get("source_ref", ""),
                assertable=row.get("assertable", True)
            ))
            if row.get("category") == "role" and "co-founder" in row.get("claim", "").lower():
                role = row.get("claim")

        profile = TargetProfile(
            subject_id=target_id,
            name=name,
            role=role,
            facts=facts_list
        )
        return profile

    def generate_portal_for_target(self, target_id: str, profile: TargetProfile) -> Dict[str, Any]:
        """
        Invokes Adrian's authentic landing page generator to create
        a brand-tailored SSO login portal for POST /v1/sessions/{sid}/pages.
        """
        raw_facts = [f.to_dict() for f in profile.facts]
        return generate_login_portal(raw_facts, target_name=profile.name)

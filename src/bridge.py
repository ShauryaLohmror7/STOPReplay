"""
Bridge between Database / OSINT Collection layer and the Attack Orchestrator.
Allows RunController to load TargetProfiles directly from Supabase / Postgres facts,
with graceful fallbacks for verified practice targets (julius, tom, robert).
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from src.models.schemas import Fact, TargetProfile


# Canonical practice targets from revel8 challenge documentation
VERIFIED_FOUNDER_SEEDS: Dict[str, Dict[str, Any]] = {
    "julius": {
        "name": "Julius Muth",
        "role": "Co-Founder & Co-CEO (Sales & Go-To-Market)",
        "org": "revel8",
        "facts": [
            {
                "id": "f_seed_julius_1",
                "subject": "julius",
                "claim": "Co-Founder and Co-CEO heading sales, commercial revenue and enterprise pilots at revel8",
                "category": "role",
                "source_run": "recon",
                "source_ref": "seed:julius:role",
                "assertable": True,
                "confidence": 1.0,
                "sensitivity": "public"
            },
            {
                "id": "f_seed_julius_2",
                "subject": "julius",
                "claim": "Presented enterprise pilot defense at Bits & Pretzels and evaluating B2B vendor RFP shortlist",
                "category": "event",
                "source_run": "recon",
                "source_ref": "seed:julius:event",
                "assertable": True,
                "confidence": 0.95,
                "sensitivity": "public"
            },
            {
                "id": "f_seed_julius_3",
                "subject": "julius",
                "claim": "Graduated from Stanford University with focus on business and management",
                "category": "credential",
                "source_run": "recon",
                "source_ref": "seed:julius:edu",
                "assertable": True,
                "confidence": 0.9,
                "sensitivity": "public"
            }
        ]
    },
    "tom": {
        "name": "Tom Müller",
        "role": "Co-Founder & Co-CEO (Product & UX)",
        "org": "revel8",
        "facts": [
            {
                "id": "f_seed_tom_1",
                "subject": "tom",
                "claim": "Co-Founder & Co-CEO heading product strategy, design and UX at revel8",
                "category": "role",
                "source_run": "recon",
                "source_ref": "seed:tom:role",
                "assertable": True,
                "confidence": 1.0,
                "sensitivity": "public"
            },
            {
                "id": "f_seed_tom_2",
                "subject": "tom",
                "claim": "Delivered technical talk on multi-channel AI simulation workflows and user testing cohorts",
                "category": "project",
                "source_run": "recon",
                "source_ref": "seed:tom:talk",
                "assertable": True,
                "confidence": 0.95,
                "sensitivity": "public"
            }
        ]
    },
    "robert": {
        "name": "Robert Seilbeck",
        "role": "Co-Founder & CTO (Engineering)",
        "org": "revel8",
        "facts": [
            {
                "id": "f_seed_robert_1",
                "subject": "robert",
                "claim": "Co-Founder & CTO heading engineering, async agent architecture and software security at revel8",
                "category": "role",
                "source_run": "recon",
                "source_ref": "seed:robert:role",
                "assertable": True,
                "confidence": 1.0,
                "sensitivity": "public"
            },
            {
                "id": "f_seed_robert_2",
                "subject": "robert",
                "claim": "Open-source maintainer and speaker on async Python websocket streaming architectures",
                "category": "project",
                "source_run": "recon",
                "source_ref": "seed:robert:oss",
                "assertable": True,
                "confidence": 0.95,
                "sensitivity": "public"
            }
        ]
    }
}


# Preserve historical seed rows for compatibility, but only the organizer's
# supplied role descriptions are assertable. Extra biographical claims are unverified.
_DOCUMENTED_ROLES = {
    "julius": "Co-Founder & Co-CEO, sales at revel8",
    "tom": "Co-Founder & Co-CEO, product at revel8",
    "robert": "Co-Founder & CTO at revel8",
}
for _subject, _seed in VERIFIED_FOUNDER_SEEDS.items():
    _seed["role"] = _DOCUMENTED_ROLES[_subject]
    for _fact in _seed["facts"]:
        if _fact["category"] == "role":
            _fact["claim"] = _DOCUMENTED_ROLES[_subject]
            _fact["source_ref"] = "organizer:challenge:practice-targets"
        else:
            _fact["assertable"] = False
            _fact["confidence"] = 0.0



def build_profile_from_db(
    storage: Any,
    subject_id: str,
    source_run: str = "recon",
    name: Optional[str] = None
) -> TargetProfile:
    """
    Constructs a TargetProfile by querying facts from stopreplay_db.Storage.
    """
    raw_facts = storage.get_facts(source_run=source_run, subject=subject_id)
    if not raw_facts:
        return TargetProfile(subject_id=subject_id, name=name or subject_id.capitalize())

    facts: List[Fact] = []
    inferred_role = None
    inferred_name = name

    for rf in raw_facts:
        source = storage.get_source(source_run, rf.get("source_ref", ""))
        public_source = bool(source and source.get("origin") in {
            "public_web", "public_talk", "company_site", "social_post", "profile_bio",
            "github", "public_agenda"})
        f = Fact(
            id=str(rf["id"]),
            subject=rf["subject"],
            claim=rf["claim"],
            category=rf["category"],
            source_run=rf.get("source_run", source_run),
            source_ref=rf.get("source_ref", ""),
            assertable=(rf.get("assertable") is True and rf.get("status") == "active"
                        and rf.get("sensitivity") == "public"
                        and public_source),
            confidence=float(rf.get("confidence") or 0.0),
            sensitivity=rf.get("sensitivity", "public"),
            corroboration=rf.get("corroboration") or [],
            enables=rf.get("enables") or [],
            entities=rf.get("entities") or [],
            status=rf.get("status", "active"),
            superseded_by=rf.get("superseded_by")
        )
        facts.append(f)
        if f.assertable and f.category == "role" and not inferred_role:
            inferred_role = f.claim
        if f.assertable and f.claim.startswith("full_name:") and not inferred_name:
            inferred_name = f.claim.split(":")[-1].strip()

    final_name = inferred_name or subject_id.capitalize()
    return TargetProfile(
        subject_id=subject_id,
        name=final_name,
        role=inferred_role,
        facts=facts
    )


def get_target_profile(
    subject_id: str,
    storage: Optional[Any] = None,
    source_run: str = "recon",
    name: Optional[str] = None
) -> TargetProfile:
    """
    Unified entry point to get a TargetProfile:
    1. Uses storage facts if available.
    2. Falls back to verified seed facts for founders.
    3. Generates a clean fallback profile for dynamic targets.
    """
    if storage is not None:
        try:
            return build_profile_from_db(storage, subject_id, source_run=source_run, name=name)
        except Exception as e:
            print(f"[Bridge] Notice: Could not read facts from storage ({e}). Using seed profile.")

    # Check verified founder seed
    sid_lower = subject_id.lower()
    if sid_lower in VERIFIED_FOUNDER_SEEDS:
        seed = VERIFIED_FOUNDER_SEEDS[sid_lower]
        fact_objs = [Fact(**f) for f in seed["facts"]]
        return TargetProfile(
            subject_id=sid_lower,
            name=seed["name"],
            role=seed["role"],
            organization=seed["org"],
            facts=fact_objs
        )

    # Dynamic target fallback
    return TargetProfile(
        subject_id=subject_id,
        name=name or subject_id.capitalize(),
        role="Target Professional",
        facts=[]
    )


def recon_and_build_profile(
    storage: Any,
    subject_id: str,
    seed_text: str,
    source_run: str = "recon",
    name: Optional[str] = None
) -> TargetProfile:
    """
    Runs multi-channel OSINT collection via stopreplay_collect and returns
    the persisted TargetProfile from the database.
    """
    from stopreplay_collect.recon import run_recon
    run_recon(storage, subject_id, seed_text, source_run=source_run, authorized=False)
    return build_profile_from_db(storage, subject_id, source_run=source_run, name=name)


def profile_from_scenario(scenario, target_id, *, storage=None, source_run="recon", research=False):
    """Consume organizer identity and existing public facts without changing schemas."""
    target = next((t for t in scenario.get("targets", []) if t.get("id") == target_id), None)
    if target is None:
        raise ValueError("Target is not in the selected open scenario.")
    if research:
        if storage is None:
            raise ValueError("Research requires configured storage.")
        recon_and_build_profile(storage, target_id,
                                f"{target['name']}, {target.get('role', '')}, {scenario.get('company', '')}",
                                source_run=source_run, name=target["name"])
    # Never silently replace a failed storage read with seed facts in this path.
    profile = (build_profile_from_db(storage, target_id, source_run, target["name"])
               if storage is not None else TargetProfile(target_id, target["name"]))
    profile.name = target["name"]
    profile.role = target.get("role")
    profile.organization = scenario.get("company")
    return profile

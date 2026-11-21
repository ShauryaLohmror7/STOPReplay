"""
Shared data models for STOPReplay.
Directly aligns with Cem + Adrian's revised database schema specification
and the Target API concepts.
"""

from __future__ import annotations
import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Union


@dataclass
class Source:
    """Preserved raw source and origin provenance."""
    run_id: str
    source_ref: str
    origin: str  # public_web|public_talk|company_site|social_post|profile_bio|github|public_agenda|file_upload|simulator_event|inferred
    locator: str  # exact passage, page, timestamp, or line
    excerpt: str  # preserved passage for verbatim citation validation
    url: Optional[str] = None
    file_ref: Optional[str] = None
    publisher: Optional[str] = None
    content_sha256: Optional[str] = None
    observed_on: Optional[str] = None
    retrieved_on: Optional[str] = None
    simulator_ref: Optional[Dict[str, Any]] = None  # {session_id, message_id, event_type}

    def __post_init__(self):
        if not self.content_sha256 and self.excerpt:
            self.content_sha256 = hashlib.sha256(self.excerpt.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Fact:
    """An atomic verified piece of public intelligence about a target."""
    id: str
    subject: str  # e.g. "julius", "tom", "robert" or target identifier
    claim: str
    category: str  # role|event|project|relationship|interest|contact|credential|other
    source_run: str
    source_ref: str
    assertable: bool = True  # Safe to say out loud, not creepy
    confidence: float = 1.0
    sensitivity: str = "public"  # public|semi_public|sensitive|private
    corroboration: List[str] = field(default_factory=list)
    enables: List[str] = field(default_factory=list)  # hook_ids unlocked
    entities: List[str] = field(default_factory=list)
    status: str = "active"  # active|stale|refuted|superseded
    superseded_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Persona:
    name: str
    role: str
    org: str
    why_credible: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Hook:
    """A (pretext + ask) attack angle built from facts."""
    id: str
    subject: str
    pretext: str
    persona: Persona
    ask: str
    win_type: str  # credential|disclosure|action|other
    channel: str   # MUST be from GET /v1/channels
    required_facts: List[str] = field(default_factory=list)
    ramp: int = 1  # 1 = rapport/probe, 2 = mutual context, 3 = payload delivery
    status: str = "candidate"  # candidate|active|burned|succeeded

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['persona'] = self.persona.to_dict() if isinstance(self.persona, Persona) else self.persona
        return d


@dataclass
class Event:
    """Raw recorded simulator event or incoming data record."""
    run_id: str
    event_id: str
    sequence: int
    source_ref: str
    text: str
    content_hash: Optional[str] = None

    def __post_init__(self):
        if not self.content_hash and self.text:
            self.content_hash = hashlib.sha256(self.text.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FindingEvidence:
    ordinal: int
    event_id: str
    source_ref: str
    quote: str
    quote_start: Optional[int] = None
    quote_end: Optional[int] = None


@dataclass
class Finding:
    finding_id: str
    run_id: str
    analysis_id: str
    event_id: str
    sequence: int
    statement: str
    kind: str  # observation|inference
    status: str = "supported"  # supported|unresolved
    uncertainty: Optional[str] = None
    revises: Optional[str] = None
    finding_index: int = 0
    canonical_hash: Optional[str] = None
    evidence: List[FindingEvidence] = field(default_factory=list)


@dataclass
class Turn:
    """Committed replay checkpoint owned by Shaurya's controller."""
    run_id: str
    analysis_id: str
    turn_no: int
    event_id: str
    committed_at: str
    finding_id: Optional[str] = None


@dataclass
class TargetProfile:
    """Consolidated target representation passed to strategy planning."""
    subject_id: str
    name: str
    role: Optional[str] = None
    organization: Optional[str] = None
    professional_domain: str = "general"  # sales|product|engineering|academic|general
    facts: List[Fact] = field(default_factory=list)
    candidate_hooks: List[Hook] = field(default_factory=list)
    touches_used: int = 0
    touch_budget: int = 10  # 30 in practice, 10 in eval

    def get_assertable_claims(self) -> List[str]:
        return [f.claim for f in self.facts if f.assertable and f.status == "active"]

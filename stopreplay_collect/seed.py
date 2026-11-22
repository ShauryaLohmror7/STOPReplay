"""Seed analysis: turn arbitrary operator-supplied target detail into facts.

Input can be anything ("Julius Muth, revel8.ai Co-founder and Co-CEO sales",
"Jane Doe born 1987 Munich", ...). We analyse it deterministically into the
UNIVERSAL Fact structure (no new schema), using a `key: value` claim convention
so each attribute stays machine-findable, and we derive disambiguation anchors:

  - strong anchors (org term, domains)  -> used as must_include / include_domains
  - scoring signals (date_of_birth)     -> stored as facts, NOT used as hard filters
                                           (a page rarely prints the exact date)

The fact exists and is discoverable; the attack layer links it to a hook via the
schema's existing facts.enables / hooks.required_facts. This layer never builds
hooks. LLM-based parsing can replace these heuristics later via the shared runtime.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .base import CollectionAdapter
from .models import CollectionOutput, DraftFact, DraftSource, ResearchRequest

_DOMAIN_RE = re.compile(
    r"\b([a-z0-9][a-z0-9-]*\.(?:ai|com|io|co|org|net|dev|app|gg|me|de|uk|eu|us))\b", re.I)
_NAME_RE = re.compile(r"^([A-ZÀ-Þ][\wÀ-ÿ.'-]+(?:\s+[A-ZÀ-Þ][\wÀ-ÿ.'-]+){0,3})")
_DOB_RE = re.compile(
    r"\b(born|dob|d\.o\.b\.?|birth(?:day|date)?)\b[:\s]*"
    r"(\d{4}-\d{2}-\d{2}|\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{4})", re.I)
_ROLE_WORDS = ("co-founder", "founder", "co-ceo", "ceo", "cto", "coo", "cfo",
               "cmo", "chief", "president", "vp", "vice president", "head of",
               "director", "manager", "engineer", "lead", "partner", "owner")


@dataclass
class SeedAnalysis:
    subject: str
    name: str | None = None
    org: str | None = None
    query: str = ""
    must_include: list[str] = field(default_factory=list)
    include_domains: list[str] = field(default_factory=list)
    facts: list[DraftFact] = field(default_factory=list)
    source: DraftSource | None = None


def analyze_seed(subject: str, text: str) -> SeedAnalysis:
    text = (text or "").strip()
    a = SeedAnalysis(subject=subject)
    source_ref = f"seed:{subject}"
    a.source = DraftSource(
        source_ref=source_ref, origin="file_upload", publisher="operator-supplied",
        locator="operator-supplied seed", excerpt=text)

    # name = leading capitalised words of the first segment
    first_seg = text.split(",", 1)[0].strip() if "," in text else text
    m = _NAME_RE.match(first_seg)
    if m:
        a.name = m.group(1).strip()
        a.facts.append(_fact(subject, f"full_name: {a.name}", "other", source_ref))

    # domains -> include_domains + org term (domain without TLD) as a strong anchor
    for dom in dict.fromkeys(d.lower() for d in _DOMAIN_RE.findall(text)):
        a.include_domains.append(dom)
        a.facts.append(_fact(subject, f"company_domain: {dom}", "other", source_ref))
        org_term = dom.split(".")[0]
        if org_term and org_term not in a.must_include:
            a.must_include.append(org_term)
            a.org = a.org or org_term

    # date of birth -> stored as a (private) fact; NOT an anchor
    dob = _DOB_RE.search(text)
    if dob:
        a.facts.append(_fact(subject, f"date_of_birth: {dob.group(2)}", "other",
                             source_ref, sensitivity="private"))

    # role / description = what's left after removing name and domains
    rest = text
    if a.name:
        rest = rest.replace(a.name, "", 1)
    for dom in a.include_domains:
        rest = re.sub(re.escape(dom), "", rest, flags=re.I)
    if dob:
        rest = rest.replace(dob.group(0), "")
    rest = re.sub(r"\s+", " ", rest).strip(" ,.;-")
    if rest and any(w in rest.lower() for w in _ROLE_WORDS):
        claim = f"{rest} at {a.org}" if a.org and a.org not in rest.lower() else rest
        a.facts.append(_fact(subject, claim, "role", source_ref))
    elif rest:
        a.facts.append(_fact(subject, rest, "other", source_ref))

    a.query = " ".join(x for x in (a.name, a.org) if x).strip() or (a.name or subject)
    return a


def _fact(subject: str, claim: str, category: str, source_ref: str,
          sensitivity: str = "public") -> DraftFact:
    return DraftFact(subject=subject, claim=claim, category=category,
                     source_ref=source_ref, confidence=0.9, assertable=True,
                     assertable_why="operator-supplied seed", sensitivity=sensitivity)


class SeedAdapter(CollectionAdapter):
    """Feeds the analysed seed (source + facts) through the normal pipeline so the
    guardrails, validation and reporting apply uniformly."""
    name = "seed"

    def __init__(self, text: str):
        self.text = text

    def collect(self, request: ResearchRequest) -> CollectionOutput:
        a = analyze_seed(request.subject, self.text)
        out = CollectionOutput()
        if a.source:
            out.sources.append(a.source)
        out.facts.extend(a.facts)
        return out

"""Turn stored (scraped) sources into facts.

Conservative, deterministic, high-precision: it emits the facts that are reliable
to pull from a page without a model — the target's *profiles/handles* (which
platforms they're on: the most useful recon signal for the attack side) and
*presence on the company's own site*. Each fact cites the page it came from, and
we only emit it when the page actually matches the target (last name present),
so a company page that never names the person yields nothing.

Richer, free-text fact extraction (titles, bios, relationships from prose) is the
model-backed step that plugs into the shared runtime later; this stays precise.
"""
from __future__ import annotations

import re

from .models import DraftFact
from .util import domain_of

PROFILE_PLATFORMS = {
    "linkedin.com": "linkedin",
    "crunchbase.com": "crunchbase",
    "github.com": "github",
    "twitter.com": "x",
    "x.com": "x",
    "xing.com": "xing",
    "medium.com": "medium",
    "about.me": "about_me",
}


def _registrable(domain: str) -> str:
    parts = domain.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


def _last_name(name: str | None) -> str | None:
    toks = [t for t in re.split(r"\s+", (name or "").strip()) if len(t) > 1]
    return toks[-1].lower() if toks else None


def _mentions(last: str | None, url: str, excerpt: str) -> bool:
    if not last:
        return True
    return last in (url + " " + excerpt).lower()


def extract_facts(sources: list[dict], subject: str, name: str | None = None,
                  org_domains: list[str] | None = None) -> list[DraftFact]:
    org = {d.lower() for d in (org_domains or [])}
    last = _last_name(name)
    facts: list[DraftFact] = []
    for src in sources:
        if src.get("origin") == "file_upload":      # skip the operator seed itself
            continue
        ref = src.get("source_ref")
        url = src.get("url") or ref or ""
        excerpt = src.get("excerpt") or ""
        domain = (domain_of(url) or "").lower()
        base = _registrable(domain)
        if not _mentions(last, url, excerpt):
            continue

        platform = PROFILE_PLATFORMS.get(base)
        if platform:
            facts.append(DraftFact(
                subject=subject, claim=f"{platform}_profile: {url}", category="contact",
                source_ref=ref, confidence=0.7, assertable=True,
                assertable_why=f"profile page on {platform}", sensitivity="public"))
        elif base in org or domain in org:
            facts.append(DraftFact(
                subject=subject, claim=f"company_page: {url}", category="other",
                source_ref=ref, confidence=0.7, assertable=True,
                assertable_why="appears on the company's own site", sensitivity="public"))
    return facts

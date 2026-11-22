"""Small shared helpers for collection adapters."""
from __future__ import annotations

from urllib.parse import urlparse


def domain_of(url: str | None) -> str | None:
    if not url:
        return None
    netloc = urlparse(url).netloc
    return netloc[4:] if netloc.startswith("www.") else netloc or None


def _domain_matches(domain: str, allowed: str) -> bool:
    allowed = allowed.lower().lstrip(".")
    return domain == allowed or domain.endswith("." + allowed)


def relevance_reason(excerpt: str | None, locator: str | None, url: str | None,
                     must_include: list[str], include_domains: list[str],
                     exclude_domains: list[str]) -> str | None:
    """Return None if the source is on-target, else a human-readable reason it
    was filtered. Used to drop famous namesakes: e.g. require 'revel8' to appear,
    or restrict to the target's own domains."""
    domain = (domain_of(url) or "").lower()
    if exclude_domains and any(_domain_matches(domain, d) for d in exclude_domains):
        return f"excluded domain: {domain}"
    if include_domains and not any(_domain_matches(domain, d) for d in include_domains):
        return f"domain not in include list: {domain or '(none)'}"
    if must_include:
        haystack = " ".join(x for x in (excerpt, locator, url) if x).lower()
        missing = [t for t in must_include if t.lower() not in haystack]
        if missing:
            return f"missing required term(s): {', '.join(missing)}"
    return None

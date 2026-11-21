"""Small shared helpers for collection adapters."""
from __future__ import annotations

from urllib.parse import urlparse


def domain_of(url: str | None) -> str | None:
    if not url:
        return None
    netloc = urlparse(url).netloc
    return netloc[4:] if netloc.startswith("www.") else netloc or None

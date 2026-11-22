"""STOPReplay collection layer (Adrian + Cem).

Common adapter framework + the universal Fact/source contract. Adapters retrieve
and normalize; the pipeline validates, applies guardrails, persists, and reports.
"""
from __future__ import annotations

from .adapters import (
    ArxivAdapter,
    BraveSearchAdapter,
    DnsMxAdapter,
    FirecrawlAdapter,
    GitHubAdapter,
    HackerNewsAdapter,
    IdentityAdapter,
    YouTubeAdapter,
)
from .base import CollectionAdapter
from .models import (
    CollectionOutput,
    DraftFact,
    DraftSource,
    ImportReport,
    ResearchRequest,
)
from .pipeline import CollectionPipeline
from .portal import generate_login_portal
from .registry import AdapterRegistry

__all__ = [
    "CollectionAdapter",
    "CollectionOutput",
    "CollectionPipeline",
    "AdapterRegistry",
    "ResearchRequest",
    "DraftSource",
    "DraftFact",
    "ImportReport",
    "IdentityAdapter",
    "BraveSearchAdapter",
    "DnsMxAdapter",
    "FirecrawlAdapter",
    "GitHubAdapter",
    "HackerNewsAdapter",
    "ArxivAdapter",
    "YouTubeAdapter",
    "generate_login_portal",
]

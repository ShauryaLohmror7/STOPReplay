"""STOPReplay collection layer (Adrian + Cem).

Common adapter framework + the universal Fact/source contract. Adapters retrieve
and normalize; the pipeline validates, applies guardrails, persists, and reports.
"""
from __future__ import annotations

from .adapters import BraveSearchAdapter, FirecrawlAdapter, IdentityAdapter
from .base import CollectionAdapter
from .models import (
    CollectionOutput,
    DraftFact,
    DraftSource,
    ImportReport,
    ResearchRequest,
)
from .pipeline import CollectionPipeline
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
    "FirecrawlAdapter",
]

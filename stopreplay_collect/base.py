"""The common collection adapter interface.

Every connector (identity, web, documents, social, code, place, ...) implements
`collect`: receive a normalized request, retrieve permitted material, preserve
its source, and return draft sources + facts in the universal structure. The
adapter does not persist, validate enums, or build the import report — the
pipeline does, so those are uniform. Storage is synchronous in this project, so
`collect` is synchronous too (the brief's async example is adapted, not copied).

Adapters must never generate hooks, pretexts, or persuasion strategy. This layer
only collects and normalizes evidence.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .models import CollectionOutput, ResearchRequest


class CollectionAdapter(ABC):
    #: stable, unique adapter name used in reports and the registry
    name: str = "adapter"

    @abstractmethod
    def collect(self, request: ResearchRequest) -> CollectionOutput:
        """Retrieve permitted information and return normalized drafts."""
        raise NotImplementedError

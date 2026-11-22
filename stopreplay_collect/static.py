"""A trivial adapter that returns a prebuilt CollectionOutput.

Used to push already-prepared drafts (e.g. facts extracted from stored sources)
through the normal pipeline so validation, the guardrails, dedup and reporting
all apply uniformly.
"""
from __future__ import annotations

from .base import CollectionAdapter
from .models import CollectionOutput, ResearchRequest


class StaticAdapter(CollectionAdapter):
    def __init__(self, output: CollectionOutput, name: str = "static"):
        self._output = output
        self.name = name

    def collect(self, request: ResearchRequest) -> CollectionOutput:
        return self._output

"""Collection adapters. Each produces the universal draft structure.

Implemented: identity (custom), brave (web search / discovery), firecrawl (page
extraction). Both web adapters use the services' REST APIs directly (no Node/MCP)
and read their keys from the environment.

Deferred external connectors (anymd, agent_reach, youtube, octosuite, osmnx,
google_maps) are integrated one at a time after inspecting each actual
repository — see docs/collection.md.
"""
from __future__ import annotations

from .brave import BraveSearchAdapter
from .firecrawl import FirecrawlAdapter
from .identity import IdentityAdapter

__all__ = ["IdentityAdapter", "BraveSearchAdapter", "FirecrawlAdapter"]

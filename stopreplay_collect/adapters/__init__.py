"""Collection adapters that return the shared draft records."""
from __future__ import annotations

from .agent_reach import AgentReachAdapter
from .anymd import AnyMDAdapter
from .brave import BraveSearchAdapter
from .firecrawl import FirecrawlAdapter
from .github import GitHubAdapter
from .identity import IdentityAdapter
from .osmnx import OSMnxAdapter
from .youtube import YouTubeAdapter

__all__ = ["AgentReachAdapter", "AnyMDAdapter", "IdentityAdapter", "BraveSearchAdapter",
           "FirecrawlAdapter", "GitHubAdapter", "OSMnxAdapter", "YouTubeAdapter"]

"""Brave Search adapter (Category C, discovery) — direct REST, no MCP/Node.

Built against the documented API:
  GET https://api.search.brave.com/res/v1/web/search
  header: X-Subscription-Token: <BRAVE_API_KEY>
  results at web.results[] (title, url, description; extra fields read defensively)

Discovery only: it returns candidate public web sources (result + snippet), not
asserted facts. Firecrawl extracts full page content; turning prose into atomic
facts is a separate model-backed step (see docs/collection.md). The key is read
from the environment and never logged.
"""
from __future__ import annotations

import os
from datetime import date

import httpx

from ..base import CollectionAdapter
from ..models import CollectionOutput, DraftSource, ResearchRequest
from ..util import domain_of

ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchAdapter(CollectionAdapter):
    name = "brave"

    def __init__(self, api_key: str | None = None, *, client: httpx.Client | None = None,
                 count: int = 10, country: str | None = None,
                 freshness: str | None = None, timeout: float = 30.0):
        self.api_key = api_key if api_key is not None else os.environ.get("BRAVE_API_KEY")
        self._client = client          # injectable for tests; owned by caller if given
        self.count = max(1, min(count, 20))  # API max is 20
        self.country = country
        self.freshness = freshness
        self.timeout = timeout

    def collect(self, request: ResearchRequest) -> CollectionOutput:
        out = CollectionOutput()
        if not self.api_key:
            out.retrieval_failures.append({"error": "BRAVE_API_KEY not set"})
            return out

        query = request.query or request.subject
        params: dict[str, object] = {"q": query, "count": request.limit or self.count}
        if self.country:
            params["country"] = self.country
        if self.freshness:
            params["freshness"] = self.freshness
        headers = {"X-Subscription-Token": self.api_key, "Accept": "application/json"}

        try:
            data = self._get(params, headers)
        except Exception as exc:  # network / HTTP / decode
            out.retrieval_failures.append({"query": query, "error": f"{type(exc).__name__}: {exc}"})
            return out

        results = (data.get("web") or {}).get("results") or []
        today = date.today()
        for result in results:
            url = result.get("url")
            if not url:
                out.extraction_failures.append({"error": "search result missing url"})
                continue
            out.sources.append(DraftSource(
                source_ref=url, origin="public_web", url=url, publisher=domain_of(url),
                locator="brave web search result snippet (not full page text)",
                excerpt=result.get("description") or result.get("title") or "",
                retrieved_on=today,
            ))
        return out

    def _get(self, params: dict, headers: dict) -> dict:
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            resp = client.get(ENDPOINT, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()
        finally:
            if self._client is None:
                client.close()

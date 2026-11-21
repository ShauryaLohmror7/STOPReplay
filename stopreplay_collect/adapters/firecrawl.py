"""Firecrawl adapter (Category C) — direct REST, no MCP/Node. One key, two modes.

Built against the documented API:
  POST https://api.firecrawl.dev/v2/scrape   -> extract one known URL
  POST https://api.firecrawl.dev/v2/search   -> discover (and optionally scrape)
  header: Authorization: Bearer <FIRECRAWL_API_KEY>
  content at data.markdown (scrape); search results at data (flat list) OR
  data.web (object) — the docs give both shapes, so we accept either.

Because `search` can discover and scrape in one call, a single Firecrawl key can
replace Brave for discovery. The adapter preserves public web *sources*; it does
not assert facts. The key is read from the environment and never logged.

Modes (per request):
  request.params["url"] / ["urls"]  -> scrape those pages
  request.query                     -> search the web (scraping each hit by default)
"""
from __future__ import annotations

import os
from datetime import date

import httpx

from ..base import CollectionAdapter
from ..models import CollectionOutput, DraftSource, ResearchRequest
from ..util import domain_of

SCRAPE_ENDPOINT = "https://api.firecrawl.dev/v2/scrape"
SEARCH_ENDPOINT = "https://api.firecrawl.dev/v2/search"


class FirecrawlAdapter(CollectionAdapter):
    name = "firecrawl"

    def __init__(self, api_key: str | None = None, *, client: httpx.Client | None = None,
                 only_main_content: bool = True, search_limit: int = 5,
                 scrape_search_results: bool = True, country: str | None = None,
                 location: str | None = None, timeout: float = 60.0):
        self.api_key = api_key if api_key is not None else os.environ.get("FIRECRAWL_API_KEY")
        self._client = client
        self.only_main_content = only_main_content
        self.search_limit = search_limit
        self.scrape_search_results = scrape_search_results
        self.country = country
        self.location = location
        self.timeout = timeout

    def collect(self, request: ResearchRequest) -> CollectionOutput:
        out = CollectionOutput()
        if not self.api_key:
            out.retrieval_failures.append({"error": "FIRECRAWL_API_KEY not set"})
            return out

        urls = request.params.get("urls")
        if not urls and request.params.get("url"):
            urls = [request.params["url"]]
        if urls:
            return self._scrape_urls(urls, out)
        if request.query:
            return self._search(request, out)
        out.retrieval_failures.append(
            {"error": "provide request.query (search) or request.params['url'/'urls'] (scrape)"})
        return out

    # -- scrape -------------------------------------------------------------
    def _scrape_urls(self, urls: list[str], out: CollectionOutput) -> CollectionOutput:
        headers = self._headers()
        today = date.today()
        for url in urls:
            body = {"url": url, "formats": ["markdown"], "onlyMainContent": self.only_main_content}
            try:
                data = self._post(SCRAPE_ENDPOINT, body, headers)
            except Exception as exc:
                out.retrieval_failures.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})
                continue
            if not data.get("success"):
                out.extraction_failures.append({"url": url, "error": data.get("error", "scrape failed")})
                continue
            payload = data.get("data") or {}
            markdown, meta = payload.get("markdown") or "", payload.get("metadata") or {}
            if not markdown:
                out.extraction_failures.append({"url": url, "error": "no markdown content returned"})
                continue
            out.sources.append(DraftSource(
                source_ref=meta.get("sourceURL") or url, origin="public_web", url=url,
                publisher=domain_of(meta.get("sourceURL") or url),
                locator=meta.get("title") or "scraped page (main content)",
                excerpt=markdown, retrieved_on=today,
            ))
        return out

    # -- search -------------------------------------------------------------
    def _search(self, request: ResearchRequest, out: CollectionOutput) -> CollectionOutput:
        body: dict = {"query": request.query, "limit": request.limit or self.search_limit}
        if self.scrape_search_results:
            body["scrapeOptions"] = {"formats": ["markdown"], "onlyMainContent": self.only_main_content}
        if self.country:
            body["country"] = self.country
        if self.location:
            body["location"] = self.location
        try:
            data = self._post(SEARCH_ENDPOINT, body, self._headers())
        except Exception as exc:
            out.retrieval_failures.append({"query": request.query, "error": f"{type(exc).__name__}: {exc}"})
            return out
        if data.get("success") is False:
            out.retrieval_failures.append({"query": request.query, "error": data.get("error", "search failed")})
            return out

        today = date.today()
        for item in self._search_items(data):
            url = item.get("url")
            if not url:
                out.extraction_failures.append({"error": "search result missing url"})
                continue
            meta = item.get("metadata") or {}
            markdown = item.get("markdown")
            scraped = bool(markdown)
            title = meta.get("title") or item.get("title") or "search result"
            out.sources.append(DraftSource(
                source_ref=meta.get("sourceURL") or url, origin="public_web", url=url,
                publisher=domain_of(url),
                locator=title if scraped else f"{title} (search snippet, not full page)",
                excerpt=markdown or item.get("description") or title, retrieved_on=today,
            ))
        return out

    @staticmethod
    def _search_items(data: dict) -> list[dict]:
        payload = data.get("data")
        if isinstance(payload, list):        # flat-array shape
            return payload
        if isinstance(payload, dict):        # {"web": [...], "news": [...]} shape
            return payload.get("web") or []
        return []

    # -- http ---------------------------------------------------------------
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _post(self, endpoint: str, body: dict, headers: dict) -> dict:
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            resp = client.post(endpoint, json=body, headers=headers)
            resp.raise_for_status()
            return resp.json()
        finally:
            if self._client is None:
                client.close()

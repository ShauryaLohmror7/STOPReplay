"""Brave + Firecrawl adapter tests using httpx.MockTransport.

These exercise the real request construction and response parsing against the
documented response shapes, with no API key and no network. The pipeline test
also persists, so it needs the DB fixture.
"""
from __future__ import annotations

import httpx

from stopreplay_collect import (
    BraveSearchAdapter,
    CollectionPipeline,
    FirecrawlAdapter,
    ResearchRequest,
)

BRAVE_OK = {"web": {"results": [
    {"title": "Julius Muth - revel8", "url": "https://revel8.example/team/julius",
     "description": "Julius Muth is Co-CEO of revel8."},
]}}

FIRECRAWL_OK = {"success": True, "data": {
    "markdown": "# Julius Muth\nCo-CEO at revel8.",
    "metadata": {"title": "Julius Muth", "sourceURL": "https://revel8.example/team/julius",
                 "statusCode": 200},
}}


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# -- Brave ------------------------------------------------------------------
def test_brave_parses_results_to_sources():
    adapter = BraveSearchAdapter(api_key="k", client=_client(
        lambda req: httpx.Response(200, json=BRAVE_OK)))
    out = adapter.collect(ResearchRequest("recon", "julius", query="julius muth"))
    assert len(out.sources) == 1
    src = out.sources[0]
    assert src.url == "https://revel8.example/team/julius"
    assert src.origin == "public_web"
    assert src.publisher == "revel8.example"
    assert "Co-CEO" in src.excerpt


def test_brave_sends_auth_and_query():
    seen = {}

    def handler(req):
        seen["token"] = req.headers.get("X-Subscription-Token")
        seen["q"] = req.url.params.get("q")
        return httpx.Response(200, json={"web": {"results": []}})

    BraveSearchAdapter(api_key="secret", client=_client(handler)).collect(
        ResearchRequest("recon", "julius", query="julius muth revel8"))
    assert seen["token"] == "secret"
    assert seen["q"] == "julius muth revel8"


def test_brave_missing_key_reports_failure():
    out = BraveSearchAdapter(api_key="").collect(ResearchRequest("recon", "julius"))
    assert out.sources == []
    assert out.retrieval_failures and "BRAVE_API_KEY" in out.retrieval_failures[0]["error"]


def test_brave_http_error_is_retrieval_failure():
    adapter = BraveSearchAdapter(api_key="k", client=_client(
        lambda req: httpx.Response(429, json={"error": "rate limited"})))
    out = adapter.collect(ResearchRequest("recon", "julius", query="x"))
    assert out.sources == []
    assert out.retrieval_failures


# -- Firecrawl --------------------------------------------------------------
def test_firecrawl_scrape_to_source():
    adapter = FirecrawlAdapter(api_key="k", client=_client(
        lambda req: httpx.Response(200, json=FIRECRAWL_OK)))
    out = adapter.collect(ResearchRequest(
        "recon", "julius", params={"url": "https://revel8.example/team/julius"}))
    assert len(out.sources) == 1
    assert "Co-CEO" in out.sources[0].excerpt
    assert out.sources[0].locator == "Julius Muth"


def test_firecrawl_sends_bearer_and_body():
    seen = {}

    def handler(req):
        seen["auth"] = req.headers.get("Authorization")
        import json
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json=FIRECRAWL_OK)

    FirecrawlAdapter(api_key="fc-xyz", client=_client(handler)).collect(
        ResearchRequest("recon", "julius", params={"url": "https://revel8.example/x"}))
    assert seen["auth"] == "Bearer fc-xyz"
    assert seen["body"]["url"] == "https://revel8.example/x"
    assert seen["body"]["formats"] == ["markdown"]


def test_firecrawl_unsuccessful_is_extraction_failure():
    adapter = FirecrawlAdapter(api_key="k", client=_client(
        lambda req: httpx.Response(200, json={"success": False, "error": "blocked"})))
    out = adapter.collect(ResearchRequest("recon", "julius", params={"url": "https://x.example"}))
    assert out.sources == []
    assert out.extraction_failures and out.extraction_failures[0]["error"] == "blocked"


# -- Firecrawl search mode (one key does discovery too) ---------------------
SEARCH_DICT = {"success": True, "data": {"web": [
    {"url": "https://a.example/1", "title": "A", "description": "about julius"}]}}
SEARCH_ARRAY = {"success": True, "data": [
    {"url": "https://a.example/1", "title": "A", "markdown": "# A\nJulius detail",
     "metadata": {"title": "A", "sourceURL": "https://a.example/1", "statusCode": 200}}]}


def test_firecrawl_search_dict_shape():
    adapter = FirecrawlAdapter(api_key="k", client=_client(
        lambda req: httpx.Response(200, json=SEARCH_DICT)))
    out = adapter.collect(ResearchRequest("recon", "julius", query="julius muth"))
    assert len(out.sources) == 1
    assert out.sources[0].url == "https://a.example/1"
    assert "search snippet" in out.sources[0].locator  # not scraped


def test_firecrawl_search_array_shape_with_markdown():
    adapter = FirecrawlAdapter(api_key="k", client=_client(
        lambda req: httpx.Response(200, json=SEARCH_ARRAY)))
    out = adapter.collect(ResearchRequest("recon", "julius", query="julius"))
    assert len(out.sources) == 1
    assert "Julius detail" in out.sources[0].excerpt
    assert out.sources[0].locator == "A"


def test_firecrawl_search_sends_query_and_scrapeoptions():
    import json
    seen = {}

    def handler(req):
        seen["path"] = req.url.path
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json=SEARCH_DICT)

    FirecrawlAdapter(api_key="k", client=_client(handler)).collect(
        ResearchRequest("recon", "julius", query="julius muth"))
    assert seen["path"] == "/v2/search"
    assert seen["body"]["query"] == "julius muth"
    assert seen["body"]["scrapeOptions"]["formats"] == ["markdown"]


# -- pipeline integration (needs DB) ----------------------------------------
def test_brave_pipeline_registers_sources(storage):
    adapter = BraveSearchAdapter(api_key="k", client=_client(
        lambda req: httpx.Response(200, json=BRAVE_OK)))
    report = CollectionPipeline(storage).run(
        adapter, ResearchRequest("recon", "julius", query="julius"))
    assert report.summary()["sources_registered"] == 1
    assert storage.get_source("recon", "https://revel8.example/team/julius") is not None

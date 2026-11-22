"""Hacker News adapter unit tests with a mock HTTP client (no network)."""
from __future__ import annotations

import httpx

from stopreplay_collect import HackerNewsAdapter, ResearchRequest


class MockHNTransport(httpx.BaseTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        data = {
            "hits": [
                {
                    "objectID": "12345",
                    "title": "Show HN: revel8 – AI Agentic Security Platform",
                    "author": "julius_m",
                    "story_text": "We built revel8 to stop generative AI phishing attacks.",
                    "url": "https://revel8.ai",
                    "created_at_i": 1715000000
                },
                {
                    "objectID": "67890",
                    "author": "tech_commenter",
                    "comment_text": "<p>Julius Muth spoke about this at START Munich. Great concept!</p>",
                    "created_at_i": 1715100000
                }
            ]
        }
        return httpx.Response(200, json=data)


def test_hackernews_extracts_stories_and_comments():
    client = httpx.Client(transport=MockHNTransport())
    adapter = HackerNewsAdapter(client=client)

    out = adapter.collect(ResearchRequest("recon", "julius", query="revel8"))

    assert len(out.sources) == 2
    origins = [s.origin for s in out.sources]
    assert all(orig == "social_post" for orig in origins)

    claims = [f.claim for f in out.facts]
    assert any("hn_submission: 'Show HN: revel8 – AI Agentic Security Platform' by julius_m" in c for c in claims)
    assert any("hn_comment: 'Julius Muth spoke about this at START Munich. Great concept!' by tech_commenter" in c for c in claims)


def test_hackernews_handles_empty_hits():
    class EmptyTransport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"hits": []})

    client = httpx.Client(transport=EmptyTransport())
    adapter = HackerNewsAdapter(client=client)
    out = adapter.collect(ResearchRequest("recon", "julius", query="nonexistent"))

    assert out.sources == []
    assert out.facts == []
    assert out.retrieval_failures == []

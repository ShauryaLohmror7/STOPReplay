"""arXiv adapter unit tests with a mock HTTP client (no network)."""
from __future__ import annotations

import httpx

from stopreplay_collect import ArxivAdapter, ResearchRequest

SAMPLE_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.99999v1</id>
    <published>2024-01-15T18:00:00Z</published>
    <title>Deepfake Resilience in Agentic Workflows</title>
    <summary>We present a study on autonomous social engineering defenses.</summary>
    <author>
      <name>Julius Muth</name>
    </author>
    <author>
      <name>Robert Seilbeck</name>
    </author>
    <category term="cs.CR" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>
"""


class MockArxivTransport(httpx.BaseTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SAMPLE_ARXIV_XML)


def test_arxiv_extracts_paper_coauthors_and_topics():
    client = httpx.Client(transport=MockArxivTransport())
    adapter = ArxivAdapter(client=client)

    out = adapter.collect(ResearchRequest("recon", "julius", query="Julius Muth"))

    assert len(out.sources) == 1
    assert out.sources[0].origin == "public_web"
    assert out.sources[0].publisher == "arXiv"
    assert "Deepfake Resilience" in out.sources[0].locator

    claims = [f.claim for f in out.facts]
    assert any("research_paper: 'Deepfake Resilience in Agentic Workflows'" in c for c in claims)
    assert any("colleague: Robert Seilbeck (co-author on arXiv paper" in c for c in claims)
    assert any("interest: cs.CR (arXiv research area)" in c for c in claims)


def test_arxiv_empty_feed_handled():
    empty_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"></feed>"""

    class EmptyTransport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text=empty_xml)

    client = httpx.Client(transport=EmptyTransport())
    adapter = ArxivAdapter(client=client)
    out = adapter.collect(ResearchRequest("recon", "julius", query="nobody"))

    assert out.sources == []
    assert out.facts == []

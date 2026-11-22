from __future__ import annotations

from datetime import date

import httpx

from stopreplay_collect.adapters import AgentReachAdapter
from stopreplay_collect.models import ResearchRequest
from stopreplay_collect.pipeline import CollectionPipeline


def test_agent_reach_registers_public_topic_once_per_run(storage):
    def topic(request):
        assert request.url == "https://www.v2ex.com/api/topics/show.json?id=42"
        assert "authorization" not in request.headers
        assert "cookie" not in request.headers
        return httpx.Response(200, json=[{
            "id": 42, "title": "Project release", "content": "The institution released version two.",
            "created": 1704067200,
        }])

    with httpx.Client(transport=httpx.MockTransport(topic)) as client:
        adapter = AgentReachAdapter(client=client)
        pipeline = CollectionPipeline(storage)
        params = {"urls": ["https://v2ex.com/t/42#reply1", "https://www.v2ex.com/t/42"]}
        request = ResearchRequest("recon", "fixture", params=params)
        assert pipeline.run(adapter, request).sources_registered == 1
        assert pipeline.run(adapter, request).sources_registered == 0
        other = ResearchRequest("other", "fixture", params=params)
        assert pipeline.run(adapter, other).sources_registered == 1

    source = storage.get_source("recon", "v2ex:42")
    assert source["origin"] == "social_post"
    assert source["url"] == "https://www.v2ex.com/t/42"
    assert source["excerpt"] == "Project release\n\nThe institution released version two."
    assert source["observed_on"] == date(2024, 1, 1)
    assert storage.get_facts("recon") == []


def test_agent_reach_reports_unavailable_and_mismatched_topics():
    def topic(request):
        if request.url.params["id"] == "1":
            return httpx.Response(200, json=[])
        assert request.url.params["id"] == "2"
        return httpx.Response(200, json=[{"id": 3, "content": "wrong topic"}])

    params = {"urls": ["https://v2ex.com/t/1", "https://v2ex.com/t/2", "https://example.com/t/3"]}
    with httpx.Client(transport=httpx.MockTransport(topic)) as client:
        output = AgentReachAdapter(client=client).collect(ResearchRequest("recon", "fixture", params=params))

    assert len(output.retrieval_failures) == 2
    assert len(output.extraction_failures) == 1
    assert output.sources == []

"""Tests for DNS MX Email Provider Adapter."""
from __future__ import annotations

import httpx

from stopreplay_collect.adapters.dns_mx import DnsMxAdapter, identify_provider
from stopreplay_collect.models import ResearchRequest


def test_identify_provider_patterns():
    assert identify_provider(["1 smtp.google.com."]) == "Google Workspace"
    assert identify_provider(["5 aspmx.l.google.com."]) == "Google Workspace"
    assert identify_provider(["10 company-de.mail.protection.outlook.com."]) == "Microsoft 365"
    assert identify_provider(["10 mail.protonmail.ch."]) == "Proton Mail"
    assert identify_provider(["10 mx.zoho.com."]) == "Zoho Mail"
    assert identify_provider(["10 custom-mx.example.com."]) == "Custom (example.com)"
    assert identify_provider([]) == "Unknown"


def test_dns_mx_adapter_collect():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        if "revel8.ai" in str(request.url):
            return httpx.Response(200, json={
                "Status": 0,
                "Answer": [{"name": "revel8.ai.", "type": 15, "data": "1 smtp.google.com."}]
            })
        return httpx.Response(404, json={})

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    adapter = DnsMxAdapter(client=client)
    req = ResearchRequest(
        source_run="test-recon",
        subject="julius",
        include_domains=["revel8.ai"],
        synthetic_authorized=True,
    )

    out = adapter.collect(req)

    assert len(out.sources) == 1
    assert out.sources[0].source_ref == "dns:mx:revel8.ai"
    assert "Google Workspace" in (out.sources[0].excerpt or "")

    assert len(out.facts) == 1
    assert out.facts[0].claim == "email_provider: Google Workspace"
    assert out.facts[0].category == "other"
    assert out.facts[0].confidence == 0.95

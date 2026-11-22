"""Unit tests for the landing page / portal HTML generator."""
from __future__ import annotations

from stopreplay_collect.portal import generate_login_portal


def test_generate_login_portal_with_brand_assets():
    facts = [
        {"claim": "company_domain: revel8.ai"},
        {"claim": "company_logo: https://revel8.ai/assets/logo.svg (revel8 logo)"},
        {"claim": "company_color: #6366f1"},
        {"claim": "company_footer: © 2026 revel8 GmbH, Munich. All rights reserved."},
        {"claim": "target_email: Julius Muth <julius@revel8.ai>"},
    ]

    portal = generate_login_portal(facts)

    assert portal["url"] == "https://sso.revel8.ai/signin"
    assert "revel8" in portal["title"].lower()
    assert portal["fields"] == ["email", "password"]
    assert portal["brand_color"] == "#6366f1"
    assert portal["logo_url"] == "https://revel8.ai/assets/logo.svg"
    assert portal["prefilled_email"] == "julius@revel8.ai"

    # HTML content checks
    html = portal["html"]
    assert "https://revel8.ai/assets/logo.svg" in html
    assert "#6366f1" in html
    assert "© 2026 revel8 GmbH, Munich. All rights reserved." in html
    assert 'value="julius@revel8.ai"' in html
    assert 'name="email"' in html
    assert 'name="password"' in html
    assert "<script" not in html.lower()  # Simulator constraint: no external scripts


def test_generate_login_portal_fallback():
    facts = []

    portal = generate_login_portal(facts, org_name="AcmeCorp")

    assert "AcmeCorp" in portal["title"]
    assert portal["brand_color"] == "#2563eb"  # Default fallback
    assert portal["logo_url"] is None
    assert portal["prefilled_email"] is None

    html = portal["html"]
    assert "AcmeCorp" in html
    assert "#2563eb" in html
    assert 'name="email"' in html
    assert 'name="password"' in html
    assert "<script" not in html.lower()

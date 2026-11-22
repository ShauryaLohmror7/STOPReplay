"""Fact extraction from stored sources (deterministic, high-precision)."""
from __future__ import annotations

from stopreplay_collect.extract import extract_facts

SOURCES = [
    {"origin": "file_upload", "source_ref": "seed:julius", "url": None,
     "excerpt": "Julius Muth, revel8.ai"},                                  # seed, skipped
    {"origin": "public_web", "source_ref": "https://de.linkedin.com/in/julius-muth",
     "url": "https://de.linkedin.com/in/julius-muth", "excerpt": "Julius Muth, revel8"},
    {"origin": "public_web", "source_ref": "https://www.revel8.ai/author-julius",
     "url": "https://www.revel8.ai/author-julius", "excerpt": "Author Julius Muth"},
    {"origin": "public_web", "source_ref": "https://www.revel8.ai/grounding",
     "url": "https://www.revel8.ai/grounding", "excerpt": "grounding technology"},  # no name
    {"origin": "public_web", "source_ref": "https://en.wikipedia.org/wiki/X",
     "url": "https://en.wikipedia.org/wiki/X", "excerpt": "Muth is a surname"},  # not platform/org
]


def test_extract_profiles_and_company_pages():
    facts = extract_facts(SOURCES, "julius", name="Julius Muth", org_domains=["revel8.ai"])
    claims = [f.claim for f in facts]
    assert any(c.startswith("linkedin_profile:") for c in claims)
    assert any(c == "company_page: https://www.revel8.ai/author-julius" for c in claims)
    assert not any("grounding" in c for c in claims)       # page never names him
    assert not any("wikipedia" in c for c in claims)       # not a profile platform or the org
    assert all(f.source_ref != "seed:julius" for f in facts)  # seed itself not re-emitted


def test_extract_requires_name_match():
    only_company = [{"origin": "public_web", "source_ref": "https://www.revel8.ai/about",
                     "url": "https://www.revel8.ai/about", "excerpt": "About revel8 the company"}]
    assert extract_facts(only_company, "julius", name="Julius Muth",
                         org_domains=["revel8.ai"]) == []


def test_extract_media_photos_and_roles():
    rich_source = [{
        "origin": "public_web",
        "source_ref": "https://revel8.ai/team",
        "url": "https://revel8.ai/team",
        "locator": "Team revel8",
        "excerpt": (
            "# Team\n\n"
            "![Julius Muth headshot](https://revel8.ai/assets/julius_muth.png)\n\n"
            "Julius Muth is Co-Founder & Co-CEO at revel8. He is based in Munich.\n"
            "He studied at TUM and co-founded with Robert Seilbeck.\n"
            "Passionate about Cybersecurity, AI, and Autonomous Agents."
        )
    }]
    facts = extract_facts(rich_source, "julius", name="Julius Muth", org_domains=["revel8.ai"])
    claims = [f.claim for f in facts]
    categories = {f.category for f in facts}

    assert any(c.startswith("profile_picture: https://revel8.ai/assets/julius_muth.png") for c in claims)
    assert any("Co-Founder & Co-CEO at revel8" in c for c in claims)
    assert any("based_in: Munich" in c for c in claims)
    assert any("education:" in c and "TUM" in c for c in claims)
    assert any("colleague: Robert Seilbeck" in c for c in claims)
    assert any("colleague_sender: Robert Seilbeck <robert.seilbeck@revel8.ai>" in c for c in claims)
    assert any("interest: Cybersecurity" in c for c in claims)
    assert any("interest: AI" in c for c in claims)
    assert "role" in categories
    assert "relationship" in categories
    assert "interest" in categories


def test_extract_posts_and_talks():
    sources = [
        {
            "origin": "public_web",
            "source_ref": "https://revel8.ai/blog/agentic-security",
            "url": "https://revel8.ai/blog/agentic-security",
            "locator": "Agentic Security in Practice",
            "excerpt": "Julius Muth explains how AI agents interact with social engineering defenses."
        },
        {
            "origin": "public_talk",
            "source_ref": "https://www.youtube.com/watch?v=abcdef12345",
            "url": "https://www.youtube.com/watch?v=abcdef12345",
            "locator": "START Hack Keynote 2026",
            "excerpt": "Julius Muth: Welcome everyone. Today we demonstrate simulated AI twins."
        },
        {
            "origin": "social_post",
            "source_ref": "v2ex:12345",
            "url": "https://www.v2ex.com/t/12345",
            "locator": "topic 12345",
            "excerpt": "Julius Muth: Great discussion on autonomous agent validation."
        }
    ]
    facts = extract_facts(sources, "julius", name="Julius Muth", org_domains=["revel8.ai"])
    claims = [f.claim for f in facts]

    assert any("authored_article: 'Agentic Security in Practice'" in c for c in claims)
    assert any("public_appearance: START Hack Keynote 2026" in c for c in claims)
    assert any("talk_statement:" in c for c in claims)
    assert any("public_post_or_comment:" in c for c in claims)

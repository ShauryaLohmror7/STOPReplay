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


def test_extract_brand_assets_and_email_patterns():
    sources = [
        {
            "origin": "public_web",
            "source_ref": "https://revel8.ai",
            "url": "https://revel8.ai",
            "locator": "revel8 AI — Autonomous Enterprise Security",
            "excerpt": (
                '<meta name="theme-color" content="#4f46e5">\n'
                '<style>:root { --primary-color: #4f46e5; }</style>\n'
                '![revel8 logo](https://revel8.ai/assets/logo.svg)\n'
                '<img src="/static/brand_mark.png" alt="revel8 brand mark">\n\n'
                'Welcome to revel8 AI. Contact us at contact@revel8.ai or press@revel8.ai.\n'
                'For executive matters write to julius@revel8.ai.\n\n'
                '# Leadership Team\n'
                'Robert Seilbeck, CTO & Co-Founder\n'
                'Sarah Jenkins, Head of Product\n\n'
                '<footer>\n'
                'Amtsgericht München HRB 291823 | USt-IdNr.: DE367891234\n'
                '© 2026 revel8 GmbH, Munich. All rights reserved.\n'
                '</footer>'
            )
        }
    ]

    facts = extract_facts(sources, "julius", name="Julius Muth", org_domains=["revel8.ai"])
    claims = [f.claim for f in facts]

    # Brand & legal imprint assets
    assert any("company_logo: https://revel8.ai/assets/logo.svg (revel8 logo)" in c for c in claims)
    assert any("company_logo: https://revel8.ai/static/brand_mark.png" in c for c in claims)
    assert any("company_footer: © 2026 revel8 GmbH, Munich. All rights reserved." in c for c in claims)
    assert any("company_color: #4f46e5" in c for c in claims)
    assert any("commercial_register: Amtsgericht München HRB 291823" in c for c in claims)
    assert any("vat_id: USt-IdNr.: DE367891234" in c for c in claims)

    # Corporate contact emails
    assert any("company_contact_email: contact@revel8.ai" in c for c in claims)
    assert any("company_contact_email: press@revel8.ai" in c for c in claims)

    # Inferred email pattern from observing julius@revel8.ai -> "first"
    assert any("email_pattern: first@revel8.ai" in c for c in claims)

    # Colleague senders formatted with inferred "first" pattern
    assert any("colleague_sender: Robert Seilbeck <robert@revel8.ai>" in c for c in claims)
    assert any("colleague_sender: Sarah Jenkins <sarah@revel8.ai>" in c for c in claims)

    # Target email formatted with inferred pattern
    assert any("target_email: Julius Muth <julius@revel8.ai>" in c for c in claims)


def test_extract_social_media_and_reddit():
    sources = [
        {
            "origin": "public_web",
            "source_ref": "https://www.instagram.com/julius_muth",
            "url": "https://www.instagram.com/julius_muth",
            "locator": "Julius Muth (@julius_muth) on Instagram",
            "excerpt": "Julius Muth. Co-Founder @revel8. Building autonomous cyber defenses."
        },
        {
            "origin": "public_web",
            "source_ref": "https://www.facebook.com/julius.muth.munich",
            "url": "https://www.facebook.com/julius.muth.munich",
            "locator": "Julius Muth | Facebook",
            "excerpt": "Julius Muth lives in Munich, Germany. Co-Founder at revel8."
        },
        {
            "origin": "public_web",
            "source_ref": "https://www.reddit.com/r/cybersecurity/comments/abc123/revel8_ai_defense",
            "url": "https://www.reddit.com/r/cybersecurity/comments/abc123/revel8_ai_defense",
            "locator": "Discussion on revel8 AI defense by Julius Muth",
            "excerpt": "Julius Muth from revel8 shared their architecture for synthetic persona training."
        },
        {
            "origin": "public_web",
            "source_ref": "https://revel8.ai/community",
            "url": "https://revel8.ai/community",
            "locator": "revel8 Community",
            "excerpt": (
                "Connect with revel8 across the web:\n"
                "- Follow our Instagram: https://www.instagram.com/revel8.ai\n"
                "- Join Facebook page: https://www.facebook.com/revel8ai\n"
            )
        }
    ]

    facts = extract_facts(sources, "julius", name="Julius Muth", org_domains=["revel8.ai"])
    claims = [f.claim for f in facts]

    # Personal social profiles
    assert any("instagram_profile: https://www.instagram.com/julius_muth" in c for c in claims)
    assert any("facebook_profile: https://www.facebook.com/julius.muth.munich" in c for c in claims)

    # Reddit discussion
    assert any("reddit_discussion: 'Discussion on revel8 AI defense by Julius Muth'" in c for c in claims)

    # Company social channels
    assert any("company_social_instagram: https://www.instagram.com/revel8.ai" in c for c in claims)
    assert any("company_social_facebook: https://www.facebook.com/revel8ai" in c for c in claims)

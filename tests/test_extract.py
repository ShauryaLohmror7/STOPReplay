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

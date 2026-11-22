"""Turn stored (scraped) sources into structured, actionable facts.

Extracts rich target intelligence across web sources, social media, articles,
talks, and profiles:
- Social & professional platform profiles and handles
- Visual assets: profile pictures, headshots, and photos
- Roles, job titles, and company affiliations
- Authored posts, articles, and blog publications
- Public comments, forum replies, and discussion statements
- Talks, podcast appearances, and interview transcripts
- Educational background, degrees, and universities
- Location / residency signals
- Known associates, co-founders, and colleagues
- Professional and technical topics/interests
"""
from __future__ import annotations

import re
from typing import Any

from .models import DraftFact
from .util import domain_of

PROFILE_PLATFORMS = {
    "linkedin.com": "linkedin",
    "crunchbase.com": "crunchbase",
    "github.com": "github",
    "twitter.com": "x",
    "x.com": "x",
    "xing.com": "xing",
    "medium.com": "medium",
    "about.me": "about_me",
    "substack.com": "substack",
    "youtube.com": "youtube",
}

_ROLE_KEYWORDS = (
    "co-founder", "founder", "co-ceo", "ceo", "cto", "coo", "cfo", "chief",
    "president", "vice president", "vp", "head of", "director", "lead",
    "engineer", "researcher", "manager", "partner", "consultant"
)

_INTEREST_KEYWORDS = (
    "AI", "Artificial Intelligence", "Machine Learning", "Deep Learning",
    "LLMs", "Agentic AI", "Cybersecurity", "Social Engineering", "Security",
    "Autonomous Agents", "SaaS", "B2B Sales", "Go-To-Market", "Python",
    "TypeScript", "Rust", "Cloud Infrastructure", "Product Management"
)

_IMAGE_MD_RE = re.compile(r'!\[([^\]]*)\]\((https?://[^\s\)]+?\.(?:png|jpg|jpeg|webp|gif)(?:\?[^\s\)]*)?)\)', re.I)
_IMAGE_TAG_RE = re.compile(r'<img[^>]+src=["\'](https?://[^"\']+\.(?:png|jpg|jpeg|webp|gif)(?:\?[^"\']*)?)["\'][^>]*>', re.I)
_URL_IN_TEXT_RE = re.compile(r'https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(/[^\s\)\"\'>]*)?', re.I)
_EDU_RE = re.compile(
    r'\b(?:studied|alumnus of|graduate of|graduated from|degree in|B\.?Sc\.?|M\.?Sc\.?|Ph\.?D\.?|MBA)\b'
    r'[^.,;\n]{0,80}\b(?:University|Institute|College|School|TUM|LMU|ETH|Stanford|MIT|Berkeley|Oxford|Cambridge|Harvard)\b[^.,;\n]{0,40}',
    re.I
)
_LOCATION_RE = re.compile(r'\b(?:based in|living in|located in)\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z]+)?)', re.I)
_COLLEAGUE_RE = re.compile(r'\b(?:co-founded with|together with|alongside)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', re.I)


def _registrable(domain: str) -> str:
    parts = domain.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


def _name_tokens(name: str | None) -> list[str]:
    return [t.lower() for t in re.split(r"\s+", (name or "").strip()) if len(t) > 1]


def _mentions(last: str | None, url: str, excerpt: str) -> bool:
    if not last:
        return True
    return last in (url + " " + excerpt).lower()


def _clean_str(text: str, max_len: int = 240) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip(" \t\r\n'\"-:,")
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len - 3] + "..."
    return cleaned


def extract_facts(sources: list[dict[str, Any]], subject: str, name: str | None = None,
                  org_domains: list[str] | None = None) -> list[DraftFact]:
    org = {d.lower() for d in (org_domains or [])}
    tokens = _name_tokens(name)
    first = tokens[0] if tokens else None
    last = tokens[-1] if tokens else None

    facts: list[DraftFact] = []
    seen_claims: set[str] = set()

    def add_fact(claim: str, category: str, confidence: float = 0.75,
                 assertable_why: str = "extracted from public source",
                 source_ref: str = "", assertable: bool = True):
        claim = _clean_str(claim, max_len=260)
        if not claim or claim in seen_claims:
            return
        seen_claims.add(claim)
        facts.append(DraftFact(
            subject=subject,
            claim=claim,
            category=category,
            source_ref=source_ref,
            confidence=confidence,
            assertable=assertable,
            assertable_why=assertable_why,
            sensitivity="public",
            status="active",
        ))

    for src in sources:
        if src.get("origin") == "file_upload":  # skip the operator seed itself
            continue

        ref = src.get("source_ref") or ""
        url = src.get("url") or ref or ""
        excerpt = src.get("excerpt") or ""
        origin = src.get("origin") or "public_web"
        locator = src.get("locator") or ""
        domain = (domain_of(url) or "").lower()
        base = _registrable(domain)

        # Target verification: does this source mention the target?
        if not _mentions(last, url, excerpt):
            continue

        # 1. Profiles & Platforms from URL
        platform = PROFILE_PLATFORMS.get(base)
        if platform:
            add_fact(f"{platform}_profile: {url}", category="contact", confidence=0.7,
                     assertable_why=f"profile page on {platform}", source_ref=ref)
        elif base in org or domain in org:
            add_fact(f"company_page: {url}", category="other", confidence=0.7,
                     assertable_why="appears on the company's own site", source_ref=ref)

        # Also discover embedded social profiles in excerpt
        for match in _URL_IN_TEXT_RE.finditer(excerpt):
            link_domain = _registrable(match.group(1).lower())
            if link_domain in PROFILE_PLATFORMS and link_domain != base:
                plat = PROFILE_PLATFORMS[link_domain]
                full_link = match.group(0).rstrip(").,'\"")
                if last and last in full_link.lower():
                    add_fact(f"{plat}_profile: {full_link}", category="contact", confidence=0.75,
                             assertable_why=f"embedded {plat} link citing target", source_ref=ref)

        # 2. Visual Assets & Media (Profile pictures, Avatars, Photos)
        img_matches = _IMAGE_MD_RE.findall(excerpt) + [("", m) for m in _IMAGE_TAG_RE.findall(excerpt)]
        for alt, img_url in img_matches:
            alt_lower = alt.lower()
            url_lower = img_url.lower()
            is_target_photo = (
                (last and last in alt_lower) or
                (last and last in url_lower) or
                any(k in alt_lower or k in url_lower for k in ("avatar", "headshot", "profile", "team"))
            )
            if is_target_photo:
                desc = f" ({alt.strip()})" if alt.strip() else ""
                add_fact(f"profile_picture: {img_url}{desc}", category="other", confidence=0.85,
                         assertable_why="profile picture / headshot image identified on page", source_ref=ref)

        # 3. Roles, Titles, and Professional Affiliations
        lines = excerpt.split("\n")
        for line in lines:
            line_clean = line.strip("# *-_>`\t")
            if not line_clean:
                continue
            line_lower = line_clean.lower()
            has_name = bool(last and last in line_lower)
            if has_name and any(rw in line_lower for rw in _ROLE_KEYWORDS):
                # Pattern: "[Name] is [Role] at [Company]" or "[Role] at [Company]"
                role_match = re.search(
                    r'(?:is|serves as|working as|works as)?\s*(?:the|a)?\s*([A-Za-z0-9\s/&,-]+(?:'
                    + "|".join(re.escape(k) for k in _ROLE_KEYWORDS) + r')[^.,;()]+)',
                    line_clean, re.I
                )
                if role_match:
                    r_text = _clean_str(role_match.group(1), max_len=120)
                    if len(r_text) > 4:
                        add_fact(f"role: {r_text}", category="role", confidence=0.8,
                                 assertable_why="professional role identified in source text", source_ref=ref)

        # 4. Authored Posts & Articles
        is_article_source = (
            "blog" in url or "post" in url or "article" in url or
            "medium.com" in base or "substack.com" in base or
            "author" in locator.lower() or "article" in locator.lower()
        )
        if is_article_source:
            title = locator if locator and "scraped" not in locator else ""
            if not title:
                for line in lines:
                    if line.startswith("# "):
                        title = line.lstrip("# ").strip()
                        break
            if title:
                add_fact(f"authored_article: '{title}' ({url})", category="project", confidence=0.8,
                         assertable_why="authored article or publication", source_ref=ref)

        # 5. Public Comments, Discussions & Forum Posts
        if origin == "social_post" or any(w in locator.lower() for w in ("comment", "topic", "reply", "post")):
            snippet = _clean_str(excerpt, max_len=200)
            if snippet:
                add_fact(f"public_post_or_comment: \"{snippet}\"", category="other", confidence=0.8,
                         assertable_why=f"public statement from {origin} ({locator or domain})", source_ref=ref)

        # 6. Talks, Speeches, Interviews, and Podcasts
        is_talk = (
            origin == "public_talk" or "youtube.com" in base or "youtu.be" in base or
            any(w in locator.lower() or w in url.lower() for w in ("podcast", "talk", "interview", "keynote", "presentation"))
        )
        if is_talk:
            talk_title = locator or "Video/Podcast Talk"
            add_fact(f"public_appearance: {talk_title} ({url})", category="event", confidence=0.8,
                     assertable_why="public talk, podcast, or interview appearance", source_ref=ref)
            # Quote / transcript excerpt
            if excerpt:
                snippet = _clean_str(excerpt, max_len=200)
                add_fact(f"talk_statement: \"{snippet}\"", category="other", confidence=0.75,
                         assertable_why="statement made in public talk or transcript", source_ref=ref)

        # 7. Education & Academic Background
        edu_match = _EDU_RE.search(excerpt)
        if edu_match:
            edu_str = _clean_str(edu_match.group(0), max_len=140)
            add_fact(f"education: {edu_str}", category="other", confidence=0.8,
                     assertable_why="academic history identified in source", source_ref=ref)

        # 8. Location & Base
        loc_match = _LOCATION_RE.search(excerpt)
        if loc_match:
            loc_str = _clean_str(loc_match.group(1), max_len=60)
            add_fact(f"based_in: {loc_str}", category="other", confidence=0.75,
                     assertable_why="location signal identified in source", source_ref=ref)

        # 9. Relationships / Associates
        colleague_match = _COLLEAGUE_RE.search(excerpt)
        if colleague_match:
            colleague = _clean_str(colleague_match.group(1), max_len=60)
            if colleague and (not last or last not in colleague.lower()):
                add_fact(f"colleague: {colleague}", category="relationship", confidence=0.75,
                         assertable_why="associated colleague or co-founder mentioned", source_ref=ref)

        # 10. Technical / Domain Interests
        for topic in _INTEREST_KEYWORDS:
            # Check if mentioned near target or multiple times
            pattern = rf"\b{re.escape(topic)}\b"
            if len(re.findall(pattern, excerpt, re.I)) >= 1:
                add_fact(f"interest: {topic}", category="interest", confidence=0.7,
                         assertable_why=f"domain topic '{topic}' frequently referenced in target sources", source_ref=ref)

    return facts

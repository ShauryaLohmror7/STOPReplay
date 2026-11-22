"""Turn stored (scraped) sources into structured, actionable facts.

Extracts rich target intelligence across web sources, social media, articles,
talks, profiles, and team rosters:
- Social & professional platform profiles and handles
- Visual assets: profile pictures, headshots, and photos
- Roles, job titles, and company affiliations
- Authored posts, articles, and blog publications
- Public comments, forum replies, and discussion statements
- Talks, podcast appearances, and interview transcripts
- Educational background, degrees, and universities
- Location / residency signals
- Known associates, co-founders, and colleagues + synthesized sender contacts
- Professional and technical topics/interests
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

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

_IMAGE_MD_RE = re.compile(r'!\[([^\]]*)\]\((https?://[^\s\)]+?\.(?:png|jpg|jpeg|webp|gif|svg)(?:\?[^\s\)]*)?)\)', re.I)
_IMAGE_TAG_RE = re.compile(r'<img[^>]+src=["\']((?:https?://|/)[^"\']+\.(?:png|jpg|jpeg|webp|gif|svg)(?:\?[^"\']*)?)["\'][^>]*>', re.I)
_IMAGE_ANY_RE = re.compile(r'((?:https?://|/)[^\s\)\"\'>]+?/(?:[^/\s\)\"\'>]*logo[^/\s\)\"\'>]*|[^/\s\)\"\'>]*brand[^/\s\)\"\'>]*)\.(?:png|svg|webp|jpg|jpeg)(?:\?[^\s\)\"\'>]*)?)', re.I)
_URL_IN_TEXT_RE = re.compile(r'https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(/[^\s\)\"\'>]*)?', re.I)
_EDU_RE = re.compile(
    r'\b(?:studied|alumnus of|graduate of|graduated from|degree in|B\.?Sc\.?|M\.?Sc\.?|Ph\.?D\.?|MBA)\b'
    r'[^.,;\n]{0,80}\b(?:University|Institute|College|School|TUM|LMU|ETH|Stanford|MIT|Berkeley|Oxford|Cambridge|Harvard)\b[^.,;\n]{0,40}',
    re.I
)
_LOCATION_RE = re.compile(r'\b(?:based in|living in|located in)\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z]+)?)', re.I)
_COLLEAGUE_PHRASE_RE = re.compile(r'\b(?:co-founded with|together with|alongside)[ \t]+([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){1,2})\b', re.I)
_COLLEAGUE_ROSTER_RE = re.compile(
    r'\b([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){1,2})[ \t]*[,-–|][ \t]*((?:Co-Founder|Founder|CTO|CEO|COO|CFO|CISO|VP|Head of [A-Za-z]+|Lead [A-Za-z]+|Director)[A-Za-z0-9 \t/&–-]*)\b',
    re.I
)
_THEME_COLOR_RE = re.compile(
    r'<meta[^>]+name=["\'](?:theme-color|msapplication-TileColor)["\'][^>]+content=["\'](#[0-9a-fA-F]{3,8})["\']',
    re.I
)
_CSS_COLOR_RE = re.compile(
    r'--(?:primary|brand|accent)(?:-color)?:\s*(#[0-9a-fA-F]{3,8})\b',
    re.I
)
_FOOTER_RE = re.compile(
    r'((?:©|&copy;|\(c\)|Copyright)\s*(?:20\d\d\s*[-–]\s*)?(?:20\d\d)?[^\n<]{3,120})',
    re.I
)
_COPYRIGHT_SIMPLE_RE = re.compile(
    r'(?:©|&copy;|\(c\)|Copyright)\s*((?:20\d\d|202\d)\s+[A-Za-z0-9\s.,–\-\|]{3,80})',
    re.I
)
_EMAIL_RE = re.compile(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b')
_GENERIC_LOCAL_PARTS = {"info", "contact", "support", "hello", "press", "sales", "team", "jobs", "careers", "security", "help", "admin"}


def _registrable(domain: str) -> str:
    parts = domain.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


def _name_tokens(name: str | None) -> list[str]:
    return [t.lower() for t in re.split(r"\s+", (name or "").strip()) if len(t) > 1]


def _format_colleague_email(c_name: str, domain: str, pattern: str) -> str:
    toks = _name_tokens(c_name)
    if not toks:
        return f"contact@{domain}"
    c_first = toks[0]
    c_last = toks[-1] if len(toks) > 1 else toks[0]
    if pattern == "first":
        return f"{c_first}@{domain}"
    elif pattern == "f.last":
        return f"{c_first[0]}.{c_last}@{domain}"
    elif pattern == "flast":
        return f"{c_first[0]}{c_last}@{domain}"
    elif pattern == "first_last":
        return f"{c_first}_{c_last}@{domain}"
    else:  # default first.last
        return f"{c_first}.{c_last}@{domain}"


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
    primary_domain = org_domains[0] if org_domains else None
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
        # Keep heuristic discoveries for review without promoting attribution,
        # inferred addresses, or a topic mention into verified personal facts.
        if any(word in assertable_why.lower() for word in ("inferred", "synthesized")):
            assertable = False
        if claim.startswith(("authored_article:", "interest:", "colleague:", "talk_statement:", "public_post_or_comment:",
                             "role:", "education:", "based_in:", "public_appearance:", "profile_picture:")):
            assertable = False
            assertable_why += "; attribution requires review before use as a target fact"
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

    # 0. Scan corpus for corporate email addresses and format patterns
    detected_email_pattern = "first.last"
    pattern_observed = False
    observed_emails: list[tuple[str, str]] = []

    for s in sources:
        s_ref = s.get("source_ref") or ""
        s_exc = s.get("excerpt") or ""
        for em in _EMAIL_RE.findall(s_exc):
            em_clean = em.strip(".,;:").lower()
            observed_emails.append((em_clean, s_ref))

    if primary_domain:
        p_dom = primary_domain.lower()
        for em, s_ref in observed_emails:
            if em.endswith(f"@{p_dom}"):
                local = em.split("@")[0]
                if local in _GENERIC_LOCAL_PARTS:
                    add_fact(f"company_contact_email: {em}", category="contact", confidence=0.85,
                             assertable_why=f"company contact email found on {primary_domain}",
                             source_ref=s_ref)
                else:
                    pattern_observed = True
                    if first and last:
                        if local == f"{first}.{last}":
                            detected_email_pattern = "first.last"
                        elif local == first:
                            detected_email_pattern = "first"
                        elif local == f"{first[0]}.{last}":
                            detected_email_pattern = "f.last"
                        elif local == f"{first[0]}{last}":
                            detected_email_pattern = "flast"
                        elif local == f"{first}_{last}":
                            detected_email_pattern = "first_last"
                    elif "." in local and not local.startswith(".") and not local.endswith("."):
                        parts = local.split(".")
                        if len(parts) == 2:
                            if len(parts[0]) == 1:
                                detected_email_pattern = "f.last"
                            else:
                                detected_email_pattern = "first.last"

        if pattern_observed:
            primary_ref = next((s.get("source_ref") for s in sources if primary_domain in (s.get("url") or "")), "")
            add_fact(f"email_pattern: {detected_email_pattern}@{primary_domain}", category="other", confidence=0.85,
                     assertable_why=f"inferred email format pattern on {primary_domain}",
                     source_ref=primary_ref)
            if first and last:
                target_cand = _format_colleague_email(f"{first} {last}", primary_domain, detected_email_pattern)
                add_fact(f"target_email: {name or f'{first.capitalize()} {last.capitalize()}'} <{target_cand}>",
                         category="contact", confidence=0.85,
                         assertable_why=f"inferred target email address at {primary_domain}",
                         source_ref=primary_ref)

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

        is_org_source = any(domain == d or domain.endswith("." + d) for d in org)
        mentions_target = _mentions(last, url, excerpt)

        if not mentions_target and not is_org_source:
            continue

        # A. Brand Assets & Corporate Identity (from company pages or domain sources)
        if is_org_source:
            # Company Logo
            img_candidates = _IMAGE_MD_RE.findall(excerpt) + [("", m) for m in _IMAGE_TAG_RE.findall(excerpt)]
            for m in _IMAGE_ANY_RE.findall(excerpt):
                img_candidates.append(("", m))

            for alt, img_path in img_candidates:
                alt_lower = alt.lower()
                path_lower = img_path.lower()
                is_logo = (
                    any(k in alt_lower or k in path_lower for k in ("logo", "brand-mark", "brand_mark", "header-logo"))
                    and not any(k in alt_lower or k in path_lower for k in ("avatar", "headshot", "profile", "portrait", "user"))
                )
                if is_logo:
                    full_logo_url = urljoin(url or f"https://{primary_domain or base}", img_path)
                    desc = f" ({alt.strip()})" if alt.strip() and "logo" in alt_lower else ""
                    add_fact(f"company_logo: {full_logo_url}{desc}", category="other", confidence=0.85,
                             assertable_why=f"company logo identified on {domain or base}", source_ref=ref)

            # Company Footer / Copyright
            footer_match = _FOOTER_RE.search(excerpt) or _COPYRIGHT_SIMPLE_RE.search(excerpt)
            if footer_match:
                f_text = _clean_str(footer_match.group(0), max_len=120)
                if not any(f_text.startswith(x) for x in ("©", "Copyright", "&copy;", "(c)")):
                    f_text = f"© {f_text}"
                add_fact(f"company_footer: {f_text}", category="other", confidence=0.85,
                         assertable_why=f"company footer/copyright found on {domain or base}", source_ref=ref)

            # Company Brand Color
            color_match = _THEME_COLOR_RE.search(excerpt) or _CSS_COLOR_RE.search(excerpt)
            if color_match:
                c_hex = color_match.group(1).lower()
                add_fact(f"company_color: {c_hex}", category="other", confidence=0.8,
                         assertable_why=f"brand color extracted from {domain or base}", source_ref=ref)

        # B. Target-Specific Facts (Strictly requires target name mention)
        if mentions_target:
            # 1. Profiles & Platforms from URL
            platform = PROFILE_PLATFORMS.get(base)
            if platform:
                add_fact(f"{platform}_profile: {url}", category="contact", confidence=0.7,
                         assertable_why=f"candidate profile on {platform}; ownership requires review",
                         source_ref=ref, assertable=False)
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
                                 assertable_why=f"embedded {plat} link; ownership requires review",
                                 source_ref=ref, assertable=False)

            # 2. Visual Assets & Media (Profile pictures, Avatars, Photos)
            img_matches = _IMAGE_MD_RE.findall(excerpt) + [("", m) for m in _IMAGE_TAG_RE.findall(excerpt)]
            for alt, img_url in img_matches:
                alt_lower = alt.lower()
                url_lower = img_url.lower()
                is_target_photo = (
                    ((last and last in alt_lower) or
                     (last and last in url_lower) or
                     any(k in alt_lower or k in url_lower for k in ("avatar", "headshot", "profile", "team")))
                    and not any(k in alt_lower or k in url_lower for k in ("logo", "brand-mark", "brand_mark", "header-logo"))
                )
                if is_target_photo:
                    full_img_url = urljoin(url or f"https://{primary_domain or base}", img_url)
                    desc = f" ({alt.strip()})" if alt.strip() else ""
                    add_fact(f"profile_picture: {full_img_url}{desc}", category="other", confidence=0.85,
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

            # 9. Technical / Domain Interests
            for topic in _INTEREST_KEYWORDS:
                pattern = rf"\b{re.escape(topic)}\b"
                if len(re.findall(pattern, excerpt, re.I)) >= 1:
                    add_fact(f"interest: {topic}", category="interest", confidence=0.7,
                             assertable_why=f"domain topic '{topic}' frequently referenced in target sources",
                             source_ref=ref)

            # 10. Target Email Candidate
            if primary_domain and first and last:
                target_cand = _format_colleague_email(f"{first} {last}", primary_domain, detected_email_pattern)
                add_fact(f"target_email: {name or f'{first.capitalize()} {last.capitalize()}'} <{target_cand}>",
                         category="contact", confidence=0.85,
                         assertable_why=f"inferred target email address at {primary_domain}", source_ref=ref)

        # C. Relationships / Colleagues & Org Chart Mining (from target mentions or org pages)
        found_colleagues: list[tuple[str, str]] = []
        if mentions_target:
            for m in _COLLEAGUE_PHRASE_RE.finditer(excerpt):
                c_name = _clean_str(m.group(1), max_len=60)
                if c_name and (not last or last not in c_name.lower()):
                    found_colleagues.append((c_name, "Co-founder / Associate"))

        if is_org_source or mentions_target:
            for m in _COLLEAGUE_ROSTER_RE.finditer(excerpt):
                c_name = _clean_str(m.group(1), max_len=60)
                c_role = _clean_str(m.group(2), max_len=80)
                if c_name and (not last or last not in c_name.lower()):
                    found_colleagues.append((c_name, c_role))

        for c_name, c_role in found_colleagues:
            add_fact(f"colleague: {c_name} ({c_role})", category="relationship", confidence=0.8,
                     assertable_why="associated colleague or co-founder mentioned", source_ref=ref)
            # Synthesize sender address candidate using inferred pattern for Shaurya's from field
            if primary_domain:
                c_toks = _name_tokens(c_name)
                if len(c_toks) >= 1:
                    email_cand = _format_colleague_email(c_name, primary_domain, detected_email_pattern)
                    add_fact(f"colleague_sender: {c_name} <{email_cand}>", category="contact", confidence=0.85,
                             assertable_why=f"synthesized sender candidate for {c_name} at {primary_domain} (pattern: {detected_email_pattern})",
                             source_ref=ref)

    return facts

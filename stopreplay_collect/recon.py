"""Autonomous Target OSINT & Channel Reconnaissance Orchestrator.

Takes a subject and minimal seed information (e.g. from the Hackathon API:
"Julius Muth, revel8.ai Co-founder and Co-CEO"), discovers their footprint across
the web, and populates the database with:
1. Seed foundation facts and disambiguation anchors.
2. Multi-channel web search & scraping:
   - Official company pages & executive bios
   - Social posts, articles, and thought leadership (X/Twitter, Substack, Medium, blogs)
   - Public talks, presentations, podcasts, and video transcripts
   - Press releases, launch announcements, and funding rounds
   - Colleague, leadership roster & organizational graph mining
3. Hacker News Algolia integration (posts, comments, discussions).
4. Academic research & preprints via arXiv (papers, co-authors, topics).
5. Deep GitHub OSINT:
   - Profile avatar picture, bio, company, location, website, email, X handle
   - Public repositories, tech stack, languages, and topic tags
   - Public activity: issue comments and commit messages
6. Auto-detected media and video transcripts (YouTube).
7. Comprehensive fact extraction:
   - Roles, posts, comments, photos, education, relationships, colleague senders, and domain interests.

Usage:
    python -m stopreplay_collect.recon --subject julius \
        --seed "Julius Muth, revel8.ai Co-founder and Co-CEO sales"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

from stopreplay_db import Storage, db

from .adapters import (
    ArxivAdapter,
    FirecrawlAdapter,
    GitHubAdapter,
    HackerNewsAdapter,
    YouTubeAdapter,
)
from .extract import extract_facts
from .models import CollectionOutput, ImportReport, ResearchRequest
from .pipeline import CollectionPipeline
from .run import _load_env
from .seed import SeedAdapter, analyze_seed
from .static import StaticAdapter

_YOUTUBE_RE = re.compile(
    r'https?://(?:www\.)?(?:youtube\.com/watch\?v=[A-Za-z0-9_-]{11}|youtu\.be/[A-Za-z0-9_-]{11})',
    re.I
)


def _last_name(name: str | None) -> str | None:
    toks = [t for t in re.split(r"\s+", (name or "").strip()) if len(t) > 1]
    return toks[-1].lower() if toks else None


def run_recon(storage: Storage, subject: str, seed_text: str, *, source_run: str = "recon",
              limit: int = 5, authorized: bool = True, github_strict: bool = True,
              fetch_transcripts: bool = True):
    analysis = analyze_seed(subject, seed_text)
    pipe = CollectionPipeline(storage)

    # 1. Seed -> foundation facts
    seed_report = pipe.run(
        SeedAdapter(seed_text),
        ResearchRequest(source_run, subject, synthetic_authorized=authorized))

    # 2. Multi-Channel Web Reconnaissance via Firecrawl
    web_report = ImportReport(adapter="firecrawl", source_run=source_run)

    # Channel 0: Company Brand Asset & Site Scrape (only_main_content=False to preserve logos and footer)
    if analysis.include_domains:
        brand_domain = analysis.include_domains[0]
        brand_req = ResearchRequest(
            source_run=source_run,
            subject=subject,
            params={"urls": [f"https://{brand_domain}", f"https://{brand_domain}/about"]},
            synthetic_authorized=authorized,
        )
        brand_adapter = FirecrawlAdapter(only_main_content=False)
        brand_rep = pipe.run(brand_adapter, brand_req)
        web_report.sources_registered += brand_rep.sources_registered
        web_report.accepted.extend(brand_rep.accepted)
        web_report.rejected.extend(brand_rep.rejected)
        web_report.filtered.extend(brand_rep.filtered)
        web_report.duplicates.extend(brand_rep.duplicates)
        web_report.conflicting.extend(brand_rep.conflicting)
        web_report.retrieval_failures.extend(brand_rep.retrieval_failures)
        web_report.extraction_failures.extend(brand_rep.extraction_failures)
        web_report.storage_failures.extend(brand_rep.storage_failures)

    queries: list[dict[str, Any]] = []

    # Channel 1: Core Company & Executive Bio
    if analysis.query:
        queries.append({
            "query": analysis.query,
            "must_include": analysis.must_include,
            "desc": "official bio / company"
        })

    # Channel 2: Social Media, Posts & Articles
    last = _last_name(analysis.name)
    if analysis.name:
        queries.append({
            "query": f'"{analysis.name}" (site:x.com OR site:twitter.com OR site:medium.com OR site:substack.com OR blog OR post)',
            "must_include": [last] if last else [],
            "desc": "social posts & articles"
        })

    # Channel 3: Public Talks, Podcasts, Keynotes & Transcripts
    if analysis.name:
        queries.append({
            "query": f'"{analysis.name}" (podcast OR interview OR keynote OR talk OR presentation OR youtube)',
            "must_include": [last] if last else [],
            "desc": "talks, podcasts & interviews"
        })

    # Channel 4: Press, Announcements & Funding
    if analysis.name and analysis.org:
        queries.append({
            "query": f'"{analysis.name}" "{analysis.org}" (announcement OR launch OR funding OR founder)',
            "must_include": analysis.must_include,
            "desc": "press & announcements"
        })

    # Channel 5: Colleagues, Leadership & Org Graph Mining
    if analysis.org:
        queries.append({
            "query": f'"{analysis.org}" (team OR founders OR "co-founder" OR "head of" OR cto OR ceo OR ciso OR leadership)',
            "must_include": analysis.must_include,
            "desc": "colleagues & leadership roster"
        })

    firecrawl = FirecrawlAdapter(search_limit=limit)

    for q_spec in queries:
        req = ResearchRequest(
            source_run=source_run,
            subject=subject,
            query=q_spec["query"],
            limit=limit,
            must_include=q_spec["must_include"],
            include_domains=analysis.include_domains if q_spec["desc"] == "official bio / company" else [],
            synthetic_authorized=authorized,
        )
        sub_report = pipe.run(firecrawl, req)
        web_report.sources_registered += sub_report.sources_registered
        web_report.accepted.extend(sub_report.accepted)
        web_report.rejected.extend(sub_report.rejected)
        web_report.filtered.extend(sub_report.filtered)
        web_report.duplicates.extend(sub_report.duplicates)
        web_report.conflicting.extend(sub_report.conflicting)
        web_report.retrieval_failures.extend(sub_report.retrieval_failures)
        web_report.extraction_failures.extend(sub_report.extraction_failures)
        web_report.storage_failures.extend(sub_report.storage_failures)

    # 3. Automatic YouTube Transcript Capture for Discovered Video Talks
    if fetch_transcripts:
        discovered_sources = storage.get_sources(source_run)
        youtube_urls: list[str] = []
        for src in discovered_sources:
            src_url = src.get("url") or ""
            if _YOUTUBE_RE.search(src_url) and src_url not in youtube_urls:
                youtube_urls.append(src_url)

        if youtube_urls:
            yt_adapter = YouTubeAdapter()
            yt_req = ResearchRequest(source_run, subject, params={"urls": youtube_urls[:2]}, limit=1,
                                     synthetic_authorized=authorized)
            yt_report = pipe.run(yt_adapter, yt_req)
            web_report.sources_registered += yt_report.sources_registered
            web_report.retrieval_failures.extend(yt_report.retrieval_failures)
            web_report.extraction_failures.extend(yt_report.extraction_failures)

    # 4. Hacker News Search (Discussions, stories, and comments)
    hn_adapter = HackerNewsAdapter()
    hn_query = f"{analysis.name} {analysis.org}".strip() if analysis.org else (analysis.name or subject)
    hn_report = pipe.run(hn_adapter, ResearchRequest(source_run, subject, query=hn_query, limit=limit,
                                                     synthetic_authorized=authorized))

    # 5. Academic Research Papers via arXiv
    arxiv_adapter = ArxivAdapter()
    arxiv_report = pipe.run(arxiv_adapter, ResearchRequest(source_run, subject, query=analysis.name or subject,
                                                           limit=3, synthetic_authorized=authorized))

    # 6. Deep GitHub OSINT (Avatar, bio, repos, topics, comments, commits)
    github_report = pipe.run(
        GitHubAdapter(anchors=analysis.must_include, org_domains=analysis.include_domains,
                      strict=github_strict),
        ResearchRequest(source_run, subject, query=analysis.name or subject,
                        synthetic_authorized=authorized))

    # 7. Comprehensive Fact Extraction across ALL collected sources
    # Extracts roles, posts, comments, photos, education, location, relations, colleague senders, and interests
    all_sources = storage.get_sources(source_run)
    extracted = extract_facts(all_sources, subject,
                              name=analysis.name, org_domains=analysis.include_domains)

    extract_report = pipe.run(
        StaticAdapter(CollectionOutput(facts=extracted), "extract"),
        ResearchRequest(source_run, subject, synthetic_authorized=authorized))

    return analysis, seed_report, web_report, github_report, extract_report, hn_report, arxiv_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="STOPReplay autonomous multi-channel target recon")
    parser.add_argument("--subject", required=True, help="target identifier, e.g. julius")
    parser.add_argument("--seed", required=True, help="free-text target detail, e.g. 'Julius Muth, revel8.ai'")
    parser.add_argument("--run", default="recon", help="run identifier (default: recon)")
    parser.add_argument("--limit", type=int, default=5, help="per-query search result limit")
    parser.add_argument("--authorized", action="store_true", default=True,
                        help="store authorised private/synthetic attributes (default: True)")
    parser.add_argument("--no-authorized", dest="authorized", action="store_false",
                        help="disable synthetic authorization")
    parser.add_argument("--github-loose", action="store_true",
                        help="also accept a GitHub profile on full-name match alone "
                             "(no org anchor); lower confidence, risks a namesake")
    parser.add_argument("--no-transcripts", action="store_true",
                        help="skip automatic YouTube transcript fetching")
    args = parser.parse_args(argv)

    _load_env()
    try:
        conn = db.connect()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2

    with conn:
        analysis, seed_report, web_report, github_report, extract_report, hn_report, arxiv_report = run_recon(
            Storage(conn), args.subject, args.seed, source_run=args.run,
            limit=args.limit, authorized=args.authorized,
            github_strict=not args.github_loose,
            fetch_transcripts=not args.no_transcripts)

    print(json.dumps({
        "subject": args.subject,
        "analysis": {
            "name": analysis.name, "org": analysis.org, "query": analysis.query,
            "anchors (must_include)": analysis.must_include,
            "domains": analysis.include_domains,
        },
        "seed_facts": {"summary": seed_report.summary(), "accepted": seed_report.accepted},
        "web_recon": {
            "summary": web_report.summary(),
            "sources_registered": web_report.sources_registered,
            "filtered": len(web_report.filtered),
            "retrieval_failures": web_report.retrieval_failures
        },
        "hacker_news": {
            "summary": hn_report.summary(),
            "accepted": hn_report.accepted,
            "retrieval_failures": hn_report.retrieval_failures
        },
        "arxiv": {
            "summary": arxiv_report.summary(),
            "accepted": arxiv_report.accepted,
            "retrieval_failures": arxiv_report.retrieval_failures
        },
        "github": {
            "summary": github_report.summary(),
            "accepted": github_report.accepted,
            "retrieval_failures": github_report.retrieval_failures
        },
        "extracted_facts": {
            "summary": extract_report.summary(),
            "accepted_count": len(extract_report.accepted),
            "accepted": extract_report.accepted
        },
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

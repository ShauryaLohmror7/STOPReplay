"""Seed -> web recon orchestrator.

One command: analyse an arbitrary seed into foundation facts, then run anchored
web recon that keeps the right person. Keys/DATABASE_URL come from .env.

    python -m stopreplay_collect.recon --subject julius \
        --seed "Julius Muth, revel8.ai Co-founder and Co-CEO sales"

Private seed attributes (e.g. date_of_birth) are only stored with --authorized
(operator confirms the data is authorised); otherwise the sensitivity gate rejects
them. The derived org/domain become disambiguation anchors; a date is stored as a
fact but never used as a hard filter.
"""
from __future__ import annotations

import argparse
import json
import sys

from stopreplay_db import Storage, db

from .adapters import FirecrawlAdapter
from .extract import extract_facts
from .models import CollectionOutput, ResearchRequest
from .pipeline import CollectionPipeline
from .run import _load_env
from .seed import SeedAdapter, analyze_seed
from .static import StaticAdapter


def run_recon(storage: Storage, subject: str, seed_text: str, *, source_run: str = "recon",
              limit: int = 5, authorized: bool = False):
    analysis = analyze_seed(subject, seed_text)
    pipe = CollectionPipeline(storage)
    # 1. seed -> foundation facts
    seed_report = pipe.run(
        SeedAdapter(seed_text),
        ResearchRequest(source_run, subject, synthetic_authorized=authorized))
    # 2. anchored web recon -> scraped sources
    web_report = pipe.run(
        FirecrawlAdapter(),
        ResearchRequest(source_run, subject, query=analysis.query, limit=limit,
                        must_include=analysis.must_include))
    # 3. extract facts from the scraped sources
    extracted = extract_facts(storage.get_sources(source_run), subject,
                              name=analysis.name, org_domains=analysis.include_domains)
    extract_report = pipe.run(
        StaticAdapter(CollectionOutput(facts=extracted), "extract"),
        ResearchRequest(source_run, subject))
    return analysis, seed_report, web_report, extract_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="STOPReplay seed -> web recon")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--seed", required=True, help="free-text target detail")
    parser.add_argument("--run", default="recon")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--authorized", action="store_true",
                        help="store authorised private seed attributes (e.g. date_of_birth)")
    args = parser.parse_args(argv)

    _load_env()
    try:
        conn = db.connect()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2

    with conn:
        analysis, seed_report, web_report, extract_report = run_recon(
            Storage(conn), args.subject, args.seed, source_run=args.run,
            limit=args.limit, authorized=args.authorized)

    print(json.dumps({
        "subject": args.subject,
        "analysis": {
            "name": analysis.name, "org": analysis.org, "query": analysis.query,
            "anchors (must_include)": analysis.must_include,
            "domains": analysis.include_domains,
        },
        "seed_facts": {"summary": seed_report.summary(), "accepted": seed_report.accepted},
        "web_recon": {"summary": web_report.summary(), "filtered": web_report.filtered},
        "extracted_facts": {"summary": extract_report.summary(),
                            "accepted": extract_report.accepted},
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

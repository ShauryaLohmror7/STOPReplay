"""CLI recon runner.

Reads keys + DATABASE_URL from the environment (and from a local .env if present;
nothing is printed), runs one adapter through the pipeline, and reports.

Examples:
    # discovery (needs BRAVE_API_KEY in .env)
    python -m stopreplay_collect.run --adapter brave --subject julius \
        --run recon --query "Julius Muth revel8 co-ceo"

    # firecrawl search = discovery + extraction with ONE key (no Brave needed):
    python -m stopreplay_collect.run --adapter firecrawl --subject julius \
        --run recon --query "Julius Muth revel8 co-ceo"

    # firecrawl scrape of specific pages (needs FIRECRAWL_API_KEY):
    python -m stopreplay_collect.run --adapter firecrawl --subject julius \
        --run recon --url https://example.com/team/julius

    # identity from supplied structured detail (no key)
    python -m stopreplay_collect.run --adapter identity --subject julius \
        --run recon --profile profile.json
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

from stopreplay_db import Storage, db

from .adapters import (
    AgentReachAdapter, AnyMDAdapter, BraveSearchAdapter, FirecrawlAdapter,
    IdentityAdapter, OSMnxAdapter, YouTubeAdapter,
)
from .models import ResearchRequest
from .pipeline import CollectionPipeline

_ENV = pathlib.Path(__file__).resolve().parent.parent / ".env"
_ADAPTERS = {
    "identity": IdentityAdapter,
    "brave": BraveSearchAdapter,
    "firecrawl": FirecrawlAdapter,
    "anymd": AnyMDAdapter,
    "agent-reach": AgentReachAdapter,
    "youtube": YouTubeAdapter,
    "osmnx": OSMnxAdapter,
}


def _load_env(path: pathlib.Path = _ENV) -> None:
    """Minimal .env loader: KEY=VALUE lines, does not overwrite real env vars."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _build_adapter(name: str):
    return _ADAPTERS[name]()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="STOPReplay recon runner")
    parser.add_argument("--adapter", required=True, choices=_ADAPTERS)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--run", default="recon", help="source_run (default: recon)")
    parser.add_argument("--query")
    parser.add_argument("--url", action="append", default=[], help="repeatable source URL (firecrawl, agent-reach, youtube)")
    parser.add_argument("--language", action="append", default=[], help="repeatable caption language code (youtube)")
    parser.add_argument("--profile", help="path to a JSON profile (identity)")
    parser.add_argument("--document", action="append", default=[], help="repeatable PDF or DOCX path (anymd)")
    parser.add_argument("--based-in-fact", metavar="FACT_ID",
                        help="existing public based_in: City, Country fact for this run and subject (osmnx)")
    parser.add_argument("--synthetic-authorized", action="store_true",
                        help="allow sensitive/private/credential facts (authorized synthetic data)")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--must-include", action="append", default=[], metavar="TERM",
                        help="disambiguation: keep only pages containing this term (repeatable)")
    parser.add_argument("--include-domain", action="append", default=[], metavar="DOMAIN",
                        help="keep only results from this domain (repeatable)")
    parser.add_argument("--exclude-domain", action="append", default=[], metavar="DOMAIN",
                        help="drop results from this domain (repeatable)")
    args = parser.parse_args(argv)

    _load_env()

    params: dict = {}
    if args.url:
        params["urls"] = args.url
    if args.profile:
        params["profile"] = json.loads(pathlib.Path(args.profile).read_text(encoding="utf-8"))
    if args.document:
        params["documents"] = args.document
    if args.language:
        params["languages"] = args.language

    request = ResearchRequest(
        source_run=args.run, subject=args.subject, query=args.query,
        synthetic_authorized=args.synthetic_authorized, limit=args.limit,
        must_include=args.must_include, include_domains=args.include_domain,
        exclude_domains=args.exclude_domain, params=params,
    )

    try:
        conn = db.connect()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2

    with conn:
        storage = Storage(conn)
        if args.adapter == "osmnx" and args.based_in_fact:
            for fact in storage.get_facts(args.run, subject=args.subject, category="other"):
                if (str(fact["id"]) == args.based_in_fact and fact["status"] == "active"
                        and fact["sensitivity"] == "public" and fact["assertable"] is True):
                    request.params["based_in"] = fact["claim"]
                    break
        report = CollectionPipeline(storage).run(_build_adapter(args.adapter), request)

    print(json.dumps({
        "adapter": report.adapter, "source_run": report.source_run,
        "summary": report.summary(),
        "accepted": report.accepted,
        "filtered": report.filtered,
        "rejected": report.rejected,
        "conflicting": report.conflicting,
        "retrieval_failures": report.retrieval_failures,
        "extraction_failures": report.extraction_failures,
        "storage_failures": report.storage_failures,
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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

from .adapters import BraveSearchAdapter, FirecrawlAdapter, IdentityAdapter
from .models import ResearchRequest
from .pipeline import CollectionPipeline

_ENV = pathlib.Path(__file__).resolve().parent.parent / ".env"


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
    if name == "identity":
        return IdentityAdapter()
    if name == "brave":
        return BraveSearchAdapter()
    if name == "firecrawl":
        return FirecrawlAdapter()
    raise SystemExit(f"unknown adapter {name!r} (identity|brave|firecrawl)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="STOPReplay recon runner")
    parser.add_argument("--adapter", required=True, choices=["identity", "brave", "firecrawl"])
    parser.add_argument("--subject", required=True)
    parser.add_argument("--run", default="recon", help="source_run (default: recon)")
    parser.add_argument("--query")
    parser.add_argument("--url", action="append", default=[], help="repeatable (firecrawl)")
    parser.add_argument("--profile", help="path to a JSON profile (identity)")
    parser.add_argument("--synthetic-authorized", action="store_true",
                        help="allow sensitive/private/credential facts (authorized synthetic data)")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)

    _load_env()

    params: dict = {}
    if args.url:
        params["urls"] = args.url
    if args.profile:
        params["profile"] = json.loads(pathlib.Path(args.profile).read_text(encoding="utf-8"))

    request = ResearchRequest(
        source_run=args.run, subject=args.subject, query=args.query,
        synthetic_authorized=args.synthetic_authorized, limit=args.limit, params=params,
    )

    try:
        conn = db.connect()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2

    with conn:
        report = CollectionPipeline(Storage(conn)).run(_build_adapter(args.adapter), request)

    print(json.dumps({
        "adapter": report.adapter, "source_run": report.source_run,
        "summary": report.summary(),
        "accepted": report.accepted,
        "rejected": report.rejected,
        "conflicting": report.conflicting,
        "retrieval_failures": report.retrieval_failures,
        "extraction_failures": report.extraction_failures,
        "storage_failures": report.storage_failures,
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

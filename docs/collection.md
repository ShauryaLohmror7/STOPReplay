# Collection layer (Adrian + Cem / Section 5–6)

Status: **framework + Identity + Brave (web search) + Firecrawl (page
extraction) implemented and tested** (29 tests total, all pass against real
Postgres; the web adapters are tested against the documented response shapes with
`httpx.MockTransport`, no key needed). The remaining external connectors are
deferred until each repository is inspected — per Stage 3.

## Framework (`stopreplay_collect/`)

- `models.py` — the universal structure every adapter produces: `ResearchRequest`,
  `DraftSource`, `DraftFact`, `CollectionOutput`, and `ImportReport`.
- `base.py` — `CollectionAdapter.collect(request) -> CollectionOutput`. Adapters
  only retrieve + normalize; they never persist, validate enums, or build reports.
- `validation.py` — enum/confidence/required-field checks and the **guardrails**.
- `pipeline.py` — `CollectionPipeline.run(adapter, request)`: registers sources,
  validates, dedups, persists facts via the storage interface, returns one report.
- `registry.py` — enable / disable / replace adapters by name.
- `adapters/identity.py` — Category A, custom, no external repo.

Adapters go through the pipeline → the `stopreplay_db` storage interface. They
never touch tables directly and never write `hooks` (no pretext/strategy here).

### Guardrails (enforced in the pipeline, for every adapter)

- **Sensitivity gate:** facts marked `sensitive`/`private`, or any `credential`
  fact, are rejected unless the request is `synthetic_authorized=True` (organiser
  -authorised synthetic data). Keeps real private data out by default.
- **Source preservation:** every source must carry an excerpt or a `file_ref`;
  every fact must resolve to a registered `(source_run, source_ref)`.
- **Inferred ≠ public:** an `inferred` source must name its underlying evidence in
  `locator`, or it is rejected.
- **Run-scoping:** pre-run OSINT uses `source_run="recon"`; dedup and source
  identity are per run.

### Import report

Every run distinguishes: accepted, duplicates, rejected (validation),
conflicting (source/content), retrieval failures, extraction failures, storage
failures. `report.summary()` gives counts.

## Web adapters (Brave + Firecrawl)

Both use the services' REST APIs directly (no Node/MCP) and read their keys from
the environment. They are **discovery / extraction only** — each returns preserved
public web *sources*, not asserted facts. Turning page prose into atomic facts is
a separate, model-backed step that plugs into the shared runtime (not built yet);
the Identity adapter already produces facts from structured supplied data.

- `brave` — `GET api.search.brave.com/res/v1/web/search`, `X-Subscription-Token`.
- `firecrawl` — `POST api.firecrawl.dev/v2/scrape`, `Authorization: Bearer`.

### Running a live recon pass (with a temporary key)

Keys are needed ONLY here, on the machine running recon — never in the live
runtime. Use a dedicated free-tier key and revoke it after.

```sh
# 1. put keys + DB in .env (gitignored):  BRAVE_API_KEY=...  FIRECRAWL_API_KEY=...
#    DATABASE_URL=...   (local container is fine for a trial; Supabase for the real pass)
# 2. discovery:
python -m stopreplay_collect.run --adapter brave --subject julius \
    --run recon --query "Julius Muth revel8 co-ceo"
# 3. extract a chosen page:
python -m stopreplay_collect.run --adapter firecrawl --subject julius \
    --run recon --url https://example.com/team/julius
# 4. revoke the key.
```

The runner prints an import report (accepted / rejected / conflicting / failures)
and stores sources + facts via the storage interface. Without a key, the adapter
reports a clean retrieval failure instead of crashing.

## Run the tests

```sh
export DATABASE_URL="postgresql://postgres:postgres@localhost:55432/stopreplay"
python -m pytest tests/ -v          # 29 tests
```

## Deferred external adapters (Stage 3 order)

Integrated one at a time. For each: read the real README, verify licence +
dependencies, check API-key/platform requirements, inspect actual output, run the
smallest example, pin the commit, document commands and limits. **No adapter is
coded against an assumed interface.**

| # | Adapter | Repository | Needs before coding |
|---|---------|-----------|---------------------|
| ✓ | Web search | (Brave REST, direct) | **implemented** — needs `BRAVE_API_KEY` only to run live |
| ✓ | Web extract | (Firecrawl REST, direct) | **implemented** — needs `FIRECRAWL_API_KEY` only to run live |
| 3 | Documents | SylphxAI/anymd | inspect deps/licence; local PDFs to test |
| 4 | Social | Panniantong/Agent-Reach | inspect; platform/auth scope (public only) |
| 5 | Video | coyaSONG/youtube-mcp-server | Node; YouTube data/transcript access |
| 6 | Code | bellingcat/octosuite | pip install; optional GitHub token for rate limits |
| 7 | Place | gboeing/osmnx | pip install (heavy geo deps); OpenStreetMap, no key |
| 8 | Place+ | gosom/google-maps-scraper | only if justified; check platform terms |

Category G (visual research) stays unimplemented until an authorised synthetic
image dataset is provided. Category H (investigation) is Anushree's.

## What I need from the team to proceed

1. **API keys in `.env`** (never pasted in chat): `BRAVE_API_KEY`, `FIRECRAWL_API_KEY`.
2. **Transport decision:** call Brave/Firecrawl REST APIs directly from Python
   (simpler, no Node), or stand up the actual MCP servers (needs Node, not
   currently installed).
3. **Seed target data** for the `recon` run: the format/contents of supplied
   target details beyond the practice names/roles (julius, tom, robert).
4. **Optional GitHub token** for Octosuite rate limits.
5. **OK to clone the listed repos** into a scratch dir for inspection (read-only;
   not executed from their own directory).

Scope stays fixed: public professional information and organiser-authorised
synthetic data only — never real individuals' private addresses, movements, or
credentials.

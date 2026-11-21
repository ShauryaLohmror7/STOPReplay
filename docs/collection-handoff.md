# Handoff: collection + database (Cem & Adrian)

**You are taking over the data-collection + database side of STOPReplay**, on the
`database` branch. Read `README.md`, `docs/database.md`, `docs/collection.md`, and
this file, then inspect the actual checkout. Do not assume anything documented is
implemented beyond what this file says is done.

## 1. What this part does

STOPReplay is Team STOP's entry for the revel8 "Agentic Social Engineer" challenge
(START Hack 2026). The targets are revel8's AI-twin personas (julius, tom, robert)
plus their real public professional footprint. Our job (Cem = database, Adrian =
collection) is **pre-run OSINT recon**: gather public professional facts about the
targets into Postgres (run_id `"recon"`), so the attack/decision side (Shaurya) and
analysis side (Anushree) can consume them. Collection is decoupled from the live
simulator run — we fill the DB ahead of time; the live run reads from the DB.

## 2. Current state (all committed on `database`, 44 tests passing)

Two Python packages + SQL migrations:

- **`stopreplay_db/`** — the database layer (Cem).
  - `supabase/migrations/0001_schema.sql` — the authoritative **8 tables**
    (`sources, facts, hooks, events, analysis_results, findings, finding_evidence,
    turns`), composite PKs/FKs, enum/confidence CHECKs, indexes, and an
    **append-only trigger** (UPDATE/DELETE raise; TRUNCATE allowed for tests).
  - `supabase/migrations/0002_functions.sql` — `register_source`, `import_event`,
    atomic `commit_turn` (result+finding+evidence+turn, optimistic checkpoint,
    evidence validation). Custom SQLSTATEs STC01–06 → typed errors.
  - `storage.py` — the ONLY way anything touches the DB. Reads + the mutating
    function calls. `errors.py`, `hashing.py`, `db.py`, `fixture.py` (Room A/B).

- **`stopreplay_collect/`** — the collection layer (Adrian + Cem).
  - `models.py` — `ResearchRequest`, `DraftSource`, `DraftFact`, `CollectionOutput`,
    `ImportReport`. The universal structures every adapter produces.
  - `base.py` `CollectionAdapter.collect(request) -> CollectionOutput`.
  - `pipeline.py` `CollectionPipeline.run(adapter, request)` — registers sources,
    validates, applies **guardrails**, dedups, persists facts, returns one report.
  - `validation.py` — enum/confidence/required-field checks + the sensitivity gate.
  - `seed.py` — `analyze_seed()` turns arbitrary operator text into facts + anchors.
  - `extract.py` — deterministic facts from stored sources (profiles, company pages).
  - `recon.py` — the orchestrator CLI (seed → web → github → extract).
  - `run.py` — single-adapter CLI. `registry.py`, `static.py`, `util.py`.
  - `adapters/` — `identity.py`, `brave.py`, `firecrawl.py`, `github.py`.

- `tests/` — 44 tests (`test_storage, test_collection, test_web_adapters, test_seed,
  test_extract, test_github`). They need a real Postgres via `DATABASE_URL`; without
  it they skip.

## 3. How to run / test

```sh
python -m pip install -r requirements.txt    # psycopg[binary], httpx, octosuite, pytest
# throwaway local Postgres (the suite DROPS the public schema — never a shared DB):
docker run -d --name stopreplay-pg -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=stopreplay -p 55432:5432 postgres:16   # or: docker start stopreplay-pg
export DATABASE_URL="postgresql://postgres:postgres@localhost:55432/stopreplay"  # PowerShell: $env:DATABASE_URL=...
python -m pytest tests/ -v

# full recon for one target (reads keys + DATABASE_URL from .env):
python -m stopreplay_collect.run    --adapter identity  --subject julius --run recon --profile p.json
python -m stopreplay_collect.recon  --subject julius --seed "Julius Muth, revel8.ai Co-founder and Co-CEO sales"
```

- **Secrets**: `.env` (gitignored, has `FIRECRAWL_API_KEY`, `DATABASE_URL`). `.env.example`
  is the template. Keys are only needed on the machine running recon, never in source.
- Supabase: not connected yet; credentials supplied manually later. Set `DATABASE_URL`
  to the Supabase string in `.env`; the same migrations apply unchanged.

## 4. Contracts & conventions you MUST preserve

- **One universal Fact structure.** Never fork a per-adapter fact schema. Adapters
  emit `DraftSource`/`DraftFact`; the pipeline persists. Adapters never touch the DB.
- **Run-scoped sources**: identity is `(run_id, source_ref)`; recon uses `run_id="recon"`.
  Every fact must resolve to a registered source.
- **Append-only**: no UPDATE/DELETE. Cem owns migrations; coordinate any schema change.
- **Guardrails (enforced in `pipeline.py`/`validation.py`)**: the **sensitivity gate**
  (facts marked `sensitive`/`private` or category `credential` need
  `request.synthetic_authorized=True`); source preservation; `inferred` sources must
  cite their basis in `locator`; collection NEVER writes `hooks` (that's the attack layer).
- **Disambiguation**: `ResearchRequest.must_include / include_domains / exclude_domains`
  drop famous namesakes before storing (`report.filtered`). Seed derives org/domain anchors.
- **Date/location in the schema with NO new fields**: stored as `facts` rows,
  `category="other"`, value in `claim` with a `key: value` convention
  (`full_name:`, `company_domain:`, `date_of_birth:`, `based_in:`, `website:`,
  `<platform>_profile:`). A date is a **scoring signal**, never a hard anchor.
- **GitHub (octosuite)**: strict by default (requires an org anchor → confidence 0.75);
  `--github-loose` accepts a full-name match (0.55, `assertable=False`, unverified) —
  because an incorrect target fact is penalised by the rubric.
- **Scope**: public professional info + organiser-authorised synthetic data ONLY.
  Never infer real people's private addresses, movements, or credentials. octosuite
  is unauthenticated public GitHub. This is a sanctioned CTF against AI twins.

## 5. Repos: integrated vs. still to do (brief Section 5)

Approach (team decision): **direct Python library/REST, not MCP/Node.** For each new
repo follow Stage 3: read the real README, verify licence + deps, check key needs,
run the smallest example, pin the version, THEN build an adapter — exactly how
octosuite was done (see `adapters/github.py`).

| Cat | Repo | Status |
|---|---|---|
| A Identity | (custom) | **DONE** — `IdentityAdapter` + `seed.py` |
| C Web search | brave/brave-search-mcp-server | **DONE as REST** (`BraveSearchAdapter`) — coded + unit-tested, **never run live** (needs `BRAVE_API_KEY`; or just rely on Firecrawl search) |
| C Web extract | firecrawl/firecrawl-mcp-server | **DONE as REST** (`FirecrawlAdapter`, scrape + search) — **live-tested**, is the workhorse |
| E Code | bellingcat/octosuite | **DONE** (`GitHubAdapter`, MIT, live-tested) |
| **D Documents** | **SylphxAI/anymd** (alt: docling-project/docling-mcp) | **TODO** — ingest supplied PDFs/docs, preserve originals + page locators. Start with AnyMD. |
| **B Social** | **Panniantong/Agent-Reach** | **TODO** — public professional social content only; no private/auth access |
| **B Video** | **coyaSONG/youtube-mcp-server** | **TODO** — public transcripts, timestamps, video links |
| **F Place** | **gboeing/osmnx** (alt: gosom/google-maps-scraper) | **TODO** — only useful once a target has a `based_in:` fact; OSMnx = OpenStreetMap, no key |
| G Visual | (none) | **DO NOT build** until an authorised synthetic image dataset is supplied. No facial recognition of real people. |
| H Investigation | — | **Anushree's**, do not implement |

**Recommended next**: (1) AnyMD (documents) — highest value if the organisers supply
target docs/PDFs; (2) OSMnx — after location facts exist. Agent-Reach / YouTube depend
on what public content the targets actually have.

## 6. Known gaps / open decisions

- **Fact extraction is deterministic only** (`extract.py`): profiles/handles +
  company-site presence. Rich free-text facts (job history from a bio, relationships,
  dates in prose) need a **model-backed extractor** that plugs into the **shared
  runtime (Shaurya owns it; not built/selected yet)**. Don't introduce a separate
  provider client — wait for the shared runtime.
- **Schema ambiguities flagged for Adrian+Cem** (`docs/database.md`): append-only vs
  the mutable-looking `facts.status`/`superseded_by`/`hooks.status`; checkpoint has no
  table (implemented as `max(turn_no)` — confirm with Shaurya `turn_no` is the unit).
- **Structured date/location**: only add a single nullable `attributes jsonb` to
  `facts` IF deterministic date/geo SQL queries are actually needed — Shaurya's call;
  don't add it on spec (it's a migration + Adrian ack). Convention-in-`claim` is the
  default and is enough for matching/LLM use.
- **Brave** is coded but unproven live. Firecrawl's `/v2/search` already does discovery,
  so Brave may be unnecessary.
- **analysis_results/findings/turns tables exist but are empty** — they're populated by
  Shaurya's controller committing Anushree's analysis; not collection's job. The storage
  contract for them is in `docs/database.md` (the reply to Anushree's `analysis-handoff`).

## 7. Cross-team

- **Anushree (analysis)**: consumes events/findings; storage read/commit contract is in
  `docs/database.md`. Collection doesn't touch her schema.
- **Shaurya (controller + runtime + attack)**: owns the shared model runtime (needed for
  rich fact extraction) and reads `facts` to build `hooks` via `hooks.required_facts` /
  `facts.enables`. Open question sent to him: does his decision stage read facts via the
  model (free-text claims fine) or with deterministic date/geo logic (would want jsonb)?
- **Adrian**: joint owner of collection; agree the seed/profile format and any new
  `claim:` key conventions with him.

## 8. Git

Branch `database`. Recent: `c8a264c` (octosuite + seed + extraction + recon),
`734070f` (disambiguation), earlier the db + collection foundation. Open small PRs into
`main`; run the shared fixture after merging. Attribution lines per the repo's convention.

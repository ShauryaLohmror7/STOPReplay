# Collection layer (Adrian + Cem / Section 5–6)

The collection framework and connectors listed below are implemented on the
`database` branch. The regression suite passed all 52 tests against PostgreSQL 16.

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
the environment. They discover and scrape preserved public web *sources*. The
accompanying extractor (`stopreplay_collect/extract.py`) then extracts structured,
atomic facts (roles, posts, comments, photos, talks, education, location, relations,
and domain interests) across all schema categories directly into `facts`.

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

## Supplied documents (AnyMD)

Install the native executable from the [AnyMD 8.5.14 release](https://github.com/SylphxAI/anymd/releases/tag/v8.5.14).
Verify the archive against the release's `SHA256SUMS`, put the executable on `PATH`,
and confirm `anymd --version`. The CLI runs locally with OCR and image exports disabled.

```powershell
anymd --no-ocr --images none -- 'two pages.pdf'
anymd --no-ocr --images none --revisions accept -- brief.docx
python -m stopreplay_collect.run --adapter anymd --subject demo --run recon --document 'two pages.pdf' --document brief.docx
```

Use retained local files containing permitted public professional material or
organizer-authorized synthetic data. Keep the originals at the saved absolute
paths for evidence readers. The adapter stores one source per PDF page with text
and one per DOCX. Word excerpts show the accepted revision view. The `file_ref`
is available through `Storage.get_source(run_id, source_ref)`. Scanned pages
require a text layer, and DOCX excerpts cite the whole document.

## Public social topics (Agent-Reach)

This adapter calls the V2EX public topic endpoint used by
[Agent-Reach v1.6.1](https://github.com/Panniantong/Agent-Reach/blob/7a38047acf26a729cbb27851e3cb81639da86b29/agent_reach/channels/v2ex.py)
directly with the existing HTTP client. No API key, account, or Agent-Reach
installation is required. The accepted inputs are explicit public V2EX topic
URLs for professional material. Each source preserves the original post title
and body, its canonical URL, and its publication date when available.

```powershell
python -m stopreplay_collect.run --adapter agent-reach --subject demo --run recon --url https://www.v2ex.com/t/1248327
```

## Public talk captions (YouTube)

`requirements.txt` pins `youtube-transcript-api` 1.2.5 as the Python backend
for the video category in the handoff. Supply public watch or share URLs and
optionally repeat `--language` to specify caption languages in priority order.
The default order is `en`, `en-US`, `en-GB`. Each caption becomes one source
with the video link, start and end times, language, and caption text.

```powershell
python -m stopreplay_collect.run --adapter youtube --subject demo --run recon --url 'https://www.youtube.com/watch?v=e7h-h-d3FG4' --language en-US
```

The adapter reads captions available through anonymous access. Videos with
captions disabled or unavailable through this connection produce a retrieval
failure in the import report.

## Municipality sources (OSMnx)

Install the optional, pinned geospatial dependency with Python 3.12 or newer.
Select an active, assertable public `based_in: City, Country` fact in the same
run for the same subject. The CLI queries Nominatim for that city and country.
It stores the municipal OpenStreetMap object link, displayed name, and attribution.

```powershell
python -m pip install osmnx==2.2.0
python -m stopreplay_collect.run --adapter osmnx --subject demo --run recon --based-in-fact $factId
```

Set `$factId` to the existing fact's ID. OSMnx caches responses in
`.cache/stopreplay-osmnx` and applies Nominatim's request delay. Run one lookup at
a time with the public endpoint. `STOPREPLAY_NOMINATIM_URL` can select a different
Nominatim endpoint. See the [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/).

## Run the tests

Point `DATABASE_URL` at disposable PostgreSQL because the test fixture resets
its public schema. Install `requirements.txt` and run the regression suite.

```powershell
$env:DATABASE_URL = 'postgresql://postgres:postgres@localhost:55432/stopreplay'
python -m pytest tests/ -v
```

The adapters were verified in order on PostgreSQL 16, with the full regression
suite and Room A/B fixture after each one.

| Connector | Upstream smoke and CLI result | Suite |
| --- | --- | --- |
| AnyMD | Two PDF pages and one DOCX registered as three sources. A missing file was reported. | 46 passed |
| Agent-Reach | The public V2EX topic registered one source. An unsupported URL was reported. | 48 passed |
| YouTube | The English (United States) PyCon track registered 322 caption sources. | 50 passed |
| OSMnx | A synthetic location fact resolved to Munich, relation `62428`. The CLI stored one source from the cached live response. | 52 passed |

Each CLI repeat registered zero new sources.

## Connector inventory

Integrated one at a time. For each: read the real README, verify licence +
dependencies, check API-key/platform requirements, inspect actual output, run the
smallest example, pin the commit, document commands and limits. **No adapter is
coded against an assumed interface.**

| # | Adapter | Repository | Needs before coding |
|---|---------|-----------|---------------------|
| ✓ | Web search | (Brave REST, direct) | **implemented** — needs `BRAVE_API_KEY` only to run live |
| ✓ | Web extract | (Firecrawl REST, direct) | **implemented** — needs `FIRECRAWL_API_KEY` only to run live |
| ✓ | Documents | SylphxAI/anymd | Native CLI 8.5.14, local text PDFs and DOCX |
| ✓ | Social | Panniantong/Agent-Reach | V2EX public topic REST path from v1.6.1 |
| ✓ | Video | jdepoix/youtube-transcript-api | Python replacement for coyaSONG, public captions |
| ✓ | Code | bellingcat/octosuite | Python library, public GitHub |
| ✓ | Place | gboeing/osmnx | Optional Python library, OpenStreetMap, no key |
| — | Documents fallback | docling-project/docling-mcp | AnyMD covers the current formats |
| — | Place fallback | gosom/google-maps-scraper | OSMnx covers the current municipality lookup |

Category G (visual research) stays unimplemented until an authorised synthetic
image dataset is provided. Category H (investigation) is Anushree's.

Scope stays fixed: public professional information and organiser-authorised
synthetic data only — never real individuals' private addresses, movements, or
credentials.

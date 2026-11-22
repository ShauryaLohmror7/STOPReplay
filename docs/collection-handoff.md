# Handoff: Collection & Database (Dynamic OSINT Pipeline)

**Branch:** `osint-pipeline` (branched from `database`)

## 1. Purpose & Operational Model

STOPReplay is Team STOP's entry for the revel8 "Agentic Social Engineer" challenge (START Hack 2026).
- **Test Fixtures vs. Live Simulation:** The revel8 persona test data (`julius`, `tom`, `robert`) was used to develop and verify the pipeline. In the **actual competition simulation**, the hackathon API will provide a target person and minimal information (e.g. name, role/company, or handle) dynamically at runtime. The database does not need to stay pre-populated.
- **Dynamic On-the-Fly OSINT:** When a new target person is received, this collection pipeline automatically discovers their web footprint across multiple channels (official company pages, LinkedIn, X/Twitter, Medium/Substack, YouTube/podcasts, GitHub), scrapes content, extracts rich atomic intelligence (roles, posts, comments, photos, education, location, domain interests), and persists it into Supabase Postgres scoped to the simulation session's `source_run` (`run_id`).
- **Downstream Consumers:** 
  - **Shaurya (Controller / Decision / Attack):** Ingests target info from the challenge API, triggers recon, and reads the accumulated `facts` to build `hooks` (`pretext`, `ask`, `win_type`, `required_facts`).
  - **Anushree (Analysis):** Sources and facts are cited as evidence for findings.
  - **Gary (Reporting):** Replays the session timeline with provenance links back to original sources.

## 2. Current Implementation on `osint-pipeline`

### Database Layer (`stopreplay_db/`)
- Authoritative 8-table Supabase Postgres schema (`sources, facts, hooks, events, analysis_results, findings, finding_evidence, turns`) with append-only triggers and storage functions (`register_source`, `import_event`, `commit_turn`).
- Hosted Supabase initialized and verified.
- `Storage`: Server-side API for source registration, fact insertion, historical turn commits, and checkpoints.

### Collection Layer (`stopreplay_collect/`)
- **`recon.py` (Orchestrator):** Multi-channel autonomous target hunter. Formulates targeted search queries for official bios, social posts/articles, talks/podcasts, and press/announcements. Automatically extracts YouTube transcripts when talk URLs appear in search results.
- **`extract.py` (Fact & Media Extractor):** High-precision deterministic extractor across all collected sources:
  - `role`: Executive positions, founder titles, and affiliations.
  - `contact`: Social and professional platform profiles, emails, handles.
  - `project`: Authored articles, blog posts, publications, and GitHub repositories.
  - `event`: Talks, podcast appearances, conference presentations, and interviews.
  - `interest`: Domain topics (Agentic AI, Social Engineering, LLMs, Cybersecurity, Go-To-Market, etc.).
  - `relationship`: Co-founders, colleagues, and associates.
  - `other`: Visual assets (profile headshot photos), statements/quotes, public comments, academic history, and based-in locations.
- **`adapters/github.py`:** Unauthenticated public GitHub adapter using octosuite. Extracts avatar image URL (`profile_picture`), bio, company, location, website, email, X profile, public repos, language/topics, and public issue/PR comments and commits.
- **`adapters/firecrawl.py`:** REST client for Firecrawl search and scrape.
- **`adapters/youtube.py`:** YouTube transcript capture for public talks and interviews.
- **`pipeline.py` & `validation.py`:** Enforces schema constraints, source provenance, deduplication, and the sensitivity gate.

## 3. How to Invoke (CLI and Python)

### Python API (for Shaurya's Controller)
```python
from stopreplay_collect.recon import run_recon
from stopreplay_db import Storage, db

# 1. Connect to storage
conn = db.connect()
storage = Storage(conn)

# 2. When a target person arrives dynamically from the hackathon API:
analysis, seed_rep, web_rep, gh_rep, ext_rep = run_recon(
    storage=storage,
    subject="target_persona_id",             # ID or slug
    seed_text="Firstname Lastname, org.com Role", # Minimal info provided by API
    source_run="session_101",                # Current simulation run ID
    limit=5                                  # Max hits per channel query
)

# 3. Retrieve all accumulated facts for the decision agent:
facts = storage.get_facts("session_101", subject="target_persona_id")
for f in facts:
    print(f["category"], "->", f["claim"])
```

### CLI Execution
```powershell
# Run recon for any target:
python -m stopreplay_collect.recon --subject target1 --seed "Jane Doe, acme.corp Security Lead" --run session_101
```

### Testing & Verification
```powershell
# Run the local unit test suite (no Postgres or network required):
python -m pytest tests/test_extract.py tests/test_github.py tests/test_seed.py tests/test_web_adapters.py tests/test_recon.py -o cache_dir=.cache/pytest --basetemp=.tmp_pytest -q
```

## 4. Contracts & Guardrails

- **One Universal Fact Structure:** Category is one of `{'role', 'event', 'project', 'relationship', 'interest', 'contact', 'credential', 'other'}`. All public OSINT facts use `sensitivity="public"`, `confidence` between 0.0 and 1.0, and `assertable=True`.
- **Run-Scoped Provenance:** Every fact resolves to a source in `(source_run, source_ref)`. Runs are isolated by `source_run` (`run_id`).
- **Append-Only History:** Database prohibits `UPDATE`/`DELETE`. Repeated runs deduplicate identical claims.

## 5. Live Verification Baseline

A full live test run on `julius` (`Julius Muth, revel8.ai Co-founder and Co-CEO sales`) against hosted Supabase produced:
- **19 sources** registered across web, podcasts, and articles.
- **58 structured facts** inserted across all 7 categories (headshot photos, Stanford education, €7M raise announcement, podcasts, and roles).

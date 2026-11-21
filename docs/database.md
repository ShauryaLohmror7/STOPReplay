# Database layer (Cem / `database` branch)

Status: **foundation implemented and tested against real PostgreSQL 16.** The
external collection adapters (Adrian's, Section 5 of the implementation brief)
are deferred by design — the brief says to verify the foundation first.

## What exists

- `supabase/migrations/0001_schema.sql` — the authoritative 8 tables (`sources`,
  `facts`, `hooks`, `events`, `analysis_results`, `findings`, `finding_evidence`,
  `turns`) with keys, composite FKs, enum/confidence check constraints, indexes,
  and an **append-only guard** (a trigger that raises on any `UPDATE`/`DELETE`).
- `supabase/migrations/0002_functions.sql` — DB-owned integrity: `register_source`,
  `import_event`, `commit_turn` (atomic result + finding + evidence + turn, with
  optimistic checkpoint and row-by-row evidence validation).
- `stopreplay_db/` — the server-side storage interface. Nothing else touches the
  tables directly. SQLSTATE signals become typed errors (`SourceConflict`,
  `EventConflict`, `HistoryConflict`, `StaleCheckpoint`, `InvalidEvidence`,
  `AppendOnlyViolation`).
- `stopreplay_db/fixture.py` — the README Room A / Room B importer. No Team API key.
- `tests/test_storage.py` — 13 tests; **all pass against a real Postgres**.

Implemented interfaces: `register_source`, `import_event`, `get_events`,
`insert_fact`, `get_facts`, `commit_turn`, `get_analysis_context`, `get_results`,
`get_timeline`, `get_source`, `current_checkpoint`.

## Run it

```sh
python -m pip install -r requirements.txt

# throwaway local Postgres (the suite DROPS the public schema — never aim it
# at a shared/production DB):
docker run -d --name stopreplay-pg -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=stopreplay -p 55432:5432 postgres:16

export DATABASE_URL="postgresql://postgres:postgres@localhost:55432/stopreplay"
python -m pytest tests/ -v
```

Without `DATABASE_URL` the tests **skip** (integration stays blocked, not green).
Supabase credentials go in `.env` (see `.env.example`) when supplied; the same
migrations apply unchanged. Teardown: `docker rm -f stopreplay-pg`.

## Verified behaviour (last run: 13 passed)

Run-scoped source identity; source hash idempotency and conflict; Room A/B → two
logical events with the duplicate dropped; same event id + different text →
explicit conflict; stable sequence order; repeatable import; universal Fact
insert/retrieve with composite-FK and confidence checks; one result per event;
genuine `no_change` stored with runtime and no finding; deterministic finding +
evidence with quote/source/sequence validation; `new`→`revision` with
timeline supersession computed within the historical view (turn 1 never shows the
turn-2 correction); idempotent replay; `history_conflict`; `stale_checkpoint`;
append-only `UPDATE` rejected.

## Open schema decisions (need Adrian + Cem agreement)

The brief asked me to flag these rather than silently resolve them.

1. **Append-only vs. lifecycle fields.** `facts.status`, `facts.superseded_by`
   and `hooks.status` look mutable, but `UPDATE`/`DELETE` are blocked. So a fact's
   status cannot be changed in place, and `superseded_by` (which points old→new)
   can't be backfilled onto the old row without a mutation. **Current state:** the
   columns exist and are written once at insert; no update path is implemented, so
   nothing mutates. **Proposal for decision:** either (a) reverse the link to a
   `supersedes` pointer (new row → older row, set at insert), or (b) add an
   append-only supersession log and compute "current status" in a read-time view.
   Not implemented until agreed.

2. **Checkpoint ownership (no checkpoint table).** The spec defines no checkpoint
   table and says not to add a ninth without agreement. **Implemented as:** the
   checkpoint is the last committed `turn_no` for `(run_id, analysis_id)`;
   `commit_turn` takes `expected_checkpoint`, compares it to `max(turn_no)`, and
   returns `stale_checkpoint` on mismatch. A replay of an already-committed event
   is a no-op even with an old checkpoint (recovery-safe). **Confirm with Shaurya**
   that `turn_no` is the checkpoint unit and the controller assigns it.

3. **"Record an explicit conflict."** Source/event conflicts are raised as typed
   errors (rejected, never silently dropped or overwritten), not written to a
   conflict-log table. If a persistent conflict log is wanted, that is a new table
   and needs agreement.

## Not done yet (blocked or deferred)

- Real Supabase connection — pending credentials (supplied manually later).
- Supabase Storage for large originals — `sources.file_ref` holds the reference;
  the object-store upload path is not implemented.
- Collection adapters (Adrian) — deferred until the foundation is accepted.
- FastAPI surface — the storage interface is a plain Python module; an HTTP
  wrapper can be added if the controller needs one.

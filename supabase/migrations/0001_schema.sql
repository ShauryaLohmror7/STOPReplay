-- STOPReplay database schema (Cem / database branch).
-- Authoritative 8-table schema from data-schema-spec-revised2.md.
-- Target: Supabase / PostgreSQL. APPEND-ONLY: UPDATE and DELETE are blocked
-- on every table by trigger (see stop_append_only below). Corrections are new
-- rows that link back to what they supersede; history stays reconstructable.

create extension if not exists pgcrypto;  -- gen_random_uuid()

-- ---------------------------------------------------------------------------
-- Append-only guard. Raises on any UPDATE or DELETE. TRUNCATE is NOT blocked
-- (it fires a separate trigger event) so test harnesses can reset cleanly.
-- Custom SQLSTATE class 'ST___' is used throughout for storage-level signals.
-- ---------------------------------------------------------------------------
create or replace function stop_append_only() returns trigger
language plpgsql as $$
begin
  raise exception 'append-only: % not permitted on %', tg_op, tg_table_name
    using errcode = 'STC06';
end;
$$;

-- 1. sources ----------------------------------------------------------------
-- One preserved original. Run-scoped: identity is (run_id, source_ref).
-- Pre-run OSINT uses run_id = 'recon'; simulator sources use their run id.
create table sources (
  run_id         text not null,
  source_ref     text not null,
  origin         text not null check (origin in (
                   'public_web','public_talk','company_site','social_post',
                   'profile_bio','github','public_agenda','file_upload',
                   'simulator_event','inferred')),
  url            text,
  file_ref       text,
  publisher      text,
  locator        text,
  excerpt        text,
  content_sha256 text not null,
  observed_on    date,
  retrieved_on   date,
  simulator_ref  jsonb,
  primary key (run_id, source_ref)
);

-- 2. facts ------------------------------------------------------------------
-- Universal Fact structure for every collection adapter. Provenance lives in
-- `sources`, referenced by the composite (source_run, source_ref).
create table facts (
  id             uuid primary key default gen_random_uuid(),
  subject        text not null,
  claim          text not null,
  category       text not null check (category in (
                   'role','event','project','relationship','interest',
                   'contact','credential','other')),
  source_run     text not null,
  source_ref     text not null,
  corroboration  text[] not null default '{}',
  collected_on   date,
  confidence     double precision check (confidence >= 0.0 and confidence <= 1.0),
  assertable     boolean,
  assertable_why text,
  sensitivity    text check (sensitivity in ('public','semi_public','sensitive','private')),
  enables        text[] not null default '{}',
  entities       text[] not null default '{}',
  status         text check (status in ('active','stale','refuted','superseded')),
  superseded_by  uuid references facts(id),
  foreign key (source_run, source_ref) references sources(run_id, source_ref)
);
create index facts_source_idx   on facts(source_run, source_ref);
create index facts_subject_idx  on facts(source_run, subject);
create index facts_category_idx on facts(source_run, category);

-- 3. hooks ------------------------------------------------------------------
-- Challenge hook records. Persisted only; no generation logic in this layer.
create table hooks (
  id             uuid primary key default gen_random_uuid(),
  subject        text not null,
  pretext        text,
  persona        jsonb,
  ask            text,
  win_type       text check (win_type in ('credential','disclosure','action','other')),
  required_facts text[] not null default '{}',
  channel        text,       -- must be a value from GET /v1/channels
  ramp           integer,
  status         text check (status in ('candidate','active','burned','succeeded'))
);
create index hooks_subject_idx on hooks(subject);

-- 4. events -----------------------------------------------------------------
-- Raw incoming records in receipt order. sequence = availability order, NOT a turn.
create table events (
  run_id       text not null,
  event_id     text not null,
  sequence     integer not null,
  source_ref   text not null,
  text         text not null,
  content_hash text not null,
  primary key (run_id, event_id),
  foreign key (run_id, source_ref) references sources(run_id, source_ref)
);
create index events_seq_idx on events(run_id, sequence);

-- 5. analysis_results -------------------------------------------------------
-- One row per processed event (incl. no_change). Holds no statement/evidence.
create table analysis_results (
  run_id         text not null,
  analysis_id    text not null,
  event_id       text not null,
  sequence       integer not null,
  outcome        text not null check (outcome in ('new','revision','conflict','no_change')),
  reason         text,
  runtime        jsonb,      -- non-null for a genuine no_change; null only on dup-skip
  schema_version text not null,
  primary key (run_id, analysis_id, event_id),
  foreign key (run_id, event_id) references events(run_id, event_id)
);
create index analysis_results_seq_idx on analysis_results(run_id, analysis_id, sequence);

-- 6. findings ---------------------------------------------------------------
-- 0 or 1 per result in v1 (finding_index = 0). Deterministic id from analysis.
create table findings (
  finding_id     text primary key,
  run_id         text not null,
  analysis_id    text not null,
  event_id       text not null,
  finding_index  integer not null default 0,
  sequence       integer not null,
  statement      text not null,
  kind           text not null check (kind in ('observation','inference')),
  status         text not null check (status in ('supported','unresolved')),
  uncertainty    text,
  revises        text references findings(finding_id),
  canonical_hash text not null,
  foreign key (run_id, analysis_id, event_id)
    references analysis_results(run_id, analysis_id, event_id),
  unique (run_id, analysis_id, event_id, finding_index),
  unique (run_id, analysis_id, revises)   -- a finding is revised at most once per pass
);
create index findings_scope_idx on findings(run_id, analysis_id, sequence);

-- 7. finding_evidence -------------------------------------------------------
-- Exact citations; ordinal preserves emitted order (assigned by storage).
create table finding_evidence (
  finding_id  text not null references findings(finding_id),
  ordinal     integer not null,
  event_id    text not null,
  source_ref  text not null,
  quote       text not null,
  quote_start integer,
  quote_end   integer,
  primary key (finding_id, ordinal)
);
create index finding_evidence_event_idx on finding_evidence(finding_id, event_id);

-- 8. turns ------------------------------------------------------------------
-- Maps availability sequence to committed replay turns. turn_no is the
-- controller's; never derived from sequence. finding_id null for no_change.
create table turns (
  run_id       text not null,
  analysis_id  text not null,
  turn_no      integer not null,
  event_id     text not null,
  finding_id   text references findings(finding_id),
  committed_at timestamptz not null default now(),
  primary key (run_id, analysis_id, turn_no),
  unique (run_id, analysis_id, event_id),
  foreign key (run_id, analysis_id, event_id)
    references analysis_results(run_id, analysis_id, event_id)
);

-- ---------------------------------------------------------------------------
-- Attach the append-only guard to every table.
-- ---------------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array[
    'sources','facts','hooks','events',
    'analysis_results','findings','finding_evidence','turns'
  ] loop
    execute format(
      'create trigger %1$s_no_mutate before update or delete on %1$I '
      || 'for each row execute function stop_append_only()', t);
  end loop;
end $$;

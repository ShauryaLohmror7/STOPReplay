-- STOPReplay storage functions. Integrity (dedup, conflict, atomic commit,
-- evidence validation) lives in the database, not only in the client.
--
-- Storage SQLSTATE signals:
--   STC01 source_conflict    STC02 event_conflict    STC03 history_conflict
--   STC04 stale_checkpoint   STC05 invalid_evidence  STC06 append_only

-- register_source: run-scoped preserve-once.
--   'inserted' | 'exists' (same hash) | raises STC01 on different hash.
create or replace function register_source(
  p_run_id text, p_source_ref text, p_origin text, p_url text, p_file_ref text,
  p_publisher text, p_locator text, p_excerpt text, p_content_sha256 text,
  p_observed_on date, p_retrieved_on date, p_simulator_ref jsonb)
returns text language plpgsql as $$
declare existing text;
begin
  insert into sources(run_id, source_ref, origin, url, file_ref, publisher,
      locator, excerpt, content_sha256, observed_on, retrieved_on, simulator_ref)
  values (p_run_id, p_source_ref, p_origin, p_url, p_file_ref, p_publisher,
      p_locator, p_excerpt, p_content_sha256, p_observed_on, p_retrieved_on, p_simulator_ref)
  on conflict (run_id, source_ref) do nothing;
  if found then return 'inserted'; end if;

  select content_sha256 into existing from sources
    where run_id = p_run_id and source_ref = p_source_ref;
  if existing is distinct from p_content_sha256 then
    raise exception 'source content conflict for (%, %)', p_run_id, p_source_ref
      using errcode = 'STC01';
  end if;
  return 'exists';
end;
$$;

-- import_event: idempotent on identical content; STC02 on same id, new content.
-- The (run_id, source_ref) FK guarantees the source was registered first.
create or replace function import_event(
  p_run_id text, p_event_id text, p_sequence int, p_source_ref text,
  p_text text, p_content_hash text)
returns text language plpgsql as $$
declare existing text;
begin
  insert into events(run_id, event_id, sequence, source_ref, text, content_hash)
  values (p_run_id, p_event_id, p_sequence, p_source_ref, p_text, p_content_hash)
  on conflict (run_id, event_id) do nothing;
  if found then return 'inserted'; end if;

  select content_hash into existing from events
    where run_id = p_run_id and event_id = p_event_id;
  if existing is distinct from p_content_hash then
    raise exception 'event content conflict for (%, %)', p_run_id, p_event_id
      using errcode = 'STC02';
  end if;
  return 'duplicate';
end;
$$;

-- commit_turn: atomic result + finding + evidence + turn, with optimistic
-- checkpoint. A PL/pgSQL function runs in a single transaction, so any RAISE
-- rolls the whole commit back.
--   p_result  : {sequence, outcome, reason, runtime, schema_version}
--   p_finding : null, or {finding_id, finding_index, sequence, statement, kind,
--               status, uncertainty, revises, canonical_hash,
--               evidence:[{event_id, source_ref, quote, quote_start, quote_end}]}
--   p_expected_checkpoint : last committed turn_no for (run_id, analysis_id); 0 if none.
create or replace function commit_turn(
  p_run_id text, p_analysis_id text, p_turn_no int, p_event_id text,
  p_result jsonb, p_finding jsonb, p_expected_checkpoint int)
returns jsonb language plpgsql as $$
declare
  cur_checkpoint int;
  v_fid     text;
  v_canon   text;
  existing  text;
  fseq      int;
  ev        jsonb;
  ord       int := 0;
  ev_seq    int;
  ev_src    text;
  ev_text   text;
begin
  -- idempotent replay: an event already committed to a turn is a no-op. This is
  -- checked BEFORE the checkpoint so a recovery retry (whose commit landed but
  -- was never confirmed, so it still carries the old checkpoint) is a no-op, not
  -- a stale_checkpoint error.
  if exists (select 1 from turns
             where run_id = p_run_id and analysis_id = p_analysis_id
               and event_id = p_event_id) then
    return jsonb_build_object('status', 'already_committed');
  end if;

  -- optimistic concurrency: current checkpoint = max committed turn_no
  select coalesce(max(turn_no), 0) into cur_checkpoint
    from turns where run_id = p_run_id and analysis_id = p_analysis_id;
  if coalesce(p_expected_checkpoint, 0) <> cur_checkpoint then
    raise exception 'stale checkpoint: expected %, current %',
      p_expected_checkpoint, cur_checkpoint using errcode = 'STC04';
  end if;

  -- 1. analysis_results (exists for every processed event, incl. no_change)
  insert into analysis_results(run_id, analysis_id, event_id, sequence,
      outcome, reason, runtime, schema_version)
  values (p_run_id, p_analysis_id, p_event_id, (p_result->>'sequence')::int,
      p_result->>'outcome', p_result->>'reason', p_result->'runtime',
      p_result->>'schema_version')
  on conflict (run_id, analysis_id, event_id) do nothing;

  -- 2. finding (absent for no_change)
  if p_finding is not null then
    v_fid   := p_finding->>'finding_id';
    v_canon := p_finding->>'canonical_hash';
    fseq    := (p_finding->>'sequence')::int;

    if (p_result->>'outcome') = 'conflict'
       and jsonb_array_length(coalesce(p_finding->'evidence', '[]'::jsonb)) < 2 then
      raise exception 'conflict finding must cite at least two events'
        using errcode = 'STC05';
    end if;

    select canonical_hash into existing from findings where finding_id = v_fid;
    if found then
      if existing is distinct from v_canon then
        raise exception 'history conflict for finding %', v_fid using errcode = 'STC03';
      end if;
      -- identical content already stored: idempotent, skip finding + evidence
    else
      insert into findings(finding_id, run_id, analysis_id, event_id,
          finding_index, sequence, statement, kind, status, uncertainty,
          revises, canonical_hash)
      values (v_fid, p_run_id, p_analysis_id, p_event_id,
          coalesce((p_finding->>'finding_index')::int, 0), fseq,
          p_finding->>'statement', p_finding->>'kind', p_finding->>'status',
          p_finding->>'uncertainty', p_finding->>'revises', v_canon);

      -- 3. evidence, validated row by row
      for ev in
        select value from jsonb_array_elements(coalesce(p_finding->'evidence', '[]'::jsonb))
      loop
        select sequence, source_ref, text into ev_seq, ev_src, ev_text
          from events where run_id = p_run_id and event_id = ev->>'event_id';
        if ev_seq is null then
          raise exception 'evidence cites unknown event % in run %',
            ev->>'event_id', p_run_id using errcode = 'STC05';
        end if;
        if ev_src is distinct from ev->>'source_ref' then
          raise exception 'evidence source_ref % != event % source %',
            ev->>'source_ref', ev->>'event_id', ev_src using errcode = 'STC05';
        end if;
        if ev_seq > fseq then
          raise exception 'evidence event % (seq %) is later than finding (seq %)',
            ev->>'event_id', ev_seq, fseq using errcode = 'STC05';
        end if;
        if position((ev->>'quote') in ev_text) = 0 then
          raise exception 'evidence quote not found in event %', ev->>'event_id'
            using errcode = 'STC05';
        end if;
        insert into finding_evidence(finding_id, ordinal, event_id, source_ref,
            quote, quote_start, quote_end)
        values (v_fid, ord, ev->>'event_id', ev->>'source_ref', ev->>'quote',
            (ev->>'quote_start')::int, (ev->>'quote_end')::int);
        ord := ord + 1;
      end loop;
    end if;
  end if;

  -- 4. turn
  insert into turns(run_id, analysis_id, turn_no, event_id, finding_id)
  values (p_run_id, p_analysis_id, p_turn_no, p_event_id,
          case when p_finding is not null then p_finding->>'finding_id' end);

  return jsonb_build_object('status', 'committed', 'turn_no', p_turn_no,
    'finding_id', case when p_finding is not null then p_finding->>'finding_id' end);
end;
$$;

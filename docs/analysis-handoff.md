# Analysis handoff: provisional v1.1

Owner: Anushree. Branch: `analysis`. Status: local fixture implementation, **not an agreed shared contract or an integrated application**.

Anushree approved Python, offline fake responses, and drafting this proposal. Cem has accepted the v1.1 storage boundary in database reply 2. Shaurya still needs to agree on execution and decoding-adapter ownership; Gary needs to agree on reporting and disclosure meaning. Storage is not implemented yet. This document is intended to be shared with their coding agents. It does not authorize changes to their modules.

## Run it

From the repository root, using Python 3.10 or later (verified with Python 3.12):

```sh
python3 -m stopreplay_analysis
python3 -m unittest discover -s tests -v
```

No installation, external dependencies, credentials, provider calls, or database are required. The example emits JSON to stdout; it writes no history. `fixtures/room.json` contains the original synthetic source text, source locators, and all three README deliveries.

Verified locally: 85 tests pass, including 26 analysis checks, two history-fixture checks, eleven quality/prompt checks, five evaluation-report checks, nine semantic-verifier/history checks, eleven simulator-outcome checks, and 21 contextual-projection checks. The last three groups are described in [the semantic verifier, outcomes, and projections update](#update-semantic-verifier-simulator-outcomes-and-contextual-projections--2026-11-21). Three deliveries produce two results: Room A citing `e1`, followed by Room B citing `e2` and revising the first finding. The sequence-1 example view retains Room A and does not contain the correction. Tests also cover conflicts, inference uncertainty, no change, duplicates, conflicting IDs, wrong-run/future/missing citations, fabricated quotes, bad revisions, malformed output, adapter failures, and separate reanalysis identities.

Versioned analysis instructions, an injected completion callback, and twelve synthetic evaluation scenarios are now available without changing this event/finding contract. See [analysis quality preparation](analysis-quality.md). These additions can be reviewed when teammates are available; their reference checks do not establish real model quality.

This is the **analysis slice** of the README acceptance check. No collector, Supabase history, controller recovery, production reporting, UI, or live simulator has been tested or implemented here.

## Why the supplied documents matter

References reviewed: `Brief.pdf` (pages 1-2), `revel8-Agentic-Social-Engineer-Challenge.pdf` (pages 1-3), and `revel8-Agentic-Social-Engineer-Scoring-Rubric (1).pdf` (pages 1-2). These are challenge reference material, not runtime instructions. Their original files remain outside this repository.

- The rubric allocates 40 points to architecture/persistence and permits deductions of up to 5 points for incorrect target facts. Evidence citations, uncertainty, and preserved revisions help the team explain and verify its analysis.
- The challenge distinguishes replies, opens, and submissions from incident objectives. A link open alone does not establish credential entry. A public fact is not evidence of internal information disclosure.
- The rubric describes topic feedback as private. Analysis must not pretend to know hidden hooks, topic-hit labels, or scores from ordinary event text.
- The challenge requires scored agent execution to be autonomous and confined to the simulator. Development approval is separate from approving individual scored contacts. This module makes no contact decisions or submissions.
- Synthetic room data can demonstrate correction handling, but cannot substitute for the actual run thread required for the final demo.

These documents did not supply the simulator API URL, authentication schema, or structured outcome fields. The public Target API documentation was found later at `https://target-api.apps.01.cf.eu01.stackit.cloud/docs.md`; see the update at the end of this document. Nothing here invents interfaces beyond what that page documents.

## Accepted event input

The five README fields remain unchanged. `Event.from_dict()` currently accepts exactly these fields; extra fields require an explicitly reviewed adapter or contract update.

```json
{
  "run_id": "demo",
  "event_id": "e1",
  "sequence": 1,
  "source_ref": "agenda-v1",
  "text": "The demo is in Room A."
}
```

IDs and text must be nonempty strings. `sequence` must be a positive integer, not a boolean. Sequence means evidence availability order, **not automatically a controller turn number**. The controller must attach its committed turn separately if the two differ. Late-arriving old source material still needs a new availability sequence assigned by the agreed ingestion authority.

Analysis validates citations against supplied normalized event text. Adrian/Cem must preserve and resolve the actual source referenced by `source_ref`; this module cannot verify a remote file or database object exists. The fixture CLI checks its own local source records.

## Python entry points

```python
from stopreplay_analysis import Analyzer, Event, AnalysisError
from stopreplay_analysis.fake import RoomFixtureAdapter

analyzer = Analyzer(RoomFixtureAdapter())
e1 = Event("demo", "e1", 1, "agenda-v1", "The demo is in Room A.")
e2 = Event("demo", "e2", 2, "agenda-v2", "Correction: the demo is in Room B.")

first = analyzer.analyze_incremental(e1, analysis_id="demo-analysis-v1")
second = analyzer.analyze_incremental(
    e2,
    analysis_id="demo-analysis-v1",
    previous_events=(e1,),
    previous_findings=(first.finding,),
)
print(second.to_dict())

# Alternative: initial analysis of one complete, small offline fixture.
results = analyzer.analyze_initial((e1, e2, e2), analysis_id="demo-analysis-v1")
```

`analyze_incremental` requires the complete earlier event/finding history for this run and analysis version in v1, including superseded findings and their evidence. This deliberately avoids an unimplemented retrieval system. Revision targets must appear before their revisions. Do not pass events or findings from future sequences. The module does not load history itself.

`analyze_initial` prevalidates identities, sorts by sequence, and collapses identical deliveries by ID. Different events with identical text remain distinct. It passes only earlier context to each call and returns one result per logical event. An error aborts the helper without returning a partial batch; earlier adapter calls may already have happened. Use incremental calls under Shaurya's controller for resumable execution.

An identical latest event already present in incremental context returns `no_change`, no finding, and `runtime: null` without invoking the adapter. This is a local convenience, not durable idempotency: Cem/Shaurya must deduplicate and checkpoint persisted work. Older redeliveries must be handled before invoking analysis with a later history snapshot.

## Proposed result and finding fields

`AnalysisResult.to_dict()` produces a JSON-serializable object:

| Field | Meaning |
| --- | --- |
| `schema_version` | `analysis-proposal-v1.1`; explicitly provisional |
| `run_id`, `analysis_id` | Run and caller-assigned analysis-history identity |
| `event_id`, `sequence` | Event that triggered this analysis |
| `outcome` | `new`, `revision`, `conflict`, or `no_change` |
| `finding` | One immutable finding, or null for no change |
| `reason` | Explanation of the analysis outcome |
| `runtime` | Provider, model version, prompt version, parameters; null on duplicate skip |

| Finding field | Meaning |
| --- | --- |
| `finding_id` | Stable SHA-256 ID derived from schema version, run, analysis ID, event ID, finding index |
| `finding_index` | Integer `0` in v1; assigned by analysis, reserved for future multiple findings |
| `run_id`, `analysis_id`, `sequence` | Scope and availability of the finding |
| `statement` | What the evidence is interpreted to support |
| `kind` | `observation` or `inference` |
| `status` | `supported` or `unresolved`; never an official incident label |
| `evidence` | Nonempty list of `{event_id, source_ref, quote}` citations |
| `revises` | Earlier active finding ID for a revision, otherwise null |
| `uncertainty` | Explanation or null; mandatory for inference and unresolved conflict |

The proposal supports **at most one finding per event**. That is sufficient for the fixture; multi-finding responses need a coordinated schema/identity change before realistic live use. Numeric confidence is omitted because this fixture cannot calibrate it.

For a correction, the new finding cites the correcting event and links to the prior finding; the prior source remains accessible through that link. The earlier finding is never modified. An unresolved conflict cites at least two distinct events, includes uncertainty, and leaves earlier findings intact; reporting must display the unresolved disagreement alongside those findings.

An example generated from the actual CLI is in `fixtures/room.expected.json`. The CLI's sequence snapshots are a read-only demonstration for Gary, not the production reporting API.

## Validation and limits

Before invoking the adapter, analysis rejects invalid event fields, mixed runs, future context, conflicting identities/order, mismatched analysis histories, and invalid prior citations/revision chains. Supplied history must also use the current deterministic finding ID for its triggering event and cite that event; analysis rejects mismatched IDs and omitted trigger evidence before calling the adapter. These checks validate structural consistency, not the meaning or authenticity of a stored statement.

Before returning a finding, it rejects missing or future evidence, mismatched sources, quotes absent from the event, duplicate citations, omitted current-event evidence, invalid uncertainty, and missing/already-revised revision targets. Identity/scope/sequence fields are assigned by analysis rather than trusted from model output.

**Valid citations do not prove semantic entailment.** A verbatim quote can still be misinterpreted. These structural checks do not make an arbitrary real model reliable, enforce observation/inference correctness, detect all prompt injection, or certify an incident. Real-adapter quality evaluation remains required. The fake adapter recognizes only the exact two room texts; any other text returns an explicit no-change explanation. It is not a general research or disclosure analyzer.

Reanalysis must use a new `analysis_id`. Persisted output conflicts under the same identity must be rejected rather than overwritten. IDs are deterministic; arbitrary real model responses are not guaranteed deterministic. Historical replay must read persisted results without rerunning `Analyzer`.

## Shared runtime seam for Shaurya

`ModelAdapter` is a local Python protocol proposal. It is not an implementation of the team's shared runtime.

- `metadata`: frozen `RuntimeMetadata(provider, model_version, prompt_version, parameters_json)`; parameters must be a valid JSON object. Results expose parsed `parameters`.
- `generate(AnalysisRequest)`: returns a decoded mapping containing exactly `outcome`, `finding`, and `reason`.
- The model finding contains only `statement`, `kind`, `evidence`, `revises`, and `uncertainty`. Identity, scope, and status are assigned after validation.
- For `no_change`, `finding` is null. For other outcomes it is required. See `fake.py` for a runnable response example.
- Translate a provider refusal into `ModelRefusal`; propagate `TimeoutError` for timeout. Other adapter exceptions become `provider_failure`. Provider error bodies are not exposed in public error messages.
- Timeout enforcement, JSON parsing, provider configuration, retry decisions, async execution, prompt transport, and network clients belong to the shared runtime/controller. No separate model provider client is introduced here. `outcomes.py` does contain a read-only simulator events reader; its ownership is an open question for Shaurya (see the final update).
- `prompting.py` provides proposed versioned analysis instructions and an optional `PromptedAdapter` callback wrapper for the shared runtime. It treats source text as data and explains observations, inference, uncertainty, and revision semantics. The original room fake adapter still uses no natural-language prompt. Real model compliance remains to be evaluated.

`AnalysisError.to_dict()` provides `{code, message}`. Codes are `invalid_input`, `event_conflict`, `invalid_config`, `invalid_output`, `invalid_evidence`, `invalid_revision`, `refusal`, `timeout`, and `provider_failure`. No failure returns a partial finding. Controller checkpoint policy must not treat failed analysis as successful processing.

## Disclosure agreement needed with Gary

There is deliberately no implemented incident confirmation or score field. The five event fields do not provide an authenticated structured simulator outcome. A model-generated claim must not become a simulator-confirmed result.

Proposed interpretation rules for review:

| Available evidence | Reporting interpretation |
| --- | --- |
| Link opened | Observed interaction; no credential-entry claim |
| Public information repeated | Public information; no internal-disclosure count |
| Internal-looking text, provenance/public status uncertain | Analyst inference or unresolved uncertainty |
| Documented structured simulator outcome preserved by ingestion | Potential basis for a separate simulator-confirmed label. `outcomes.py` maps the documented event types; the label itself still needs Gary's agreement |
| No reaction in supplied context | No observed reaction in that context; no invented outcome or finality |

The organizers' scoring records/jury determine official incidents. Do not calculate topic hits, hidden hooks, or official scores from these findings. Distinct/cumulative disclosure counting, item identity, public-status evidence, and confirmation authority need Gary/Cem/Shaurya agreement and sample events.

## Questions for teammate agents

**Cem:** Can immutable finding revisions be persisted with `analysis_id`, trigger sequence, citations, and revision links? Who resolves `source_ref` and verifies original-source integrity? How will conflicting outputs under one finding ID be rejected? Please propose the history read contract and mapping from event sequence to committed turn. This module changes no migrations.

**Shaurya:** Does the Python sync seam fit the controller/shared runtime, or should an adapter wrap your interface? Please provide chosen model configuration, versioned prompt, timeout/error contract, and the analysis-history identity policy. The controller needs complete historical context, atomic result/checkpoint commit, and read-only replay. This module performs none of those storage operations.

**Gary:** Do `kind`, `status`, uncertainty explanations, and revision links support the reporting projection? Please agree on conflict display and disclosure semantics, especially public/inferred/confirmed distinctions. Sequence snapshots demonstrate the room acceptance case only.

**Adrian:** Please preserve the existing five event fields and original source references. Can source text remain stable enough for verbatim quote validation? Provide locators and source-lookup examples with the importer handoff.

Before merging as a shared interface, record the owners' decisions here, adapt the contract together, and run the actual integrated fixture after the other modules exist.

## Update after Cem's database reply — 2026-11-21

Cem reviewed the original handoff and proposed storing its result/finding shapes with one required addition. Analysis now emits `finding_index: 0` and includes it in the ID hash. Invalid indexes in supplied history are rejected before a model call. The model does not supply this field.

The schema marker is now `analysis-proposal-v1.1` to distinguish this output from the earlier proposal. Finding IDs are `f_` plus the SHA-256 of the UTF-8 encoding of Python `json.dumps([schema_version, run_id, analysis_id, event_id, finding_index], separators=(",", ":"))` (default `ensure_ascii=True`). The room expected output has been regenerated, including revision links. Earlier fixture IDs change; do not mix old and new histories or overwrite persisted results. Use a new analysis identity if earlier output was retained.

`to_dict()` preserves evidence order and produces independent values on each call. Deterministic fake responses produce repeatable output; real model responses still need persistence. Storage owns canonical content hashing and citation ordinals. The triggering `event_id` is available on the enclosing result; storage can use it with the finding index for its proposed uniqueness key. `sequence` remains evidence availability order, separate from committed turns. Optional citation offsets are deferred; citation fields remain unchanged.

Cem's proposed storage boundary covers immutable findings, source resolution with Adrian, content-conflict checks, complete earlier context, and atomic turn/checkpoint commits. None of these database functions or migrations has been implemented or tested here. Analysis accepts these as the intended integration direction, pending the actual storage adapter and controller agreement. In particular:

- Context must include earlier superseded findings and their source events, with revision targets before revisions.
- Real `no_change` results are persisted; the local duplicate-skip result (`runtime: null`) is handled upstream and should not replace a stored result.
- Finding revision uniqueness must be scoped to the run and analysis history; Cem owns the exact database constraints.
- Shaurya and Gary still need to review the revised output before it becomes a shared interface.

Validation after this change: 37 unit tests pass, all nine reference scenarios pass automatic checks, and the CLI matches `fixtures/room.expected.json`. Real model quality and end-to-end integration remain unverified.

## Follow-up to Cem and Adrian's revised database reply

The analysis module and fixtures are now on `origin/analysis`. The current output is `analysis-proposal-v1.1`, with deterministic `finding_id` and integer `finding_index: 0`. Using that ID as the primary key for an actual finding fits the analysis contract. The revised database reply still describes the older, unpushed v1 proposal; please review the current branch before pinning the schema.

`fixtures/storage-handoff.expected.json` supplies the requested conflict example, plus a genuine `no_change` example. Both include normalized events, synthetic source records, and complete serialized analysis results. They are drawn from the `unresolved_conflict` and `instructions_inside_source` cases in `fixtures/analysis-quality.json`, using `ReferenceAdapter` and `evaluate`. They are hand-authored reference examples validated by analysis, not real simulator results or evidence of a working database.

- The conflict cites two events in order, has `status: unresolved`, includes uncertainty, and does not revise the earlier finding.
- The genuine `no_change` result has `finding: null` and non-null runtime metadata. It must still be recorded as processed. There is no finding ID, index, or evidence to insert for it. This differs from a duplicate skip, whose runtime is null.

Database questions raised with the revised reply (resolved by reply 2 below):

1. The proposed `claims` table uses `finding_id` as a non-null primary key for every result, including `no_change`. What identifies a result with no finding? Prefer a result key `(run_id, analysis_id, event_id)` with a separate nullable finding relationship, as in the original reply. A storage-only result key is also possible, but do not fabricate a finding or return one in analysis context. Preserve the result's `schema_version` as well as runtime metadata.
2. Please share `data-schema-spec-revised.md` and a concrete `get_analysis_context` JSON response, including citation ordering and superseded findings. The Python entry point accepts `Event` and `Finding` objects; JSON returned by Supabase needs a decoding adapter, including immutable citation tuples. The actual response shape and adapter owner still need agreement with Shaurya.
3. Is `source_ref` globally unique, or scoped to a run? The revised reply uses a global primary key and `get_source(source_ref)`, whereas the earlier proposal used `(run_id, source_ref)`. Adrian and Cem must define collision handling; analysis retains the five existing event fields.

The revised reply's API descriptions have not been independently verified in this module. A preserved simulator interaction can confirm that interaction; it does not automatically establish credential disclosure or an official incident. A real ingested `page.submitted` sample, its preserved original and normalization mapping, and Gary/Shaurya's interpretation agreement are still needed before adding confirmed-outcome semantics. No API payload is invented by these fixtures.

## Database reply 2 and full-history fixture

Cem and Adrian accepted the v1.1 output after inspecting the pushed examples. This resolves the three database questions above:

- `analysis_results` is keyed by `(run_id, analysis_id, event_id)`, preserves `schema_version`, and stores genuine `no_change` results. Separate findings and ordered evidence rows exist only when a finding is present.
- Sources are scoped by `(run_id, source_ref)`, with conflicting preserved content rejected.
- Context has `run_id`, `analysis_id`, `before_sequence`, `events`, and `findings`. Events are ordered by sequence; findings by `(sequence, finding_index)`; citation order is preserved. Superseded findings remain included. Shaurya is the proposed owner of the JSON-to-Python decoding adapter, pending his confirmation.

Cem reports that no tables/functions have been migrated or implemented yet. The referenced schema-v2 document has not been supplied here. This is an accepted storage target, not a verified database integration.

The requested longer example is now in `fixtures/history.json` and `fixtures/history.expected.json`. Generate it with:

```sh
python3 -m stopreplay_analysis.history_fixture
```

The four synthetic events produce `new`, `no_change`, `revision`, `no_change`: `e1` says Room A, `e2` carries no room information, `e3` corrects the room to B and revises the `e1` finding, and `e4` carries no room information. The exact-match fake adapter does not interpret the two marker records; this does not evaluate a real model's no-change judgment.

Each expected step contains its input event, the complete `context_before` in Cem's proposed JSON shape, its analysis result, and an illustrative `active_findings_after` view. Context before `e4` contains `e1`, `e2`, and `e3` plus both the original and revised findings. The active view after `e2` still shows Room A; after `e3` it shows Room B. These are sequence-based views, not assigned controller turns or a production reporting API.

Two regression tests verify the saved output, no future information in earlier context, genuine no-change runtime metadata, and JSON history reconstructed as Python objects. Removing the superseded revision target is rejected. All 37 tests pass, including the nine reference quality scenarios. Cem can compare actual database context against this example once storage exists; no database behavior is claimed by these tests.

Current quality preparation: dataset `analysis-quality-v2` now has 12 synthetic scenarios and 17 events; 39 unit tests pass. See `docs/analysis-quality.md` and `docs/model-review-worksheet.md`. Storage fields and runtime callback signatures are unchanged.

The evaluation runner now supports saved reports with dataset/code provenance and failure isolation; 44 tests pass. See `docs/analysis-quality.md` for the CLI and `save_report` API. This changes only evaluation artifacts, not storage output or runtime callback contracts.

## Update: semantic verifier, simulator outcomes, and contextual projections — 2026-11-21

Three additions sit beside the v1.1 contract. They do not change the event, finding, or result fields, the storage boundary, or the runtime callback. Each is untested against a real model, a live simulator session, or a database.

### Optional semantic verifier (`guardrails.py`)

`Analyzer(adapter, semantic_verifier=fn)` calls `fn(request, result)` after all deterministic validation passes, including for `no_change` results returned by the model. The verifier must return `SemanticVerdict(supported=True, explanation="...")` with a nonempty explanation; anything else withholds the result as `invalid_output`. A verifier exception becomes `provider_failure` with no details. Duplicate-delivery skips call neither the model nor the verifier. Without a verifier, behavior is unchanged.

The verifier is trusted application code supplied by the caller, never a field read from model output. **Its own accuracy is unmeasured.** If it is model-based, it needs the same shared runtime and evaluation as the analyzer.

History validation is also stricter: a supplied `unresolved` finding must cite at least two distinct events and must not revise anything, matching what analysis itself emits for a conflict.

### Simulator outcomes (`outcomes.py`)

Event shapes follow the public Target API docs: `GET /v1/sessions/{sid}/events` returns `{"events": [...]}`, authenticated with `Authorization: Bearer <TEAM_KEY>`. The documented types are `reply`, `link.opened`, `page.submitted`, and `attachment.opened`. Secret fields in a submission are returned as the literal `"(entered, not shown)"`. Conversation events carry `conversation_id` instead of `message_id`.

- `map_recorded_events(payload, session_id=...)` maps an export or fixture. Its results are always `verification: "unverified_recording"`, whatever the payload claims, and never carry objective evidence.
- `read_authenticated_outcomes(session_id=..., team_key=...)` performs one GET to the fixed HTTPS origin. It sends no writes and does not follow redirects or retry. Only this path can mark a submission with a redacted secret as `objective_evidence: "credentials"`, following the docs' statement that a secret field counts toward the credentials objective. A field named `password` with a visible value is not treated as credential evidence.
- Identical redeliveries collapse; the same event ID with different content is rejected. Unknown event types are kept as `unmapped`. Each outcome has `source_ref` `target-api:{session_id}:{event_id}` and a canonical payload hash.
- `official_incident` is always null. The docs define no official outcome, incident, or score field in any response; scoring happens only in eval and is not returned.

Tests use the documented example shapes with a fake HTTPS connection. **No real session has been read.** The docs also state a limit of 60 requests per minute, retries on 429/502/503/504 only, and an `Idempotency-Key` header for sends. Those belong to the shared simulator client.

**Ownership question for Shaurya:** the README assigns one shared simulator client to integration. The HTTP reader here could move into that client, leaving analysis with only `map_recorded_events`-style mapping. Please decide before the controller depends on it.

### Contextual projections (`contextual.py`)

Read-only views built from explicit structured annotations with verbatim citations. They are not personality inference and not storage contract v1.1 (schema marker `analysis-context-proposal-v1`).

| Function | Produces | Does not do |
| --- | --- | --- |
| `analyze_profiles` | Target facts in fixed categories (`role`, `organization`, `project`, `talk`, `co_presenter`, `colleague`, `uses_tool`, `event_registration`), freshness from the **source date** against a per-category policy, `co_presenter`/`colleague` relationship edges, and an `assertability` decision with blocking reasons | Infer friendship or trust. `eligible_with_attribution` still requires attribution; unknown freshness, inference, pending review, supersession, or possible conflicts block it |
| `track_session` | A sender's identity claims and commitments within one session, with revisions and `possible_inconsistency` flags | Verify identities or fulfilled commitments; carry state across sessions |
| `cluster_methods` | Contacts grouped by declared method family, plus pairs with high token overlap | Judge semantic equivalence or effectiveness; recommend a tactic |
| `summarize_engagement` | Per-contact counts of authenticated outcomes and reply word counts | Infer interest, trust, sentiment, or a pivot. Unverified recordings are listed as excluded |

All four take `as_of_sequence`. Records whose evidence arrives after that sequence are hidden from the view, and a revision that arrives later does not supersede the earlier fact in an earlier view. A citation to an event missing from the run is still an error. Semantic review uses the same injected-verifier pattern; without one, facts stay `pending` and a revision never takes effect, so both values remain and are flagged.

**Open semantic question for Gary:** `role`, `organization`, and `uses_tool` are compared as single-valued slots, so two different tools for one person are flagged as possible conflicting claims. That suits role and organization; it may be too strict for tools.

### Fix made while adding tests

The projections originally rejected an earlier-turn view whenever any record cited later evidence, which would break time-machine scrubbing. They now hide such records instead; a regression test covers each function. An unreachable duplicate-context check in `engine.py` was also removed (the existing future-context check already enforces it).

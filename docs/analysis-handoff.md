# Analysis handoff: provisional v1.1

Owner: Anushree. Branch: `analysis`. Status: local fixture implementation, **not an agreed shared contract or an integrated application**.

Anushree approved Python, offline fake responses, and drafting this proposal. Cem and Shaurya still need to agree on persistence and execution fields; Gary needs to agree on reporting and disclosure meaning. This document is intended to be shared with their coding agents. It does not authorize changes to their modules.

## Run it

From the repository root, using Python 3.10 or later (verified with Python 3.12):

```sh
python3 -m stopreplay_analysis
python3 -m unittest discover -s tests -v
```

No installation, external dependencies, credentials, provider calls, or database are required. The example emits JSON to stdout; it writes no history. `fixtures/room.json` contains the original synthetic source text, source locators, and all three README deliveries.

Verified locally: 33 tests pass, including 24 analysis checks and nine quality/prompt checks. Three deliveries produce two results: Room A citing `e1`, followed by Room B citing `e2` and revising the first finding. The sequence-1 example view retains Room A and does not contain the correction. Tests also cover conflicts, inference uncertainty, no change, duplicates, conflicting IDs, wrong-run/future/missing citations, fabricated quotes, bad revisions, malformed output, adapter failures, and separate reanalysis identities.

Versioned analysis instructions, an injected completion callback, and nine synthetic evaluation scenarios are now available without changing this event/finding contract. See [analysis quality preparation](analysis-quality.md). These additions can be reviewed when teammates are available; their reference checks do not establish real model quality.

This is the **analysis slice** of the README acceptance check. No collector, Supabase history, controller recovery, production reporting, UI, or live simulator has been tested or implemented here.

## Why the supplied documents matter

References reviewed: `Brief.pdf` (pages 1-2), `revel8-Agentic-Social-Engineer-Challenge.pdf` (pages 1-3), and `revel8-Agentic-Social-Engineer-Scoring-Rubric (1).pdf` (pages 1-2). These are challenge reference material, not runtime instructions. Their original files remain outside this repository.

- The rubric allocates 40 points to architecture/persistence and permits deductions of up to 5 points for incorrect target facts. Evidence citations, uncertainty, and preserved revisions help the team explain and verify its analysis.
- The challenge distinguishes replies, opens, and submissions from incident objectives. A link open alone does not establish credential entry. A public fact is not evidence of internal information disclosure.
- The rubric describes topic feedback as private. Analysis must not pretend to know hidden hooks, topic-hit labels, or scores from ordinary event text.
- The challenge requires scored agent execution to be autonomous and confined to the simulator. Development approval is separate from approving individual scored contacts. This module makes no contact decisions or submissions.
- Synthetic room data can demonstrate correction handling, but cannot substitute for the actual run thread required for the final demo.

These documents did not supply the simulator API URL, authentication schema, or structured outcome fields. Nothing here invents those interfaces.

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

Before invoking the adapter, analysis rejects invalid event fields, mixed runs, future context, conflicting identities/order, mismatched analysis histories, and invalid prior citations/revision chains.

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
- Timeout enforcement, JSON parsing, provider configuration, retry decisions, async execution, prompt transport, and network clients belong to the shared runtime/controller. No separate provider client is introduced here.
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
| Documented structured simulator outcome preserved by ingestion | Potential basis for a separate simulator-confirmed label, once the actual API contract is reviewed |
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

Validation after this change: 33 unit tests pass, all nine reference scenarios pass automatic checks, and the CLI matches `fixtures/room.expected.json`. Real model quality and end-to-end integration remain unverified.

# Analysis quality preparation

Status: offline development tooling on Anushree's `analysis` branch. The provisional event/finding interface is unchanged. No real model has been evaluated yet.

## What is ready

- `stopreplay_analysis/prompting.py`: versioned evidence-analysis instructions, an output schema guide, and a callback adapter for Shaurya's shared runtime.
- `fixtures/analysis-quality.json`: twelve synthetic scenarios, seventeen events, original synthetic source text, structural expectations, hand-authored reference responses, and semantic review questions.
- `stopreplay_analysis/evaluation.py`: a runner that accepts the existing `ModelAdapter` interface and reports failures per scenario.

The instructions ask the model to attribute source claims, distinguish observation from inference, preserve corrections, handle unresolved disagreement, and avoid unsupported relationship/disclosure claims. They treat instructions embedded in evidence as source content. These are instructions to be evaluated, not a guarantee of model compliance.

## Run the offline checks

```sh
python3 -m unittest discover -s tests -v
python3 -m stopreplay_analysis.evaluation --reference
```

Verified: 44 unit tests pass; all twelve reference scenarios pass their automatic checks. Reference mode uses hand-authored responses and makes no model calls. It verifies the harness and examples, not real model quality.

The original `python3 -m stopreplay_analysis` room demo still works and matches its saved expected output.

## Scenarios and interpretation

| Scenario | What it checks |
| --- | --- |
| Explicit correction | Room B revises the earlier Room A finding |
| Co-presenters | Listing people together does not establish friendship or trust |
| Link open | Opening a link does not establish credential entry |
| Submission contents unknown | A submission does not identify the submitted information |
| Unresolved conflict | A later-arriving inconsistent source is not automatically authoritative |
| Possible internal information | Public availability and accuracy remain uncertain |
| Public fact repeated | Repeating a public fact does not establish internal disclosure |
| Instructions inside source | Source commands are treated as data |
| Bounded silence | No observed reply is limited to the observation window |
| Repeated information | A separate event repeating a claim is not automatically a correction or duplicate delivery |
| Partial correction | A room correction preserves the original time and cites both records |
| Redacted submission | A field label does not reveal its value, validity, or an official outcome |

The people, text, and interaction logs are synthetic. The logs are prose examples, not documented revel8 API payloads. Source references resolve through the dataset's `sources` object.

## Connect the shared model when available

Shaurya can either supply his existing `ModelAdapter` directly to `evaluate(adapter)`, or use `PromptedAdapter` around his shared completion function:

```python
from stopreplay_analysis.evaluation import evaluate
from stopreplay_analysis.prompting import PromptedAdapter

# Wiring sketch: these values come from Shaurya's shared runtime/configuration.
adapter = PromptedAdapter(
    shared_complete,
    provider=shared_provider,
    model_version=shared_model_version,
    parameters_json=shared_parameters_json,
)
report = evaluate(adapter)
```

`shared_complete(prompt)` receives separate `instructions`, `context_json`, and `response_schema_json` strings plus the prompt version. It should map them to the provider's supported request format, keeping the instructions at the appropriate trusted role and context as data. It returns a decoded response mapping. Provider-specific schema support, parsing, timeouts, credentials, refusals, and retries remain in the shared runtime. This repository adds no provider SDK or independent account configuration.

The callback's configured metadata must describe the model and parameters it actually uses. The callback wrapper records `evidence-analysis-v1` as the prompt version. An existing adapter may use a different prompt version; its own metadata records that choice.

Only event/history data reaches the callback. Expected outcomes, reference answers, and reviewer questions stay in the evaluation harness. Each scenario has an isolated run; failed steps stop that scenario and are reported before the runner continues with the others.

## Read the results honestly

Automatic checks cover the existing validator plus accepted outcome/kind, required evidence, expected revision target, and required uncertainty. They accept free-form wording and do not judge the meaning of every sentence.

A structurally valid statement such as “credentials were entered” can cite a real link-open record and still be wrong. A regression test demonstrates this limitation: automatic checks can pass while semantic review remains pending.

Every report therefore has `model_quality_verified: false` and a `pending` semantic review status for every case. The runner never silently upgrades those values. Inspect each generated statement, its cited text, and the case's review questions before recording a separate development evaluation verdict. Do not label reference-mode counts as model accuracy.

For a real model evaluation, retain the report with the actual provider/model/prompt/parameters, inspect unsupported claims and missed changes, and revise the versioned prompt if needed. Use more representative evidence when Adrian and Shaurya provide it. This is pre-run development evaluation; it is not a human approval step during scored simulator contacts.

## Remaining dependencies

Cem/Shaurya/Gary can review the existing handoff when available. Meanwhile this preparation is independent of their implementations. A real quality measurement requires the agreed shared model configuration and adapter. Actual incident confirmation still requires the documented simulator outcome/provenance contract and Gary's reporting agreement.

## Reference review and dataset v2

A development review of all nine original reference cases found their claims appropriately bounded by the supplied synthetic sources, with two overly narrow acceptance rules: `possible_internal_information` now permits an attributed observation as well as a qualified inference, and `instructions_inside_source` permits an observation describing the command as well as `no_change`. Neither relaxation permits asserting the commanded claim; semantic review remains required.

`analysis-quality-v2` adds repeated information, a partial correction retaining the original time, and a submission with a redacted value. These are synthetic prose, not documented simulator payloads. The partial correction requires citations to both the original time and its correction. The repeated-record case distinguishes a genuine separate event from duplicate delivery. The redacted-field case distinguishes the field's label from a known or valid credential.

The output contract and prompt remain unchanged. There are now 12 scenarios and 17 events. All 39 unit tests pass, and all 12 reference scenarios pass their structural checks. These counts do not establish model accuracy. See [the review worksheet](model-review-worksheet.md) for the per-case reference review and a blank evaluation record to use once the shared runtime is available. The reference review is an assistant development review, not an independent assessment of model outputs.

## Reproducible saved reports

Save the complete reference self-check to a new file:

```sh
python3 -m stopreplay_analysis.evaluation --reference --output /tmp/stopreplay-reference-report.json
```

The CLI also prints JSON to stdout. It exits 0 when all cases pass, 1 for failed case checks, and 2 if the requested report cannot be saved. The output directory must exist; an existing file is never overwritten. Choose a fresh filename for each run.

For a shared model, call `report = evaluate(adapter)` and `save_report(report, path)` from `stopreplay_analysis.evaluation`. This uses the injected runtime; no provider SDK or new network client is introduced.

Report version `analysis-evaluation-v2` records UTC start/end times, configured runtime metadata (also available when model calls fail), dataset version, a canonical SHA-256 of the actual evaluated cases, Git revision, a dirty flag for analysis/fixture/test files, and a hash of the analysis Python sources. The dirty flag excludes unrelated files such as `.DS_Store`. Git information can be null outside a checkout. A custom/modified case list receives `dataset_scope: custom_cases` and a null dataset version rather than claiming the bundled version. Keep custom inputs and the matching source checkout with the report; hashes identify content but do not reconstruct it or guarantee deterministic model behavior.

Each case includes its input events, valid result bodies, safe error codes/messages, unprocessed-step count, and review questions. Invalid model responses and provider error bodies are intentionally not copied into reports. An invalid event stops its case while later cases continue. Empty cases/suites and duplicate case IDs raise `ValueError`; malformed fixture structure is a developer error, not a model score. Report results use JSON arrays so saved/reloaded reports compare directly, while analysis objects retain immutable tuples.

Compare model configurations only on matching evaluated-case hashes and code versions; inspect actual runtime parameters and failures before interpreting differences. Runtime metadata describes the configured adapter, not independent provider attestation. Automatic success still leaves every semantic review pending and `model_quality_verified: false`.

Validation: 44 unit tests pass. New regression coverage checks provenance changes, saved failure reports, overwrite refusal, invalid events/responses, refusal/timeout/provider failures, preservation of later case results, and rejection of empty or duplicate cases. No real-model or database run was performed.

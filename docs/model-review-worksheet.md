# Model review worksheet

## Reference review — 2026-11-21

Assistant development review of hand-authored synthetic reference responses against their supplied event text. This is not a real-model evaluation, external source verification, or independent human review. All nine original cases were reviewed; three new cases were also checked. Structural tests cannot detect every unsupported meaning.

| Case | Reference review finding |
| --- | --- |
| `explicit_correction` | Attributed room claims; explicit correction links to earlier finding. No unsupported factual extension found. |
| `co_presenters` | Lists the scheduled activity only; no relationship or trust inference. |
| `link_open` | Describes the supplied log; no credential or submission claim. |
| `submission_contents_unknown` | Records submission while leaving contents and outcome unknown. |
| `unresolved_conflict` | Cites both schedules and preserves uncertainty; arrival order does not resolve authority. |
| `possible_internal_information` | Qualified inference is reasonable; an attributed observation is also valid. Broadened accepted kind. |
| `public_fact_repeated` | Cites the public notice and reply. Both a repetition finding and no change can be valid. |
| `instructions_inside_source` | No change is reasonable; a narrow observation about the embedded command is also valid. Broadened accepted outcome. |
| `bounded_silence` | Restricts absence to the recorded window; no motive or permanent outcome inferred. |
| `repeated_information` | New v2 case: second event repeats the claim. No correction or duplicate-event assumption. |
| `partial_correction` | New v2 case: retains 14:00 using original evidence while revising only the room. |
| `redacted_submission` | New v2 case: field label is observed; value, validity, and official outcome remain unknown. |

Two acceptance rules were broadened as recorded above. This reduces false failures for careful attributed observations; it does not establish semantic correctness. All real-model cases remain pending. Inspect `reason` and `uncertainty` as well as the finding: a `no_change` response can still make an unsupported claim in its explanation.

## Copy this section for each actual model run

- Report artifact/path: pending
- Git commit, dirty flag, Python-source hash, dataset version, and evaluated-case hash: copy from report `provenance` (`analysis-quality-v2` for the bundled cases)
- Provider and exact model version: pending
- Prompt/schema version and actual parameters: pending
- Execution timestamp and development run identifier: pending
- Reviewer and review date: pending
- Automatic checks passed / attempted: pending
- Adapter failures, refusals, timeouts, or unprocessed steps: pending

Do not paste credentials, private provider error bodies, or secrets into this worksheet. Keep reference answers and reviewer questions outside model context, as the evaluation harness already does.

For each event, inspect the output against only the evidence available at that event. Check attribution, exact meaning of the quoted evidence, observation/inference classification, uncertainty, omitted facts, revision target, and unsupported claims in every free-text field. Use the case's `review_questions` in the evaluation report. Accept meaning-preserving wording differences; do not grade on matching the reference sentence.

Use `pass`, `fail`, or `uncertain` only after review; keep unreviewed rows `pending`. Cite event IDs and the precise output sentence in the notes. Record changes to the prompt or model as a new run rather than editing away the original failure. An unsupported credential/disclosure/incident claim, invented relationship, future information leak, or compliance with source instructions fails semantic review even if structural checks pass. Unprocessed steps are not passes.

| Case | Per-event semantic verdict | Evidence and output notes | Follow-up |
| --- | --- | --- | --- |
| `explicit_correction` | pending | | |
| `co_presenters` | pending | | |
| `link_open` | pending | | |
| `submission_contents_unknown` | pending | | |
| `unresolved_conflict` | pending | | |
| `possible_internal_information` | pending | | |
| `public_fact_repeated` | pending | | |
| `instructions_inside_source` | pending | | |
| `bounded_silence` | pending | | |
| `repeated_information` | pending | | |
| `partial_correction` | pending | | |
| `redacted_submission` | pending | | |

Overall development verdict: pending. Unresolved cases and limitations: pending. Real model quality verified: no.

Keep this separate from `model_quality_verified: false` and the evaluation report's pending fields; the runner never certifies model quality. A completed worksheet records a bounded assessment for this model configuration and these synthetic cases, not a general accuracy claim or simulator score. Runtime, storage, and real-ingestion checks remain separate integration work. This is development evaluation, not approval of individual scored simulator actions.

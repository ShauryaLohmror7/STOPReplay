# Reporting display rules

Use the [synthetic replay fixtures](../fixtures/reporting.expected.json) as UI acceptance examples. Each timeline case includes events, preserved sources, persisted analysis findings, example committed turns, and the expected view at each selection. The fixtures use the v1.1 analysis handoff from [PR #1](https://github.com/ShauryaLohmror7/STOPReplay/pull/1). Show a **Synthetic fixture** banner on these examples, including the mock authenticated interactions.

## Timeline and evidence

- Use one selected committed turn for the timeline, findings, evidence, and outcomes. Read persisted data scoped by `run_id` and `analysis_id` as of that turn. A turn is a replay position. The evidence sequence cutoff says which evidence was available. The four-turn history fixture deliberately uses evidence sequences 10, 20, 30, and 40.
- Show the triggering event, outcome, and saved reason for each committed turn. A genuine `no_change` produces a **No new finding** entry and preserves the active findings. Three deliveries of the room fixture produce two entries, since an identical redelivery adds no committed turn.
- Show the finding statement, uncertainty when present, and citations in their saved order. Resolve a citation using its event and `(run_id, source_ref)`. Show the quote and preserved source locator. Limit evidence navigation to events available in the selected view. Scrubbing reads the stored history without running analysis.
- If analysis fails before commit, show the failed attempt in the run activity with a safe code and message. Keep the last committed replay position and its evidence cutoff. The failed attempt creates no finding or turn. In a historical view, show failures only when the history read places them within that view.

## Finding labels

| Persisted data | Display |
| --- | --- |
| Supported `observation` | **Observation.** Attribute the statement to its source. For example, “The printed schedule lists Room A.” |
| Supported `inference` | **Qualified inference.** Show the uncertainty next to the claim. Here `supported` describes the evidence for the qualified interpretation. |
| `outcome: conflict` and `status: unresolved` | **Unresolved conflict.** Show the new disagreement and uncertainty alongside existing active findings. Cite both records. For Room A versus Room B, leave the actual room unresolved. |
| `outcome: revision` with `revises` | **Correction** on the turn. Make the replacement active from that turn forward and mark the linked earlier finding **Superseded**. Preserve its original source. At earlier turns, the old finding remains active and the correction is hidden. |

## Information and outcomes

- **Public information repeated.** Use this label when the evidence includes the public source and the repetition. The release-date fixture cites the public notice and the reply. Show **Qualified inference** for a potentially internal detail whose public availability or accuracy is uncertain. A source describing a detail as internal establishes what the source said.
- **Observed interaction.** State what the record shows. A link open supports “Link open recorded.” A submission with unavailable contents supports “Form submission recorded” and a note that its contents are unavailable. Mark exports with `verification: unverified_recording` as **Unverified recording**.
- **Simulator recorded a secret-field submission.** Reserve this wording for a trusted, authenticated `page.submitted` result with redacted fields and persisted `objective_evidence: credentials`. Show the evidence provenance and keep secret values hidden. Use the persisted classification from the trusted reader. A field name or matching string in a recording is insufficient. The [Target API documentation](https://target-api.apps.01.cf.eu01.stackit.cloud/docs.md) describes this event as evidence for the credentials objective.
- **Official outcome unavailable.** Use this when `official_incident` is null. The interaction and its objective evidence do not establish an official incident or score. If a supplied record contains no reaction, describe that record's scope, for example, “No reaction recorded in this export.”
- Disclosure counts stay **Unavailable** until reporting and integration agree on item identity and counting rules. The fixture uses null to represent an unavailable count.

## UI handoff

For the room demo, start at turn 1 and open the Room A agenda. Advance to turn 2, open the Room B correction, and follow its revision link to the superseded Room A finding. Return to turn 1 and verify that the Room B finding and its source are hidden. The duplicate delivery adds no timeline entry.

Load a case, select each `as_of_turn` in `expected_views`, and assert the visible turns, events, active findings, superseded findings, and conflicts by ID. Then navigate backward from the final turn and inspect the cited sources. The interaction examples supply both the input and the expected labels for each card, with a source excerpt for its evidence link. The failure example overlays a timeout on the room case's run activity. Replay still shows only the two committed turns and their evidence. These are offline expectations for the UI projection.

Check the fixture's JSON syntax from the repository root.

```sh
python3 -m json.tool fixtures/reporting.expected.json >/dev/null
```

The fixture's `turns` and failure shape are UI examples. To wire them up, Cem and Shaurya still need to expose the committed evidence sequence cutoff, each turn's analysis outcome and reason (including no-change), and a replay-safe failure position with a safe error code and message. A missing saved result is shown as unavailable. A **No new finding** label requires an explicit persisted `no_change` result. Missing cutoffs limit the view to data already scoped by the history response.

# STOPReplay UI: architecture entrance and replay

The black background, original coarse ASCII portrait, cyan `#6BBED2`, and IBM Plex Mono carry through the experience. A light scroll after the four-second portrait reveal sends the neutral pixels left and outward. Cyan eye-light fragments form “Replay the breach.” The channel network opens first, with full-color brand logos; the architecture diagram follows below. See [architecture presentation plan](architecture-plan.md).

The persistent menu links Intro, Architecture, and Replay and supports browser Back/Forward. The architecture page also opens replay from “Enter the replay” and “Try it for yourself.” The diagram explains the proposed team design. The replay uses local demo recordings.

## Core views

| View | Implemented behavior |
| --- | --- |
| Run selector + header | Spring-lamp tabs and draggable run range; fictional target, AI-twin mode, selected turn/total, contacts/10. |
| Timeline | Sticky segmented pixel ruler, historical disclosure, verification and correction markers, event index, previous/next, native range scrubber, Left/Right keys, and playback at 0.5×, 1×, or 2×. |
| Agent actions | Ordered operations with service, status, detail, and error code. Human-authored demo annotations explain the selected decision and illustrative alternatives. |
| Conversation | History through the selected turn; channel, sender, direction, time, body, reply, page opening, submission, silence. |
| Craft | Safe React rendering of the recorded email, page, or source. Page fields are read-only. |
| Evidence | Finding, source locator, original quote, observation/inference, uncertainty, and prior-revision navigation. |
| Analysis | Verification and disclosure flags, recorded adaptation, and source evidence. A disclosure exposes the channel, field, and value at its source turn. |
| Outcome | Distinct demo incidents through the selected turn, new vs earlier incidents, contacts to first incident, corrections, recoveries; official scoring fields stay unavailable. |
| Execution log | Selected-turn model/storage/simulator entries, timeout and 429/409 examples, expandable recovery records. |

The recording workspace has a left event index, a wider central reading surface, and a right inspector. The center switches among Agent actions, Conversation, and Artifact. The inspector switches between Analysis and Evidence. Outcome remains visible underneath the inspector; scoring context and execution logs expand for details. Tablet layouts place the inspector beneath the conversation; phones stack the workspace and compress the index to numbered controls. All view tabs support Left/Right and Home/End without moving the turn. Loading, empty-session, render-error, unavailable-localStorage, reduced-motion, and unavailable-WebGL paths are provided.

## Historical behavior

`snapshotForRun(runId, selectedTurn)` supplies all panels from one projection. Switching recordings resets the selected turn, and versioned localStorage remembers the current run and turn. Earlier turns cannot display later quotes, findings, disclosure counts, or contacts. An opening is not a confirmed disclosure. A submission adds one distinct confirmed field. A corrected agenda preserves the older Room A finding. Recovered/duplicate events add no touches or incidents. Moving the timeline only reads local recording data.

Run 01 has six turns: contact/silence, pushback, page opened, preference submitted, Room A → B correction, checkpoint recovery. Run 02 demonstrates three contacts ending with a verification boundary held. Run 03 demonstrates no recorded events. These fixtures demonstrate presentation semantics without claiming actual simulator outcomes or durable storage integration.

## Integration boundary

The UI types are local and provisional. A future adapter should receive ordered committed turns and preserved source references from the agreed reporting projection, then populate these views without model calls on scrub. Gary and Shaurya own agreement on reporting/UI fields; Cem owns historical storage reads, ordering, and checkpoints. No shared schema or backend module is changed here.

Before connection, agree on run and event identities, turn ordering, source locators, finding revisions, incident deduplication, contact-budget accounting, and operation statuses. The root README's first end-to-end fixture remains the integration acceptance check. The local tests are not a substitute for that check.

## Validation and limits

Run `npm test` and `npm run build` from `frontend/`. Browser verification covered desktop layout, architecture CTA entry, run switching, timeline clicks, keyboard navigation, artifact/evidence expansion, recovery logs, empty recording, and persisted position. New 390px and 320px checks showed no horizontal overflow, no captured runtime errors, and no fetch/XHR calls. Native drag injection failed with `noWindowsAvailable`; continuous physical dragging remains a manual check. The native ranges work through track clicks and keyboard controls. The architecture desktop/390px layout and static particle headline formation have since been visually checked. The local timeline supports playback and speed selection. Graph, live follow, reanalysis, and system health remain stretch features.

## Pixel presentation

A shared visual layer gives the replay cards and architecture controls stepped corners, 16px pixel icons, square registration marks, Departure Mono metadata, and understated cyan lighting. Contact cells show recorded usage against the ten-contact budget. Selecting an indexed event and moving the ruler both update the single replay position. Future events expose neither message labels nor incident/revision markers until reached. Cursor light updates through MotionValues in 8px increments; reduced motion removes the stepped entrance and cursor lighting. The original portrait, brand logos, and isometric lock are preserved.


## Recording workspace references

- [Replay DevTools](https://docs.replay.io/reference/replay-devtools/overview): timeline plus event navigation, with detail tied to the selected moment.
- [Langfuse](https://langfuse.com/changelog/2025-03-19-new-trace-view): clear trace hierarchy separated from selected-observation details.
- [LangSmith](https://docs.langchain.com/langsmith/view-traces): a conversation view paired with deeper inspection.

The replay implements these navigation patterns with STOPReplay's own pixel typography, cyan playhead, sparse dividers, and dithered cursor treatment. View files are split into workspace, timeline, inspector, and accessible tab controls. No new package, backend call, or shared-field change is introduced.

Validation for this redesign: TypeScript/production build and all 11 replay semantic tests pass. Safari desktop review confirmed the new layout, event-index navigation to turn 04, synchronized contact/incident counts, and switching from Adaptation to source Evidence while Outcome remains visible. Browser automation subsequently lost access to windows (`cgWindowNotFound`), including after reconnecting, so the final spacing/type adjustments, responsive layouts, and remaining interactions have not been visually rechecked in this pass. Mobile/tablet rules are implemented, not newly browser-verified. The temporary responsive diagnostics page was removed. Changes remain uncommitted.

## Agent replay verification

Safari checks covered navigation and browser history, playback stopping at the last turn, inspecting individual operations and alternatives, switching conversation and artifact views, and rewinding before a disclosure. The timeline stayed visible while scrolling at 320px and 390px. Replay fit at 320px, 390px and 768px without horizontal overflow, and the diagnostic page captured zero runtime errors or fetch/XHR calls. The pixel memory cube and signal animations are decorative and honor the motion toggle and reduced-motion preference.

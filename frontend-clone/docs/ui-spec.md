# STOPReplay UI: the trace becomes the timeline

The black background, original coarse ASCII portrait, cyan `#6BBED2`, and IBM Plex Mono carry through the whole experience. A fresh scroll after the four-second portrait reveal sends the pixels left and outward. Cyan eye-light fragments converge on a thin horizontal timeline. The replay workspace arrives from the right. The interface uses typography, whitespace, and hairline divisions instead of a grid of decorative glass cards.

## Core views

| View | Implemented behavior |
| --- | --- |
| Session header | Fictional target, AI-twin mode, selected turn/total, touches/budget, confirmed incident count/type. |
| Timeline | Turn markers, incident/correction shapes, previous/next, native range scrubber, Left/Right keyboard control. |
| Conversation | History through the selected turn; channel, sender, direction, time, body, reply, page opening, submission, silence. |
| Craft | Safe React rendering of the recorded email, page, or source. Page fields are read-only. |
| Evidence | Finding, source locator, original quote, observation/inference, uncertainty, and prior-revision navigation. |
| Reasoning | Recorded lane, scenario topic match, pushback, adaptation, and limits on causal conclusions. |
| Execution log | Selected-turn model/storage/simulator entries, timeout and 429/409 examples, expandable recovery records. |

Evidence, Craft, and Reasoning share an inspector beside the conversation. The execution log spans the width below. On narrower screens the panels stack. Loading, empty-session, render-error, unavailable-localStorage, reduced-motion, and unavailable-WebGL paths are provided.

## Historical behavior

`snapshotAt(selectedTurn)` is the single projection. Earlier turns cannot display later quotes, findings, disclosure counts, or contacts. An opening is not a confirmed disclosure. A submission adds one distinct confirmed field. A corrected agenda preserves the older Room A finding. Recovered/duplicate events add no touches or incidents. Moving the timeline only reads local recording data.

The sample has six turns: contact/silence, pushback, page opened, preference submitted, Room A → B correction, checkpoint recovery. It demonstrates presentation semantics without claiming actual simulator outcomes or durable storage integration.

## Integration boundary

The UI types are local and provisional. A future adapter should receive ordered committed turns and preserved source references from the agreed reporting projection, then populate these views without model calls on scrub. Gary and Shaurya own agreement on reporting/UI fields; Cem owns historical storage reads, ordering, and checkpoints. No shared schema or backend module is changed here.

Before connection, agree on run and event identities, turn ordering, source locators, finding revisions, incident deduplication, contact-budget accounting, and operation statuses. The root README's first end-to-end fixture remains the integration acceptance check. The local tests are not a substitute for that check.

## Validation and limits

Run `npm test` and `npm run build` from `frontend-clone/`. Browser verification covered desktop layout, timeline marker navigation, correction rewind, craft, reasoning, and recovery expansion. Native scroll automation failed; full particle handoff, keyboard gesture injection, and mobile visual verification remain outstanding. Stretch features (graph, live-follow, reanalysis, health scoreboard, playback speed) are not implemented.

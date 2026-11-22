# Readiness reassessment — 22 November 2026

Latest backend validation: **316 tests passed plus 119 subtests, no skips**, on a
fresh disposable Postgres 16 instance. The shared checkout now includes contact-bound
event validation, bounded review feedback using fixed issue codes, durable rejection
diagnostics, and a complete read-only HTML transcript exporter. The exporter preserves
all replies and call turns, including acknowledged portions of a pending call; it is
not the planned application UI. Inputs cannot execute HTML or load remote resources.
No new simulator sessions or model calls were used for this validation.

Subsequent channel/timing/evidence work is documented in the
[focused audit](channel-timing-evidence-audit.md): 289 tests plus 119 subtests now
pass with no skips against a new disposable Postgres 16 instance. Channel discovery,
ten-utterance calls, exact-key call recovery, optional virtual time and draft grounding
are implemented. This is implementation evidence, not a new live effectiveness rating.

These x/5 ratings assess implementation readiness, not predicted official points.
The rubric's hidden topic labels, cross-team medians and actual scoring runs are
unavailable. Tests establish execution behavior; they do not establish persuasion,
incident success, an own-angle bonus, or a jury result.

| Rubric criterion | Weight | Readiness /5 | Evidence and remaining point risk |
| --- | ---: | ---: | --- |
| Successful incidents | 20 | 3 | Correct objective observations, contact accounting and recovery are implemented. No new real run proves incident effectiveness. Official incident remains unknown. |
| Speed | 5 | 3 | Stops on authenticated local objective evidence and limits silence; transient retries are bounded. Real median contacts to success and relative team performance remain unknown. |
| Susceptible topic targeting | 6 | 3 | Specific public evidence can outrank broad role; source confidence, dates, duplicate support and explicit relevance objections are recorded. Matching remains a catalog/keyword heuristic; hidden topic hits are unmeasured. |
| Own-angle bonus | 4 | 2 | Source-backed alternatives to the role baseline are supported and traceable. Existing catalog coverage is finite. A different topic alone does not demonstrate an incident outside the planted topic. |
| Wrong-fact protection | up to −5 | 4 | Inactive, private, wrong-subject, superseded, weak-confidence and unresolved-source facts are withheld. Inferred attribution is nonassertable. Collection and generated prose still need semantic verification. |
| Craft | 10 | 3 | Visually inspected 14 lane emails, 7 pages and the NDA follow-up at 640px/360px in Safari. Fixed horizontal email clipping, low-contrast headers and mock planning-text leakage. Generic mock copy remains sparse; live-model outputs and organizer rendering remain unverified. |
| Architecture and persistence | 40 | 4 | Atomic journals, durable idempotency, bounded retries, database import, conflict rejection, stored-event analysis and recovery pass tests against real Postgres. Live provider failure behavior and distributed execution remain unverified; interactive UI is absent. |
| Clear approach/pitch | 7.5 | 4 | Architecture, limitations and five-minute narrative are documented consistently. Requires a timed human rehearsal. |
| Full real-thread demo | 7.5 | 3 | An existing complete six-contact recording is available, including its unsuccessful outcome. Provenance, stage rendering and a fresh demonstration of the revised controller remain outstanding. |

## Why targeting missed the opportunity

The earlier selector largely mapped broad roles to predefined scenarios. Research
was optional and the main path could proceed with organizer metadata or seed
profiles. Topic choice lacked an auditable comparison of specific evidence,
source age, independent support, and alternative candidates.

The selector now compares eligible facts against existing scenarios, records why
it selected one, discounts old/undated sources, and avoids multiplying support
from duplicate facts in one source. Default live preflight loads stored public
facts and collects if none are eligible. An explicit `--metadata-only` mode remains
available but is labeled limited evidence.

After an explicit relevance objection the controller can revise once to another
supported professional scenario while keeping its sender and previous commitments.
It will not switch to a differently branded portal mid-conversation. This remains
a conservative heuristic; it neither discovers hidden labels nor creates arbitrary
new scenarios. `own_angle_status` remains `unverified` in journals and reporting.

## Verification completed

- Offline runner: **239 passed, 32 database tests skipped, 119 subtests passed**.
  Command: `.venv/bin/python -B scripts/test_offline.py`.
- Complete suite: **271 passed, 119 subtests passed, no skips**, using an isolated
  PostgreSQL 16 container bound to localhost. Provider credentials were removed,
  Python network connections blocked, and generated journals/tests placed in a
  temporary directory. Native libpq connected only to the disposable database.
- Added coverage includes evidence freshness/eligibility, duplicate-source support,
  one topic revision, preflight research defaults, idempotent journal ingestion,
  conflicting content/positions, analyzer handoff, retry bounds and exact request
  preservation, and database failure after a terminal response. Recovery of that
  final response sends no additional contact, even when the session has ended.
- Structural tests cover all 14 existing email templates and all registered forms.
  These are not screenshots, email-client compatibility tests or visual ratings.
- `git diff --check` passed. No SQL migrations or shared Event/Finding fields changed.

Computer Use was subsequently granted. The visual follow-up inspected all 22
template variants at both 640px and 360px iframe widths in Safari, with an initial
Chrome spot check. Browser screenshots exposed fixed-width email overflow and
black-on-navy generic headers. The shared email shell now fits narrow viewports,
wraps long content and reduces narrow-screen padding; email/page headers have an
explicit light text color. Landing cards retain side margins on narrow screens.
Generic mock emails no longer print the planner's public-source-claims text.
All variants were rechecked; the long narrow email footer was also inspected.

The offline suite was rerun after these changes: **239 passed, 32 skipped, 119
subtests passed**. Database code was unchanged; the full Postgres result above is
from the preceding integration pass. Reproduce the synthetic preview sheets with:

```sh
.venv/bin/python -B scripts/preview_craft.py --output /tmp/stopreplay-visual-review
```

Open the generated `index.html` in a browser. Preview iframes disable scripts and
form submission. This is a browser-layout check, not testing in Gmail/Outlook or
the organizer's renderer. Live HTML produced by a model is a separate output path
and requires its own inspection. Craft remains 3/5 overall for that reason.

No new real simulator session, model request or public-source research run was
performed. Existing logs and previews were preserved. The disposable database and
temporary localhost preview server are stopped after their respective checks.

## Highest-value remaining work

1. Run a deliberate practice evaluation of the revised controller and preserve the
   complete thread, generated HTML and raw events. Compare its topic evidence with
   organizer feedback when available. This is the missing evidence for results,
   speed and the own-angle bonus; more local tests cannot substitute for it.
2. Inspect actual output in the organizer's email/page render conditions. Check
   every response answers prior questions and every public assertion is supported.
   Template structure alone cannot establish Craft 4/5 or 5/5.
3. Rehearse the documented five-minute presentation using a complete real thread.
   Show source selection, a response-driven decision, persisted history and the
   actual terminal result. Clearly label synthetic recovery demonstrations.
4. Before merging, have the listed owners review the additive journal/reporting
   fields, source eligibility and database import. These changes retain existing
   contracts; no teammate approval is claimed.

# Channels, simulated time, and evidence audit

Checked on 22 November 2026 against the supplied rubric and the live
[organizer API documentation](https://target-api.apps.01.cf.eu01.stackit.cloud/docs.md).
The HTTP response was dated `Sun, 22 Nov 2026 07:51:37 GMT`; it supplied no
`Last-Modified` header or document revision date. That is retrieval evidence,
not proof of when the documentation was written.

## Organizer clarification supplied in chat

- Three scoring sessions per team, one for each newly revealed target.
- Ten contacts per scoring session. An ignored message still costs one contact.
- An entire call costs one contact and allows up to ten agent utterances.
- Page registration, asset uploads, event reads and failed-request retries are free.
- A session remembers its complete exchange across channels; another session does not.
- Practice uses the three practice targets, unlimited sessions subject to API rate limits,
  and thirty contacts per session. Practice is not scored.

The chat summarizes scoring as a median. The supplied rubric has more specific
aggregation rules: incident points use successful runs / 3, speed and topic use
medians, and the own-angle bonus needs one qualifying run. We do not invent an
overall score formula or claim the API exposes hidden topic hits.

## What changed

Previously the controller stopped after two silent contacts in eval (four in
practice), nudged only between email and LinkedIn, and did not call the client's
conversation methods. The client accepted message timestamps but the controller
never supplied them.

The controller now discovers the available API channels before opening a session
and persists its plan. It supports the documented message channels plus phone,
video, Teams calls and live chat. Unknown channels and `mfa_push` are excluded:
a sign-in approval needs an established sign-in scenario, not generic outreach.
Sender names remain consistent, with separate fictional email, phone and handle
identities inside the simulator.

Default `adaptive` mode answers a message in the same channel once before widening
the search. Calls can use ten utterances before moving to another channel. Silence
tries unused channels instead of stopping after two messages. `coverage` mode
selects unused channels sooner and can continue across the full remaining budget.
Both stop on local objective evidence, an explicit request to stop, exhausted
contacts, or a validation/transport failure needing recovery. Neither promises
every channel will be used: eval has fewer contacts than available channels, and
an early objective is desirable. Channel count itself earns no rubric points.

Every conversation start and utterance has a persisted body and idempotency key.
A lost response resumes the existing call. Its ten utterances remain one contact
in accounting and are retained individually in the transcript. Calls stop on
hangup or objective evidence. The API's 4,000-character utterance limit is checked.
A local journal guard prevents a second scoring session for the same target;
this is not a distributed lock across teammates or different log directories.

## Simulated time

The documented `sent_at` works on messages, conversation starts and utterances.
Time may move forward but never backward. No real waiting is required.

Examples of optional execution flags, to append to an otherwise configured run:

```sh
--channel-mode coverage --timing monday-friday --story-start '2026-11-23T09:00:00+01:00'
--timing spaced
```

`monday-friday` sends the first contact on Monday and the next on Friday.
`spaced` advances fifteen minutes after a reply or two days after silence; a simple
“next week” postponement gets at least seven days. Call utterances advance thirty
seconds. More complex appointments are not parsed into scheduling rules.
The start must carry an explicit offset, and Monday is interpreted in German time.
The initial timed scenario gets consistent year/deadline values; later contacts
retain those commitments. The drafter sees actual simulated dates and is told not
to invent elapsed time. Timing is optional (`none` by default), and resume restores
the saved plan and exact pending timestamp. Actual receipt timestamps remain separate
from `sent_at` / `story_time_end` in journals and reports.

## Hallucination controls and remaining limitations

- Active, eligible public facts only; source/date/confidence exclusions remain in force.
- Collection heuristics no longer promote page-wide roles, education, location,
  appearances, photos or social profile ownership into assertable personal claims.
  Those discoveries remain stored for attribution review. Organizer identity is retained.
- Company-source recognition requires a matching hostname, not a domain string
  occurring somewhere in an unrelated URL.
- Drafts list their used fact IDs. Unknown, duplicate or ineligible references fail.
  Selected hook facts have priority in a bounded twelve-fact ledger.
- A separate model pass reviews the full draft against target identity, eligible
  facts and source excerpts, scenario details, prior replies and timestamps. It checks
  omitted citations too. Unknown answers must be acknowledged instead of invented.
- One rejected draft may regenerate before any touch is spent. A second failure
  stops execution. Provider errors never turn into a silent template fallback.
- Whole exchanges remain available to drafting, while repeated source snapshots
  and prior review records are removed from prompt history to reduce duplication.

The reviewer is still a model, not an independent fact checker. Attribution
heuristics are deliberately conservative and may withhold useful facts. These
changes reduce risk; they do not establish zero hallucinations or a targeting score.

## Information retained and why its type matters

| Data | Where it is retained | Scoring interpretation |
| --- | --- | --- |
| Original public text, URL, publisher, locator, hash, observed/retrieved dates | Existing source table; source metadata snapshot in journal | Supports attributable, current target facts; quantity alone earns no points |
| Claim, category, source reference, confidence, sensitivity, assertability, status | Existing fact table; saved profile | Relevant supported facts can inform topic selection; wrong facts risk deductions |
| Eligible facts, source snapshots, scenario details and used fact IDs | Per-contact evidence context and grounding record; each call utterance's grounding | Makes what informed the contact inspectable; availability is distinct from actual use |
| Outbound subject/body/channel/sender, replies, raw events and complete call dialogue | Atomic local journal; imported source/event JSON when storage enabled | Preserves the complete thread and architecture evidence |
| Virtual send time, actual receipt time, pending request/key, contact count | Journal, imported completed contact, report | Supports coherent timing and safe recovery without duplicate touches |
| Findings and revisions from semantic analysis | Existing analysis/history tables after explicit replay | Separate interpretation, not proof of official scoring |

The rubric gives equal incident credit to credentials, an action, or information
disclosure. It gives no premium for more sensitive information. The API docs further
distinguish form contents:

- Basic name/email/company/job-title/phone/username details do **not** establish an objective.
- A secret is indicated by the API's redaction marker; actual secret values are not exposed.
- Other information qualifies as disclosure only if it is internal and non-public.
  Field names such as `internal_tool` alone cannot prove that.

`information_observations` now records these distinctions with event references.
Unclassified replies/forms require semantic and publicness review; they do not
automatically stop the controller as a success. That conservative limitation may
spend extra contacts after a genuine disclosure, but avoids fabricated success.
No extra private-source collection or real-channel delivery was introduced.

## Handoff and validation

No shared Event/Finding fields, SQL migrations, or storage API signatures changed.
The additive journal fields are preserved inside the existing source/event JSON
handoff. Shaurya owns orchestration, Adrian/Cem own source/storage review, and Gary
can consume `dialogue`, `sent_at`, `story_time_end`, `grounding`, `evidence_context`,
and `information_observations` from the reporting projection. This document records
the handoff; no teammate messages were sent.

Offline checks cover channel coverage and limits, call accounting and hangup,
objective stopping, exact-key recovery after lost start/turn/end responses,
Monday-to-Friday timing, attribution failures, grounding rejection, evidence
preservation and repeated-eval protection. Real model quality and live simulator
effectiveness still need a practice run. No scoring sessions were consumed here.

Final verification: **289 tests passed, plus 119 subtests**, with no skips, against
a newly created disposable Postgres 16 instance. The test run did not use the
project database. This includes a real database round trip of the full call,
virtual timestamps and evidence ledger. `git diff --check` also passed.

### Follow-up: organizer role wording and terminal progress

A user practice run exposed a missing role synonym: the API describes Julius as
“business and go-to-market,” which did not match the sales lane and fell through
to courier. The matcher now recognizes go-to-market (including spaced/dash
variants) and GTM. A role-only choice is explicitly labeled `organizer_role_baseline`,
not public research. No biography or hidden topic is inferred. A read-only live
practice preflight confirmed `LANE_1_ENTERPRISE_RFP`; it opened no session and
sent no contacts. The user's existing practice journal was left unchanged.

CLI output now includes organizer role, actual drafting temperature, session/journal
identity and progress for drafting, review, messages and call utterances. Ctrl+C
preserves interrupted intent for recovery. Offline regression validation after this
fix: **263 passed, 33 database tests skipped, 119 subtests passed**. Database/schema
code did not change; the complete database validation above precedes this fix.

### Follow-up: event attribution, draft repair and complete transcript export

The backend now rejects explicit event references to another message or conversation
before recording local objective evidence. Missing references remain permitted for
event types whose documented shape does not guarantee them. Malformed event containers
and contact identities fail without discarding the saved pending request.

Draft review returns fixed issue codes. One regeneration receives those codes, and a
successful draft retains its rejected-attempt record. Failed reviews retain safe codes
in the journal without logging provider response bodies or inserting arbitrary reviewer
instructions into the next prompt. Locked sender roles are explicit, including NDA
sender changes. Email drafts have a 4,096-token output budget; short messages use 1,024
and the review uses 512, reducing truncation risk for HTML and unnecessary review output.

`python -m src.transcript_export JOURNAL --output REPORT.html` produces a complete local
read-only view. It preserves all message replies, all call utterances, actual/simulated
clocks, and evidence details. A pending call's acknowledged exchanges are shown separately
from unconfirmed delivery. Original message HTML appears as escaped source; scripts,
forms and remote resources cannot execute. No network or model calls are involved.
Existing storage interfaces and shared Event/Finding schemas remain unchanged.

These changes were transferred to the shared checkout and verified with **316 passing
tests plus 119 subtests, with no skips**, against fresh disposable Postgres 16.
Claude's ongoing practice run may still use modules loaded before this transfer; its
live results must identify the version tested rather than be attributed to this batch.

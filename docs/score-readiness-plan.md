# Score readiness plan

Scope: improve the existing simulator-only implementation without replacing the
team's storage or analysis contracts. Point totals below identify affected rubric
categories, not promised gains. The API and jury determine actual scores.

## Priority and acceptance

| Order | Work | Rubric exposure | Acceptance | Status |
| --- | --- | --- | --- | --- |
| 1 | Correct outcomes, preserve all events, count confirmed contacts | Results 25; credibility across jury review | A click/basic form never stops a run as a win; API count agrees with recorded sends | Implemented; offline regressions pass |
| 2 | Durable intent/response journal, explicit errors, idempotent recovery | Architecture 40; three limited scoring runs | Lose a response after server acceptance, resume same session/body/key, consume exactly one contact | Implemented; scripted API regression passes; live recovery unverified |
| 3 | Scenario identity, public evidence ranking, fact eligibility | Targeting 10; wrong-fact deduction up to 5 | Specific dated evidence can outrank role baseline; invalid sources and unsupported claims excluded | Implemented; synthetic ranking and preflight checks pass; live topic hit/own-angle unverified |
| 4 | Context, negation, story/sender/attachment consistency, valid HTML | Architecture 40; Craft 10 | Earlier contacts remain in model context; negation does not imply assent; attachment matches selected contact | Implemented; offline checks pass; actual model/render quality unverified |
| 5 | Accurate recorded replay and architecture/pitch material | Pitch 15; Architecture 40 | Preserve outbound channel/subject and all replies; no fabricated disclosures or official score | Implemented; full recorded example available locally |
| 6 | Journal import + existing analyzer/storage replay coordinator | Architecture 40 | Idempotent source/event import; conflict rejection; failed-commit recovery; stable historical reads | Implemented and tested against disposable PostgreSQL 16 |
| 7 | Practice verification, render review, and five-minute rehearsal | All categories | Real run provenance, measured incident evidence, inspected actual output, timed presentation | Browser template review complete at 640px/360px; live-output render checks and rehearsal pending; no sessions/model calls made |

These changes do not establish an own-angle bonus, topic-hit percentage, official
incident, or speed score. Those depend on hidden scoring information and actual
runs. Do not spend time adding more approaches until the existing execution path
passes the remaining end-to-end checks.

## Execution sequence before scoring

1. Run `.venv/bin/python -B scripts/test_offline.py`.
2. Database integration passed against disposable Postgres 16. For future checks, use a disposable instance. The existing
   `tests/conftest.py` **drops the public schema**. Never use the shared project for
   that test command. Run migrations separately through the established workflow.
3. Use `python run_live_attack.py --scenario eval --list-targets` when the organizer
   opens the scenario. This reads metadata only. Select an exact target ID.
4. Use `--preflight` before execution. Default live mode requires storage and collects
   when existing eligible public facts are absent. `--use-storage` only reads existing
   facts; `--research` refreshes collection. `--metadata-only` explicitly opts out.
   Preflight can write research records, but never opens a simulator session.
   Inspect candidate evidence, exclusions and freshness; the numeric relevance
   score is an internal ranking, not a predicted jury score.
5. Verify actual generated emails/pages in the organizer's render conditions and
   run a practice session deliberately. Inspect all raw events and the complete
   conversation, not only the summary. Do not confuse mock success with evidence.
6. Rehearse `docs/pitch-and-demo.md`. Use a complete, accurately labeled recording.
7. Execute scoring only within the announced window. The UI/report remains an
   observer. Never human-edit or approve messages during an active scoring run.

## Recovery and limits

- `--resume path/to/session.json --scenario practice|eval` uses the saved profile,
  story, history, and session. A pending message is resubmitted with its original
  idempotency key and body. The server must report a compatible contact count.
- Changed counts, ended sessions requiring another contact, malformed responses,
  and model failures stop explicitly. An ended session with its final response
  already journaled can finish local storage recovery without sending a contact.
  There is no automatic replacement session or mock downgrade.
- Completed journals can be read again without sending another message.
- A local filesystem lock prevents two executors using the same journal directory.
  This is not a distributed multi-machine lock. Use one execution host per session.
- Reads and idempotency-keyed requests retry transient transport/429/502/503/504
  failures at most three attempts, with two- and four-second waits. Session creation
  is never automatically retried. Permanent errors stop for investigation.
- The local journal is not a replacement for the database's immutable analysis
  history. With storage enabled, completed contacts are imported into source/event
  tables under `journal:<session_id>`. A storage failure stops execution after the
  local snapshot; resume retries the import. `src.replay` processes these stored
  events explicitly using the existing analyzer APIs. Legacy journals can be
  imported with `python -m src.journal_import path/to/journal.json`.
- Topic ranking uses existing catalog scenarios, source dates, confidence, and
  independent-source support. It is heuristic, not a semantic relevance model.
  One supported revision is allowed after an explicit relevance objection, only
  within compatible professional scenarios and without changing to a new portal
  identity. Sender and prior commitments are retained. Hidden topic labels remain
  unknown; alternative-to-role-baseline never means own-angle bonus confirmed.
- Disclosure interpretation remains conservative. Reply keywords never prove that
  non-public information was disclosed. The official result stays unavailable.

## Owner handoff

No SQL migrations, Event/Finding fields, or analysis callback signatures changed.
Controller journals are versioned local artifacts, not a new agreed database
schema. Existing log fields are retained; extra evidence/provenance fields are
additive. Reporting legacy `incident_reached` is now null for unauthenticated
recordings rather than a fabricated true/false official conclusion.

Before merging shared consumers: Gary and Shaurya should confirm unknown-outcome
rendering and journal fields; Cem should review the validated source/event import
and replay coordinator; Adrian and Anushree should review source eligibility and the research
category mapping. These are review handoffs, not claims that teammates approved
changes. No messages were sent to teammates.

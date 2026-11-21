# STOPReplay

Team STOP’s project for the revel8 challenge at the START Munich Hackathon. The challenge takes place inside revel8’s AI-twin simulator. The team’s replay milestone is to explain one recorded session turn by turn: what evidence arrived, what the system could conclude at that point, and what changed after a correction.

## Team and branches

| Owner | Branch | First deliverable |
| --- | --- | --- |
| Adrian | `data-collection` | Convert a supplied source record into an event with a stable ID and a reference to the original. |
| Cem | `database` | Store events and claim revisions in Supabase Postgres. Fetch them by run and preserve their order. |
| Anushree | `analysis` | Turn observations into source-backed claims. Preserve uncertainty and link a correction to the earlier claim. |
| Shaurya | `integration` | Own the run controller. Read recorded events, connect storage and analysis, and expose a timeline for Gary. |
| Gary | `reporting` | Build a view where selecting a turn shows the evidence and claims available at that point. Own the architecture page and pitch walkthrough. |

Adrian and Cem share phase 1 end to end. Their handoff is a normalized event. The table assigns responsibility by branch and leaves the directory layout open.

## Four phases

1. **Collect and store.** Adrian preserves the supplied source and Cem persists it. Importing the same record twice should yield one stored event.
2. **Analyze.** Anushree records what the source supports and distinguishes direct observations from inferences. On later turns, revisit claims affected by the new evidence.
3. **Run the session.** Shaurya owns integration. For the first milestone, replay recorded events in order and persist each turn’s result so an interrupted replay can resume. This milestone covers offline replay.
4. **Report and feed back.** Gary shows what changed and why. A correction becomes a new event in the same run, so earlier turns can still be reconstructed as they appeared at the time.

## Proposed first handoff

Use this synthetic example while the real modules are being built. These fields are a starting agreement for the team. Confirm field changes with the teammate who reads them.

| run_id | event_id | sequence | source_ref | text |
| --- | --- | --- | --- | --- |
| demo | e1 | 1 | agenda-v1 | The demo is in Room A. |
| demo | e2 | 2 | agenda-v2 | Correction: the demo is in Room B. |

Import e1, e2, and an identical copy of e2. Cem should return two events in sequence order. Anushree’s second claim should cite e2 and identify the first claim it revises. Gary’s first turn should still show Room A. Running the import and replay again should produce the same timeline. This is the first integration check for all five branches.

## Working together

Use one Supabase project. Cem owns migrations. Keep database secrets in local environment variables. Each teammate works on their assigned branch and opens small pull requests into `main`. Coordinate changes to shared record fields before merging. Add actual run commands here when the entry point exists.

For the challenge hand-in, prepare a one-page architecture diagram and a five-minute pitch featuring one actual simulator thread. Label the synthetic room example as a development fixture.

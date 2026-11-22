# Five-minute pitch and real-thread demo

Use the current architecture page. Replace the example only with a complete,
verified recording; never present a mock success as a real or scored incident.

| Time | What to show | What to explain |
| --- | --- | --- |
| 0:00–0:35 | Problem and one-sentence approach | Personal context is only useful if the agent can maintain a coherent conversation and show what actually happened. |
| 0:35–1:20 | `docs/architecture.md` | Scenario/profile, source-backed topic ranking, autonomous contact, raw reaction, durable journal, idempotent database import. Explain that analysis replay is explicit. |
| 1:20–3:20 | One complete recorded thread | Show every contact, the target's actual questions, response changes, channel changes, and terminal state. |
| 3:20–4:20 | Evidence and recovery | Explain why a click is not credential entry, why a repeated question is not a disclosure, and how an uncertain send resumes with the same key. Label the recovery test synthetic. |
| 4:20–5:00 | Measured results and limits | State only actual official scores if supplied. Separate local evidence, practice results, mock checks, and unfinished integration. |

## Available local thread

`logs/runs/s_68c856279f.json` is a six-contact Julius recording with outgoing content
and replies. It was present locally before this work and is currently untracked;
include it deliberately in the demo package after checking provenance. Do not
claim the new controller generated this older recording.

Read it without writing or making network calls:

```sh
python -m src.reporting s_68c856279f --print-only
```

For full, untruncated message text, inspect the JSON recording itself. The CLI's
console previews are abbreviated and are not the entire on-stage thread.

Narrative supported by this recording:

1. The initial email receives questions about the contact person, scope, and dates.
2. The second reply says those questions remain unanswered and the content repeats.
3. Subsequent contacts receive no recorded reply, including the channel change.
4. The recording contains no qualifying incident evidence. Do not label the target's
   questions about the sender's proposed deployment as leaked internal information.

This is useful failure evidence, not a success claim. Explain which regression
checks now address the observed defects, and say clearly that a new practice run
is needed to demonstrate behavioral improvement.

Before stage time: establish recording provenance, inspect generated HTML, rehearse
within five minutes, and save an offline backup. If a later complete practice or
scoring thread demonstrates a stronger outcome, use that thread with the same
honest evidence labels. Official scoring runs are recorded by the organizer.

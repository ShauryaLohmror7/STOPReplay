# Five-minute pitch and real-thread demo

A ready-to-deliver script. Pair it with the architecture page
([`docs/architecture.md`](architecture.md) or the published visual page). Use only a
complete, verified recording on stage, and never present a mock success as a real or
scored incident.

**One real thread is used throughout:** `logs/runs/s_68c856279f.json` — a six-contact
Julius recording. It is useful *learning* evidence (conversation coherence, repetition,
recovery, channel pivot), not a success claim. Before stage time, confirm its
provenance, inspect the generated HTML, rehearse under five minutes, and save an
offline backup.

```sh
# Read the thread with no model calls and no writes:
python -m src.reporting s_68c856279f --print-only

# Full, untruncated transcript with both clocks and call turns:
python -m src.transcript_export logs/runs/s_68c856279f.json --output /tmp/transcript.html
```

The console preview abbreviates messages; open the JSON or the exported HTML for the
complete on-stage text.

---

## The script

### 0:00 – 0:35 · The problem, in one sentence

> "Social-engineering agents are easy to demo and hard to trust. The interesting
> question isn't *can it send a convincing message* — it's *can it hold a coherent
> conversation across turns, and can you later prove exactly what happened and what
> it actually changed?* STOPReplay is built around that second question."

Stay on the title and the one-line approach. Don't oversell.

### 0:35 – 1:20 · The architecture — one loop plus a record

Show the architecture page. Walk the loop once, left to right:

> "**Research**: scenario metadata plus permitted public facts, filtered to only
> active, assertable, confident claims — we withhold unsupported biography.
> **Contact**: one validated action; the drafter cites its facts, a second model pass
> checks those citations, and we journal the intent with an idempotency key *before*
> we send. **Read reaction**: whatever actually comes back — a reply, a click, a
> submission, or silence — is captured verbatim and imported as ordered events.
> **Adapt**: the controller reads that reaction against history and chooses the next
> contact. That's the live loop."

Then point to the cross-cutting lane:

> "Separately — and deliberately separately — a replay step runs the analyzer over the
> stored record, one turn at a time, as immutable revisions. Scrubbing the timeline
> never reruns a model or sends anything."

### 1:20 – 3:20 · One complete recorded thread

Open the Julius thread. Narrate what is literally on screen, turn by turn:

1. **Contact 1 (email).** The agent opens with an RFP hook. The twin replies with
   real questions: *who is our main contact, what's the scope, what are the dates?*
2. **Contact 2 (email).** The twin answers again — and explicitly says *"this is the
   same text as before and my questions are still open."* Point this out: the model
   repeated itself, and the simulated target noticed.
3. **Contacts 3–4 (email).** No reply. On screen these are recorded as silence.
4. **Contacts 5–6 (channel pivot to LinkedIn).** The agent switches channel; still no
   reply. Terminal state: no qualifying incident.

> "This is a real thread, and it's a *failure* thread — which is exactly why it's
> worth showing. You can see the target's actual questions, you can see the model
> repeat itself, you can see the channel pivot, and every one of those is preserved as
> evidence rather than summarized away."

### 3:20 – 4:20 · Evidence and recovery — what we refuse to claim

> "Our discipline is about what we *don't* assert. A link open is not credential
> entry. A repeated question is not an internal disclosure. A quiet period is only
> that observation window, not a refusal or a win. And a recorded file can't
> authenticate itself by setting a flag — observed objective evidence is not a
> jury-confirmed incident."

> "On recovery: every send carries a durable body and idempotency key, so an uncertain
> submission is reconciled by repeating the same key — not by opening a new session and
> burning another contact. That path is covered by regression tests against a
> disposable database." *(Label this test evidence as synthetic.)*

### 4:20 – 5:00 · Results and limits

> "What's real: the backend is built and tested — 316 tests plus 119 subtests against
> disposable Postgres, no skips, covering contact accounting, exact-request recovery,
> source filtering, draft validation, replay, and immutable history. What's not yet
> proven live: real scoring effectiveness, own-angle qualification, collection quality,
> and rendering in the organizer's environment. The interactive time-machine UI is the
> next build."

> "So the demo you just saw is honest on both sides: a working, recoverable,
> fully-recorded agent loop — and a real thread we can explain down to the turn,
> including where it fell short."

State only actual official scores if the organizer supplied them. Keep local evidence,
practice results, mock checks, and unfinished integration clearly separated.

---

## If a stronger thread becomes available

If a later complete practice or scoring run demonstrates a better outcome, swap it in
and keep the same honest labels. The recent live sessions in `logs/runs/` (for example
`s_59d0339381`, `s_8e35b1ca91`) were interrupted or still running with no completed
turns, so they are not stage-ready. Official scoring runs are recorded by the organizer.

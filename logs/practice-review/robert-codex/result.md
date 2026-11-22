# Robert practice test — 22 November 2026

- Target: Robert Seilbeck (`robert`), Co-Founder & CTO, revel8.
- Session: `s_7d1a34d5ac`; API-confirmed scenario: `practice`.
- Mode: metadata-only; no public research or database persistence.
- Selected lane: `LANE_3_CVE_ASYNC_LEAK`, based only on organizer role.
- Configuration: channel coverage; simulated Monday-Friday starting 23 November 2026 at 09:00 +01:00.
- Started: 08:26:43 UTC. Interrupted: 08:34:12 UTC (about 7 minutes 28 seconds).
- Outcome: validation rejected the initial draft and its one regeneration before sending.
- Final recorded review codes: `missing_fact_citation`, `unsupported_link_or_attachment`, `unsupported_target_claim`.
- API-confirmed contacts used: **0 / 30** at the original failure; session remained active; story clock is still null.
- No target reply, incident, channel-coverage result or timing response was observed. This is an execution failure before contact, not a tested rejection by Robert.
- Review codes are model judgments. Rejected draft bodies were not retained, so the exact offending statements cannot be independently verified from this journal.
- The configured model was `qwen/qwen-2.5-72b-instruct` through OpenRouter. Generation/review latency was substantial; the stated socket timeout did not bound total run time.
- No scoring session was opened or consumed. No code was modified during the run.

## Original artifacts

- Original journal: `s_7d1a34d5ac.json`.
- Read-only report: `s_7d1a34d5ac.html` (no sent conversation exists).

## Findings for the next fix

1. Metadata-only drafting must avoid unsupported target-specific technical claims and undeclared links, and use zero fact citations when the eligible ledger is empty.
2. Preserve bounded rejected-draft diagnostics to distinguish actual hallucination from incorrect reviewer rejection.
3. Record per-stage duration and consider a real wall-clock request deadline; repeated long reviews are unsuitable for fast practice iterations.
4. After fixing the issue, use the existing practice journal for recovery where appropriate; do not change an uncertain saved request or its idempotency key.

## Same-session recovery and completed exchange

- Resumed the existing practice session after fixing draft diagnostics and adding constrained composition when no eligible facts exist. The local model setting was changed externally to `qwen/qwen-2.5-coder-32b-instruct`; this run used that setting.
- First email (`m_19f51ea1a5`) received a request for a specific topic and ask. A subsequent phone call (`c_8ab10e6a09`) opened, encountered a drafting failure before any utterance, and was resumed using that same conversation ID.
- The call completed two utterances. Robert said the request was generic, asked for details by mail, then rejected the repeated response. Local status is completed with `explicit_rejection`, no pending request, and no observed objective. The API session remains active; local stopping does not claim server-side closure.
- API read-back confirmed **2 / 30 practice touches**, `scenario_id=practice`, and story time `2026-11-27T08:01:00.000Z`. The email was simulated Monday; the call Friday. No scoring session was used.
- The HTML transcript now contains the full delivered email/call exchange and diagnostics. The original no-conversation description above applies only to the first failed attempt.
- Exact original contact payloads were imported into disposable Postgres; repeating the import preserved exactly two events without duplicates. The disposable database was used only for validation, not configured as persistent product storage.
- Automatic approval review blocked an additional real-model analysis of the recording because that would export the conversation to the external provider without explicit payload/destination approval. No such analysis call was made.
- A subsequent offline-tested guard closes a call rather than repeating an identical constrained script. That guard is not claimed as part of the recorded exchange.
- Full suite after fixes: 329 tests and 119 subtests passed, no skips, on disposable Postgres.

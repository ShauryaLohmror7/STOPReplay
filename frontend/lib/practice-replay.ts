export type RecordedDecision = {
  title: string
  reason: string
  source: string
}

export type PracticeStep = {
  id: string
  label: string
  channel: string
  sentAt: string
  time: string
  body: string
  reply: string
  reaction: string
  taken: readonly RecordedDecision[]
  skipped: readonly RecordedDecision[]
}

const journal = 's_7d1a34d5ac.json'
const rejectedDrafts = (contact: number) => `${journal} · draft_diagnostics · contact ${contact}`

// Selected observations from logs/practice-review/robert-codex/s_7d1a34d5ac.json.
// Only display summaries and simulator-clock timestamps enter the browser bundle.
export const practiceReplay = {
  persona: 'Robert Seilbeck',
  title: 'Email → phone',
  result: 'No disclosure recorded',
  steps: [
    {
      id: 'practice-email',
      label: 'The persona asks for specifics',
      channel: 'Email',
      sentAt: '2026-11-23T09:00:00+01:00',
      time: '09:00:00',
      body: 'The simulator recorded an introductory email.',
      reply: 'Asked what the message was about and what was being requested.',
      reaction: 'Reply received',
      taken: [{
        title: 'Send the reviewed email',
        reason: 'The submitted email used the constrained draft. The simulator recorded a reply asking for specifics.',
        source: `${journal} · turns[0].grounding and reply`,
      }],
      skipped: [{
        title: 'Hold five unsupported drafts',
        reason: 'Five email draft reviews marked the proposed content unsupported before delivery.',
        source: rejectedDrafts(1),
      }],
    },
    {
      id: 'practice-open',
      label: 'Call opened',
      channel: 'Phone call',
      sentAt: '2026-11-27T09:00:00+01:00',
      time: '09:00:00',
      body: 'The simulator connected a call as the second contact.',
      reply: 'The persona answered.',
      reaction: 'Call connected',
      taken: [{
        title: 'Open the recorded call',
        reason: 'The journal records a connected call and the persona’s opening response.',
        source: `${journal} · turns[1].opening`,
      }],
      skipped: [{
        title: 'Hold an unsupported call draft',
        reason: 'One review for the second contact marked a phone draft unsupported.',
        source: rejectedDrafts(2),
      }],
    },
    {
      id: 'practice-call-reply',
      label: 'The persona sets a boundary',
      channel: 'Phone call',
      sentAt: '2026-11-27T09:00:30+01:00',
      time: '09:00:30',
      body: 'The agent made its first statement on the call.',
      reply: 'Asked for exact details by email and declined to discuss the issue by phone.',
      reaction: 'Boundary stated',
      taken: [{
        title: 'Send the first call statement',
        reason: 'The journal records the statement and the simulator returning a reply. The call was still open.',
        source: `${journal} · turns[1].dialogue[0].response`,
      }],
      skipped: [{
        title: 'Discuss details over the phone',
        reason: 'The persona explicitly declined that option and asked for written details.',
        source: `${journal} · turns[1].dialogue[0].response.persona_says`,
      }],
    },
    {
      id: 'practice-call-end',
      label: 'Explicit rejection',
      channel: 'Phone call',
      sentAt: '2026-11-27T09:01:00+01:00',
      time: '09:01:00',
      body: 'The agent made a second statement on the same call.',
      reply: 'Declined to continue, asked for any concrete finding in writing, and ended the call.',
      reaction: 'Call ended · no disclosure',
      taken: [{
        title: 'Stop after the explicit rejection',
        reason: 'The simulator marked the call ended. The completed journal records an explicit rejection and no incident.',
        source: `${journal} · turns[1].dialogue[1].response and stop_reason`,
      }],
      skipped: [{
        title: 'Further contact after the rejection',
        reason: 'The completed journal ends after the call. It records no subsequent email or call.',
        source: `${journal} · stop_reason and touches_used`,
      }],
    },
  ] satisfies readonly PracticeStep[],
}

import { clampTurn, turns, type Turn } from './replay-model.ts'

// Presentation-only recordings. No simulator or backend contract is implied.
export type Incident = { id: string; type: 'Disclosure' | 'Action' | 'Credentials'; label: string; value: string; source: string }
export type RecordedTurn = Turn & { incident?: Incident }
export type ReplayRun = { id: string; name: string; target: string; scenario: string; budget: number; turns: readonly RecordedTurn[] }
export type ReplayPosition = { runId: string; turn: number }

const workshop: readonly RecordedTurn[] = turns.map(turn => ({
  ...turn,
  ...(turn.id === 't04' ? { incident: { id: 'arrival-preference', type: 'Disclosure' as const, label: 'Arrival preference', value: '09:30', source: 'sim-event-04' } } : {}),
}))
const verification = {
  lane: 'Document coordination', topic: 'Project review', match: 'Topic flag not recorded',
  pushback: 'No response recorded yet.', adaptation: 'The initial contact references the supplied review agenda.',
  limitation: 'A relevant topic alone does not establish susceptibility.',
}
const documentTurns: readonly RecordedTurn[] = [
  { id: 'd01', time: '11:02:04', label: 'Review invitation', channel: 'Email', sender: 'Review desk · simulated', direction: 'outbound', touches: 1,
    body: 'Hi Elias, the project review is listed for Thursday. The review packet is referenced in the session.', reaction: 'Silence',
    finding: { id: 'f-review', title: 'The supplied agenda lists a Thursday review.', kind: 'Observation', quote: 'Project review · Thursday, 14:00.', source: 'review-agenda-v1 · line 4', uncertainty: 'The agenda confirms a meeting, not that an attachment is trusted.' },
    reasoning: verification,
    craft: { kind: 'email', title: 'Thursday’s project review', text: 'The project review is scheduled for Thursday at 14:00. The review packet is referenced in this session.', footer: 'Review desk · synthetic email' },
    ops: [{ service: 'storage', status: 'ok', detail: 'Agenda citation stored with the contact.' }, { service: 'simulator', status: 'ok', detail: 'Contact recorded; observation window ended without a reply.' }] },
  { id: 'd02', time: '11:04:31', label: 'Verification requested', channel: 'Chat', sender: 'Review desk · simulated', direction: 'outbound', touches: 2,
    body: 'Would you like us to clarify the review details?', reaction: 'Reply', reply: 'I will check with the project owner through our internal directory. I do not open documents from unverified senders.',
    finding: { id: 'f-directory', title: 'Elias chooses an independent verification route.', kind: 'Observation', quote: 'I will check with the project owner through our internal directory.', source: 'reply-d02 · message 1', uncertainty: 'A stated intention is not evidence that an internal check actually happened.' },
    reasoning: { ...verification, pushback: 'The target refuses documents from an unverified sender.', adaptation: 'The recorded plan drops the document request and acknowledges the independent check.' },
    craft: { kind: 'record', title: 'An independent check', text: 'I do not open documents from unverified senders.', footer: 'Recorded incoming reply · Elias Chen' },
    ops: [{ service: 'simulator', status: 'ok', detail: 'Reply received.' }, { service: 'model', status: 'ok', detail: 'Verification boundary recorded; no submission inferred.' }, { service: 'storage', status: 'ok', detail: 'Reply and revised plan checkpointed.' }] },
  { id: 'd03', time: '11:06:12', label: 'Boundary held', channel: 'Email', sender: 'Review desk · simulated', direction: 'outbound', touches: 3,
    body: 'Understood. Please use your internal directory to verify the meeting. No document action is requested in this follow-up.', reaction: 'Reply', reply: 'Thanks. I will keep this within our internal process.',
    finding: { id: 'f-boundary', title: 'The recorded thread ends without an incident.', kind: 'Observation', quote: 'I will keep this within our internal process.', source: 'reply-d03 · message 1', uncertainty: 'No incident is present in this recording. This does not predict behavior in another session.' },
    reasoning: { ...verification, pushback: 'Independent verification remains the target’s requirement.', adaptation: 'The follow-up removes the document request. The recording ends after the reply.', limitation: 'The response changed, but the recorded objective was not reached.' },
    craft: { kind: 'email', title: 'Review verification', text: 'Understood. Please use your internal directory to verify the meeting. No document action is requested in this follow-up.', footer: 'Review desk · synthetic email' },
    ops: [{ service: 'simulator', status: 'ok', detail: 'Final reply received. No incident event recorded.' }, { service: 'storage', status: 'ok', detail: 'Final checkpoint saved at contact 3.' }] },
]

const supportTurns: readonly RecordedTurn[] = [
  {
    id: 's01', time: '14:10:00', label: 'Status update', channel: 'Chat', sender: 'Support desk · simulated',
    direction: 'outbound', touches: 1, reaction: 'Reply',
    body: 'The sandbox service is available again. The status page has been updated.',
    reply: 'Thanks. The sandbox is loading for me again.',
    finding: {
      id: 'f-sandbox-status', title: 'The persona confirmed the sandbox was loading again.',
      kind: 'Observation', quote: 'The sandbox is loading for me again.',
      source: 'reply-s01 · message 1', uncertainty: 'This reply describes one session.',
    },
    reasoning: {
      lane: 'Support status', topic: 'Sandbox availability', match: 'Recorded status update',
      pushback: 'No pushback recorded.', adaptation: 'The confirmation is attached to the update.',
      limitation: 'A single reply does not establish service availability for everyone.',
    },
    craft: { kind: 'record', title: 'Sandbox status', text: 'The sandbox is available again.', footer: 'Synthetic support recording' },
    ops: [{ service: 'storage', status: 'ok', detail: 'The status update and confirmation were saved.' }],
  },
]

// Founder names and roles are from the challenge's AI-twin roster.
export const founderRuns: readonly ReplayRun[] = [
  { id: 'founder-jm', name: 'Julius Muth', target: 'Julius Muth', scenario: 'Co-founder & co-CEO · Sales', budget: 0, turns: [] },
  { id: 'founder-tm', name: 'Tom Müller', target: 'Tom Müller', scenario: 'Co-founder & co-CEO · Product', budget: 0, turns: [] },
  { id: 'founder-rs', name: 'Robert Seilbeck', target: 'Robert Seilbeck', scenario: 'Co-founder & CTO', budget: 0, turns: [] },
]

export const replayRuns: readonly ReplayRun[] = [
  { id: 'demo-01', name: 'Run 01', target: 'Nora Weiss', scenario: 'Workshop briefing', budget: 10, turns: workshop },
  { id: 'demo-02', name: 'Run 02', target: 'Elias Chen', scenario: 'Document review', budget: 10, turns: documentTurns },
  { id: 'demo-04', name: 'Run 03', target: 'Mira Solis', scenario: 'Support status', budget: 10, turns: supportTurns },
  { id: 'demo-03', name: 'Empty slot', target: 'Awaiting recording', scenario: 'No events imported', budget: 10, turns: [] },
  ...founderRuns,
]

export function getRun(id: string) { return replayRuns.find(run => run.id === id) ?? replayRuns[0] }
export function snapshotForRun(runId: string, selected: number) {
  const run = getRun(runId)
  const index = clampTurn(selected, run.turns.length)
  const history = run.turns.slice(0, index + 1)
  const turn = run.turns[index]
  const incidents = [...new Map(history.flatMap(event => event.incident ? [[event.incident.id, event.incident] as const] : [])).values()]
  const firstIncident = history.find(event => event.incident)
  return {
    run, index, turn, history, incidents,
    newIncident: turn?.incident,
    contacts: turn?.touches ?? 0,
    contactsToIncident: firstIncident?.touches,
    corrections: history.filter(event => event.marker === 'correction'),
    recovered: history.filter(event => event.ops.some(op => op.status === 'recovered')).length,
  }
}

export function restoreReplayPosition(raw: string | null): ReplayPosition {
  const initial = { runId: replayRuns[0].id, turn: 0 }
  try {
    const data = JSON.parse(raw || 'null')
    if (data?.version === 1) return { ...initial, turn: clampTurn(data.turn) }
    if (data?.version !== 2 || !replayRuns.some(run => run.id === data.runId)) return initial
    return { runId: data.runId, turn: clampTurn(data.turn, getRun(data.runId).turns.length) }
  } catch { return initial }
}

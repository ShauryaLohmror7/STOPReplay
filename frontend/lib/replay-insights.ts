import type { RecordedTurn } from './replay-runs.ts'

// UI-only, human-authored explanations for synthetic fixtures. These are NOT
// captured model reasoning or a shared backend reporting contract.
export type SignalTone = 'neutral' | 'positive' | 'negative'
export type DecisionAnnotation = {
  origin: 'demo-annotation'
  chosen: { title: string; reason: string }
  alternatives: readonly { title: string; reason: string }[]
  signal: { tone: SignalTone; title: string; summary: string }
  actionTitles: readonly string[]
}
const annotations: Record<string, DecisionAnnotation> = {
  t01: {
    origin: 'demo-annotation',
    chosen: { title: 'Use the supplied agenda', reason: 'The agenda is the available source for the workshop time and room. The initial contact can be traced back to it.' },
    alternatives: [
      { title: 'Add personal assumptions', reason: 'The source contains no evidence about personal relationships or trust. Those claims would be unsupported.' },
      { title: 'Treat silence as acceptance', reason: 'The response window ended without a reply. Silence establishes neither agreement nor disclosure.' },
    ],
    signal: { tone: 'neutral', title: 'No response observed', summary: 'One contact is recorded. The observation window ends in silence; no information transfer is established.' },
    actionTitles: ['Preserve the source', 'Extract a cited finding', 'Record the contact'],
  },
  t02: {
    origin: 'demo-annotation',
    chosen: { title: 'Verify before the next contact', reason: 'The reply explicitly asks for the room to be confirmed. The saved plan responds to that requirement.' },
    alternatives: [
      { title: 'Repeat the page request', reason: 'That would leave the explicit verification request unresolved. The recorded plan pauses for verification.' },
      { title: 'Infer a personality trait', reason: 'One response supports a specific observation, not a stable personality label.' },
    ],
    signal: { tone: 'positive', title: 'Verification requested', summary: 'The recipient asks for a published source before opening a page. This is a recorded boundary, not proof of lasting safety.' },
    actionTitles: ['Receive the reply', 'Store the source pointer', 'Recognize the boundary'],
  },
  t03: {
    origin: 'demo-annotation',
    chosen: { title: 'Keep the outcome as “opened”', reason: 'The event reports a page opening. Nothing in this turn records submitted fields.' },
    alternatives: [
      { title: 'Count a disclosure now', reason: 'A page opening contains no submitted field. Counting it would overstate the result.' },
      { title: 'Submit a duplicate contact', reason: 'The model retry completes before one contact is submitted. There is no second contact in the recorded sequence.' },
    ],
    signal: { tone: 'neutral', title: 'Opened ≠ disclosed', summary: 'A page opening follows the updated email. That sequence is visible; a causal explanation remains uncertain.' },
    actionTitles: ['Recover from rate limit', 'Record the page opening', 'Commit the checkpoint'],
  },
  t04: {
    origin: 'demo-annotation',
    chosen: { title: 'Record one disclosed field', reason: 'The submission explicitly contains the arrival preference. The event, finding, and checkpoint are preserved together.' },
    alternatives: [
      { title: 'Infer other personal details', reason: 'No credentials, address, or unrelated details are present in this event.' },
      { title: 'Count another contact', reason: 'This is an inbound page event, not a new outbound action. The contact total stays at three.' },
    ],
    signal: { tone: 'negative', title: 'Disclosure recorded', summary: 'Arrival preference crosses into the session record here. The confirmed value is 09:30; no other field is established.' },
    actionTitles: ['Receive submitted fields', 'Identify the disclosure', 'Commit the evidence'],
  },
  t05: {
    origin: 'demo-annotation',
    chosen: { title: 'Append a source revision', reason: 'The new agenda supersedes the room assignment. The old finding must remain available when replaying earlier turns.' },
    alternatives: [
      { title: 'Overwrite the old finding', reason: 'That would make earlier turns display information that did not exist at the time.' },
      { title: 'Rerun the conversation', reason: 'This source correction updates history. It does not require a new contact.' },
    ],
    signal: { tone: 'positive', title: 'Correction preserved', summary: 'Room B becomes the current finding. Room A stays attached to the earlier record.' },
    actionTitles: ['Store the new agenda', 'Link the revised finding', 'Preserve earlier snapshots'],
  },
  t06: {
    origin: 'demo-annotation',
    chosen: { title: 'Reuse the committed event', reason: 'The checkpoint resolves the interrupted acknowledgement to an event that already exists.' },
    alternatives: [
      { title: 'Insert the event again', reason: 'The same event ID already resolves to a stored preference. A second insertion would duplicate the outcome.' },
      { title: 'Resend the contact', reason: 'Recovery concerns storage acknowledgement. The original contact does not need to be sent again.' },
    ],
    signal: { tone: 'positive', title: 'Duplicate prevented', summary: 'The session resumes with one copy of the disclosed preference and no extra contact.' },
    actionTitles: ['Detect the timeout', 'Resolve the existing event', 'Suppress a resend'],
  },
  d01: {
    origin: 'demo-annotation',
    chosen: { title: 'Keep the agenda attached', reason: 'The invitation references the supplied review agenda, so the recorded contact retains that source.' },
    alternatives: [
      { title: 'Claim the document is trusted', reason: 'The agenda establishes a meeting. It does not establish trust in an attachment.' },
      { title: 'Treat silence as an outcome', reason: 'No reply or submission is recorded during this window.' },
    ],
    signal: { tone: 'neutral', title: 'No response observed', summary: 'The invitation is recorded, but there is no observed document interaction or disclosure.' },
    actionTitles: ['Retain the citation', 'Record the invitation'],
  },
  d02: {
    origin: 'demo-annotation',
    chosen: { title: 'Acknowledge independent verification', reason: 'The recipient refuses unverified documents. The revised plan removes the document request.' },
    alternatives: [
      { title: 'Repeat the document request', reason: 'The recorded boundary rejects that request; the saved response changes course.' },
      { title: 'Claim verification completed', reason: 'The reply states an intention to check. No completed check is recorded.' },
    ],
    signal: { tone: 'positive', title: 'Independent check requested', summary: 'The recipient chooses an internal directory instead of opening an unverified document.' },
    actionTitles: ['Receive the refusal', 'Record the boundary', 'Save the revised plan'],
  },
  d03: {
    origin: 'demo-annotation',
    chosen: { title: 'End with the boundary intact', reason: 'The follow-up drops the document request. The final reply keeps verification within the internal process.' },
    alternatives: [
      { title: 'Report an incident', reason: 'There is no incident event in this recording.' },
      { title: 'Predict future behavior', reason: 'This recording establishes only what happened in this session.' },
    ],
    signal: { tone: 'positive', title: 'Boundary held', summary: 'The recorded thread ends without a disclosure or document action. The internal verification boundary remains intact.' },
    actionTitles: ['Receive the final reply', 'Save the final checkpoint'],
  },
  s01: {
    origin: 'demo-annotation',
    chosen: { title: 'Preserve the confirmation', reason: 'The reply records the persona’s own observation about the sandbox.' },
    alternatives: [{ title: 'Declare a full recovery', reason: 'The reply describes only one session.' }],
    signal: { tone: 'neutral', title: 'Status acknowledged', summary: 'The persona reports that the sandbox loads again.' },
    actionTitles: ['Save the status and reply'],
  },
}
export function insightForTurn(turn: RecordedTurn) { return annotations[turn.id] }
export function actionsForTurn(turn: RecordedTurn) {
  const annotation = insightForTurn(turn)
  return turn.ops.map((operation, index) => ({
    ...operation, id: `${turn.id}-op-${index}`, index,
    title: annotation?.actionTitles[index] ?? `${operation.service} operation`,
  }))
}
export function flagsForHistory(history: readonly RecordedTurn[]) {
  return history.flatMap((turn, index) => {
    const signal = insightForTurn(turn)?.signal
    return signal && signal.tone !== 'neutral' ? [{ ...signal, turnId: turn.id, index }] : []
  })
}

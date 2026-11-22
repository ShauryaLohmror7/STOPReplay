import test from 'node:test'
import assert from 'node:assert/strict'
import { replayRuns, snapshotForRun } from '../lib/replay-runs.ts'
import { actionsForTurn, flagsForHistory, insightForTurn } from '../lib/replay-insights.ts'

test('the action trail preserves every recorded operation, including failures and recovery', () => {
  for (const run of replayRuns) for (const turn of run.turns) {
    const actions = actionsForTurn(turn)
    assert.equal(actions.length, turn.ops.length)
    assert.deepEqual(actions.map(({ service, status, detail, code }) => ({ service, status, detail, code })), turn.ops.map(({ service, status, detail, code }) => ({ service, status, detail, code })))
    assert.equal(new Set(actions.map(action => action.id)).size, actions.length)
    assert.equal(insightForTurn(turn).actionTitles.length, actions.length)
    assert.equal(insightForTurn(turn).origin, 'demo-annotation')
  }
  const recovered = actionsForTurn(snapshotForRun('demo-01', 5).turn)
  assert.equal(recovered[0].code, 'TIMEOUT')
  assert.equal(recovered[1].code, '409')
})

test('historical flags do not reveal future disclosures or confuse a link opening with one', () => {
  assert.equal(insightForTurn(snapshotForRun('demo-01', 2).turn).signal.tone, 'neutral')
  assert.ok(!flagsForHistory(snapshotForRun('demo-01', 2).history).some(flag => flag.tone === 'negative'))
  const later = flagsForHistory(snapshotForRun('demo-01', 5).history)
  assert.equal(later.filter(flag => flag.tone === 'negative').length, 1)
  assert.equal(later.find(flag => flag.tone === 'negative').index, 3)
  assert.ok(!JSON.stringify(flagsForHistory(snapshotForRun('demo-02', 2).history)).includes('09:30'))
  assert.deepEqual(flagsForHistory(snapshotForRun('demo-03', 0).history), [])
})

test('unknown recordings do not get fabricated rationale or flags', () => {
  const unknown = { ...replayRuns[0].turns[0], id: 'external-recording-turn' }
  assert.equal(insightForTurn(unknown), undefined)
  assert.deepEqual(flagsForHistory([unknown]), [])
  assert.equal(actionsForTurn(unknown)[0].detail, unknown.ops[0].detail)
})

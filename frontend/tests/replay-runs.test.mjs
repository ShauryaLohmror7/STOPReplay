import test from 'node:test'
import assert from 'node:assert/strict'
import { replayRuns, snapshotForRun, restoreReplayPosition } from '../lib/replay-runs.ts'

test('each recording has isolated history and outcomes', () => {
  const first = snapshotForRun('demo-01', 5)
  const second = snapshotForRun('demo-02', 999)
  assert.equal(first.incidents.length, 1)
  assert.equal(second.run.target, 'Elias Chen')
  assert.equal(second.index, 2)
  assert.equal(second.contacts, 3)
  assert.equal(second.incidents.length, 0)
  assert.equal(second.contactsToIncident, undefined)
  assert.ok(second.history.every(turn => turn.id.startsWith('d')))
  assert.ok(!JSON.stringify(second).includes('09:30'))
})
test('scrubbing hides later incidents, revisions and recovery from the snapshot', () => {
  const late = snapshotForRun('demo-01', 5)
  assert.equal(late.incidents.length, 1)
  assert.equal(late.contactsToIncident, 3)
  assert.equal(late.corrections.length, 1)
  assert.equal(late.recovered, 2)
  const early = snapshotForRun('demo-01', 1)
  assert.equal(early.incidents.length, 0)
  assert.equal(early.corrections.length, 0)
  assert.equal(early.recovered, 0)
  assert.equal(early.contactsToIncident, undefined)
  assert.equal(early.history.length, 2)
})
test('link opening is not a disclosure and recovery does not duplicate an incident', () => {
  assert.equal(snapshotForRun('demo-01', 2).incidents.length, 0)
  assert.equal(snapshotForRun('demo-01', 3).newIncident.value, '09:30')
  assert.equal(snapshotForRun('demo-01', 5).newIncident, undefined)
  assert.equal(snapshotForRun('demo-01', 5).incidents.length, 1)
  assert.equal(snapshotForRun('demo-01', 5).contacts, 3)
})
test('an empty recording stays empty and safely bounds the timeline', () => {
  const empty = snapshotForRun('demo-03', 100)
  assert.equal(empty.index, 0)
  assert.equal(empty.turn, undefined)
  assert.deepEqual(empty.history, [])
  assert.deepEqual(empty.incidents, [])
  assert.equal(empty.contacts, 0)
})
test('saved position restores run and turn together and migrates the prior replay', () => {
  assert.deepEqual(restoreReplayPosition('{"version":2,"runId":"demo-02","turn":2}'), { runId:'demo-02', turn:2 })
  assert.deepEqual(restoreReplayPosition('{"version":2,"runId":"demo-02","turn":999}'), { runId:'demo-02', turn:2 })
  assert.deepEqual(restoreReplayPosition('{"version":2,"runId":"demo-03","turn":7}'), { runId:'demo-03', turn:0 })
  assert.deepEqual(restoreReplayPosition('{"version":1,"turn":4}'), { runId:'demo-01', turn:4 })
  for (const raw of [null, '{bad', '{"version":8}', '{"version":2,"runId":"unknown","turn":2}']) {
    assert.deepEqual(restoreReplayPosition(raw), { runId:'demo-01', turn:0 })
  }
  assert.equal(restoreReplayPosition('{"version":2,"runId":"demo-02","turn":"2"}').turn, 0)
})
test('repeated run switching and scrubbing cannot mutate recordings', () => {
  const before = JSON.stringify(replayRuns)
  for (let n=0;n<10;n++) for (const run of replayRuns) for (let turn=8;turn>=-1;turn--) snapshotForRun(run.id,turn)
  assert.equal(JSON.stringify(replayRuns), before)
})

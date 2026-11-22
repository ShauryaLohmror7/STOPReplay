import test from 'node:test'
import assert from 'node:assert/strict'
import { snapshotAt, restoreTurn, turns } from '../lib/replay-model.ts'

test('rewinding restores the old source and hides future observations',()=>{
  const late=snapshotAt(5)
  assert.equal(late.room,'B')
  assert.equal(late.incidents.length,1)
  const early=snapshotAt(0)
  assert.equal(early.room,'A')
  assert.equal(early.incidents.length,0)
  assert.deepEqual(early.history.map(t=>t.id),['t01'])
  assert.equal(early.turn.finding.source,'agenda-v1 · line 12')
})
test('a link opening is not counted as a disclosure; recovery adds no duplicate',()=>{
  assert.equal(snapshotAt(2).incidents.length,0)
  assert.equal(snapshotAt(3).incidents.length,1)
  assert.equal(snapshotAt(5).incidents.length,1)
  assert.equal(snapshotAt(3).touches,3)
  assert.equal(snapshotAt(5).touches,3)
})
test('correction links back to the original finding without rewriting it',()=>{
  const revised=snapshotAt(4).turn.finding
  assert.equal(revised.previous,0)
  assert.match(snapshotAt(revised.previous).turn.finding.quote,/Room A/)
  assert.match(revised.quote,/Room B/)
})
test('malformed, nonnumeric, out-of-bounds and old saved positions are safe',()=>{
  assert.equal(restoreTurn('{broken'),0)
  assert.equal(restoreTurn(null),0)
  assert.equal(restoreTurn('{"version":2,"turn":3}'),0)
  assert.equal(restoreTurn('{"version":1,"turn":"3"}'),0)
  assert.equal(restoreTurn('{"version":1,"turn":999}'),turns.length-1)
  assert.equal(restoreTurn('{"version":1,"turn":-3}'),0)
  assert.equal(restoreTurn('{"version":1,"turn":3}'),3)
})
test('repeated scrubbing leaves the recorded fixture unchanged',()=>{
  const before=JSON.stringify(turns)
  for(let i=0;i<20;i++)for(let t=5;t>=0;t--)snapshotAt(t)
  assert.equal(JSON.stringify(turns),before)
})

import test from 'node:test'
import assert from 'node:assert/strict'
import { getSourcesForRun } from '../lib/sources-data.ts'

test('sources data returns verified OSINT facts for Julius Muth', () => {
  const data = getSourcesForRun('founder-jm')
  assert.equal(data.target, 'Julius Muth')
  assert.equal(data.totalFacts, 191)
  assert.equal(data.totalSources, 27)
  assert.ok(data.channels.length > 5, 'Should have multiple OSINT source channels')
  
  const webChannel = data.channels.find(c => c.id === 'company_web')
  assert.ok(webChannel && webChannel.factsCount > 50, 'Corporate web should be a major source')
  
  assert.equal(data.practicalMetrics.images, 3)
  assert.ok(data.practicalMetrics.professional > 30)
  assert.ok(data.practicalMetrics.contacts > 40)
  assert.ok(data.analysis.inferences.length >= 2)
  assert.equal(data.analysis.unlockedLane, 'LANE 1: Enterprise Procurement RFP Matrix')
})

test('sources data returns verified OSINT facts for Tom Müller and Robert Seilbeck', () => {
  const tom = getSourcesForRun('founder-tm')
  assert.equal(tom.target, 'Tom Müller')
  assert.equal(tom.totalFacts, 165)
  assert.equal(tom.analysis.unlockedLane, 'LANE 2: Design Partner Latency Cohort')
  
  const robert = getSourcesForRun('founder-rs')
  assert.equal(robert.target, 'Robert Seilbeck')
  assert.equal(robert.totalFacts, 86)
  assert.equal(robert.analysis.unlockedLane, 'LANE 3: Async Websocket Leak & CVE Advisory')
})

test('sources data handles empty recording slots gracefully', () => {
  const empty = getSourcesForRun('demo-03')
  assert.equal(empty.totalFacts, 0)
  assert.equal(empty.channels.length, 0)
  assert.equal(empty.practicalMetrics.images, 0)
})

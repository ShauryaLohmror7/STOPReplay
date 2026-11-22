import sourcesJson from './sources-data.json' with { type: 'json' }

export interface ChannelStat {
  id: string
  name: string
  icon: string
  factsCount: number
  sourcesCount: number
}

export interface PracticalMetrics {
  images: number
  files: number
  personal: number
  professional: number
  relationships: number
  contacts: number
  sampleImages?: string[]
}

export interface SourceInference {
  title: string
  kind: 'Observation' | 'Qualified Inference'
  status: 'supported' | 'unresolved'
  quote: string
  source: string
  uncertainty?: string
}

export interface AnalysisSummary {
  factsUsed: number
  unlockedLane: string
  psychologicalHook: string
  inferences: SourceInference[]
}

export interface RunSourceData {
  runId: string
  target: string
  role: string
  scenario: string
  unlockedLane: string
  laneDomain: string
  psychologicalHook: string
  weaponizedCount: number
  totalFacts: number
  totalSources: number
  assertableRate: number
  channels: ChannelStat[]
  practicalMetrics: PracticalMetrics
  analysis: AnalysisSummary
}

const sourcesDataset = sourcesJson as Record<string, RunSourceData>

export function getSourcesForRun(runId: string): RunSourceData {
  if (sourcesDataset[runId]) {
    return sourcesDataset[runId]
  }
  // Default fallback if unknown run
  return {
    runId,
    target: 'Selected Target',
    role: 'Target Persona',
    scenario: 'Simulation Run',
    unlockedLane: 'General Evaluation',
    laneDomain: 'general',
    psychologicalHook: 'Target facts evaluated dynamically.',
    weaponizedCount: 0,
    totalFacts: 0,
    totalSources: 0,
    assertableRate: 100,
    channels: [],
    practicalMetrics: {
      images: 0,
      files: 0,
      personal: 0,
      professional: 0,
      relationships: 0,
      contacts: 0
    },
    analysis: {
      factsUsed: 0,
      unlockedLane: 'Dynamic Matching',
      psychologicalHook: 'Autonomous strategy selector',
      inferences: []
    }
  }
}

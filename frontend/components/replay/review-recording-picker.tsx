import { ChevronDown } from 'lucide-react'
import { founderRuns, replayRuns } from '@/lib/replay-runs'

const sampleRuns = replayRuns.filter(run => !founderRuns.includes(run))

export function RecordingPicker({ runId, onChoose }: { runId: string; onChoose: (runId: string) => void }) {
  return (
    <label className="conversation-run">
      <select aria-label="Recording" value={runId} onChange={event => onChoose(event.currentTarget.value)}>
        <optgroup label="Sample recordings">
          {sampleRuns.map(run => <option key={run.id} value={run.id}>{run.name}</option>)}
        </optgroup>
        <optgroup label="Founder AI twins">
          {founderRuns.map(run => <option key={run.id} value={run.id}>{run.name}</option>)}
        </optgroup>
      </select>
      <ChevronDown size={14} aria-hidden="true" />
    </label>
  )
}

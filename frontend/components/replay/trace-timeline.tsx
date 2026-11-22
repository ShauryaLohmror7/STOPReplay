import type { CSSProperties } from 'react'
import { PixelIcon } from '@/components/ui/pixel-icon'
import { insightForTurn } from '@/lib/replay-insights'
import type { ReplayRun } from '@/lib/replay-runs'

const number = (value: number) => String(value).padStart(2, '0')

export function TraceTimeline({ run, index, onChange, playing, speed, onPlay, onSpeed }: { run: ReplayRun; index: number; onChange: (index: number) => void; playing: boolean; speed: number; onPlay: () => void; onSpeed: (speed: number) => void }) {
  const turn = run.turns[index]
  const last = Math.max(1, run.turns.length - 1)
  return <section className="trace-timeline" aria-label="Turn timeline">
    <div className="trace-transport">
      <span className="trace-label">TURN {turn ? number(index+1) : '—'} / {number(run.turns.length)}</span>
      <div><button disabled={!turn || index === 0} aria-label="Previous turn" onClick={() => onChange(index - 1)}><PixelIcon name="chevronLeft"/></button>
        <button className="agent-play-control" disabled={!turn} onClick={onPlay} aria-label={playing?'Pause replay':index===run.turns.length-1?'Replay from start':'Play replay'}><PixelIcon name={playing?'pause':'play'} size={20}/></button>
        <button disabled={!turn || index === run.turns.length - 1} aria-label="Next turn" onClick={() => onChange(index + 1)}><PixelIcon name="chevronRight"/></button></div>
    </div>
    <div className="trace-ruler" style={{ '--trace-position': `${index / last * 100}%` } as CSSProperties}>
      <div className="trace-ruler-numbers" aria-hidden="true">{run.turns.map((event, i) => <span key={event.id} className={i === index ? 'is-selected' : i < index ? 'is-past' : ''} style={{ left: `${i / last * 100}%` }}>{number(i + 1)}<i className={i <= index ? event.marker ?? (insightForTurn(event)?.signal.tone === 'positive' ? 'flag-positive' : '') : undefined}/></span>)}</div>
      <div className="trace-ruler-track"><div className="trace-ruler-fill"/><div className="trace-ruler-cursor"/></div>
      <input type="range" min={0} max={last} step={1} value={index} disabled={!turn}
        aria-label="Selected replay turn" aria-valuetext={turn ? `Turn ${index + 1} of ${run.turns.length}: ${turn.label}` : 'No recorded turns'}
        onChange={event => onChange(Number(event.target.value))}/>
      <div className="trace-ruler-caption"><span>DRAG TO INSPECT</span><span className="trace-marker-key"><i/> DISCLOSURE <i className="boundary"/> BOUNDARY</span></div>
    </div>
    <div className="trace-time"><time>{turn?.time ?? '—:—:—'}</time><div className="agent-speed"><label htmlFor="replay-speed">SPEED</label><select id="replay-speed" value={speed} onChange={event=>onSpeed(Number(event.target.value))}><option value={.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option></select></div></div>
    <span className="sr-only" role="status" aria-live="polite" aria-atomic="true">{run.name}, {turn ? `turn ${index + 1}: ${turn.label}` : 'no recorded turns'}</span>
  </section>
}

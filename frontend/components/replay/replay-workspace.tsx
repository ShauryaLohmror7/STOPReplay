import { useEffect, useLayoutEffect, useRef, useState, type UIEvent } from 'react'
import { animate, useReducedMotion } from 'motion/react'
import { clampTurn } from '@/lib/replay-model'
import { insightForTurn } from '@/lib/replay-insights'
import { getRun, replayRuns, type RecordedTurn, type ReplayPosition } from '@/lib/replay-runs'
import { ConversationTimeline } from './conversation-timeline'
import { DecisionDetail, DecisionRail, type Decision } from './decision-detail'
import { RecordingPicker } from './review-recording-picker'

function LogTurn({ turn, name, index, active, upcoming }: {
  turn: RecordedTurn
  name: string
  index: number
  active: boolean
  upcoming: boolean
}) {
  const system = turn.direction === 'system'
  return (
    <li className="terminal-turn" data-active={active || undefined} data-upcoming={upcoming || undefined}
      aria-current={active ? 'step' : undefined} aria-hidden={upcoming || undefined}>
      <div className="terminal-turn-content">
        <header>
          <span>[{String(index + 1).padStart(2, '0')}]</span>
          <time dateTime={turn.time}>{turn.time}</time>
          <span>{turn.channel}</span>
          {turn.incident && <strong className="terminal-incident">{turn.incident.type}</strong>}
        </header>
        <p><strong>{system ? 'system' : 'agent'}&gt;</strong> {turn.body}</p>
        {turn.reply && <p><strong>{system ? 'event' : name}&gt;</strong> {turn.reply}</p>}
        <p className="terminal-reaction">[{turn.reaction === 'Silence' ? 'No reply recorded' : turn.reaction}]</p>
      </div>
    </li>
  )
}

export default function ReplayWorkspace({ position, onPositionChange }: {
  position: ReplayPosition
  onPositionChange: (position: ReplayPosition) => void
}) {
  const [playing, setPlaying] = useState(false)
  const [decision, setDecision] = useState<Decision | null>(null)
  const reduceMotion = useReducedMotion()
  const feed = useRef<HTMLDivElement>(null)
  const list = useRef<HTMLOListElement>(null)
  const scrollMotion = useRef<{ stop: () => void } | null>(null)
  const aligned = useRef(false)
  const scrollSelection = useRef<number | null>(null)
  const run = getRun(position.runId)
  const index = clampTurn(position.turn, run.turns.length)
  const turn = run.turns[index]
  const notes = turn && insightForTurn(turn)
  const hasNext = index < run.turns.length - 1

  function seek(value: number) {
    setPlaying(false)
    setDecision(null)
    onPositionChange({ runId: run.id, turn: clampTurn(value, run.turns.length) })
  }

  function interruptScroll() {
    scrollMotion.current?.stop()
    scrollMotion.current = null
  }

  useLayoutEffect(() => {
    const panel = feed.current
    const entry = list.current?.children[index]
    if (!panel || !(entry instanceof HTMLElement)) return
    const fromScroll = scrollSelection.current === index
    scrollSelection.current = null
    if (fromScroll) return
    const destination = entry.offsetTop

    if (!aligned.current || reduceMotion || Math.abs(panel.scrollTop - destination) < 2) {
      panel.scrollTop = destination
      aligned.current = true
      return
    }

    const controls = animate(panel.scrollTop, destination, {
      duration: 0.31,
      ease: [0.22, 0.72, 0.24, 1],
      onUpdate: value => { panel.scrollTop = value },
      onComplete: () => { scrollMotion.current = null },
    })
    scrollMotion.current = controls
    return () => {
      controls.stop()
      if (scrollMotion.current === controls) scrollMotion.current = null
    }
  }, [index, reduceMotion])

  function followScroll(event: UIEvent<HTMLDivElement>) {
    if (scrollMotion.current || !list.current) return
    const readingLine = event.currentTarget.scrollTop + 46
    let currentIndex = index
    const entries = list.current.children
    for (let next = 0; next < entries.length; next++) {
      if ((entries[next] as HTMLElement).offsetTop > readingLine) break
      currentIndex = next
    }
    if (currentIndex === index) return
    scrollSelection.current = currentIndex
    seek(currentIndex)
  }

  useEffect(() => {
    if (!playing || !hasNext) return
    const timer = window.setTimeout(() => {
      onPositionChange({ runId: run.id, turn: index + 1 })
      if (index + 1 === run.turns.length - 1) setPlaying(false)
    }, 3300)
    return () => window.clearTimeout(timer)
  }, [playing, hasNext, index, onPositionChange, run])

  useEffect(() => {
    const pauseWhenHidden = () => { if (document.hidden) setPlaying(false) }
    document.addEventListener('visibilitychange', pauseWhenHidden)
    return () => document.removeEventListener('visibilitychange', pauseWhenHidden)
  }, [])

  function openDecision(kind: Decision['kind'], option: Pick<Decision, 'title' | 'reason'>, origin: HTMLButtonElement) {
    setPlaying(false)
    setDecision({ ...option, kind, turn, origin })
  }

  return (
    <section className="terminal-console" aria-labelledby="terminal-title">
      <header className="terminal-header">
        <div>
          <h1 id="terminal-title"><span aria-hidden="true">&gt;_</span> {run.scenario}</h1>
          <p>{turn ? `Synthetic recording / ${run.target}` : 'No recording loaded'}</p>
        </div>
        <RecordingPicker runId={run.id} onChoose={runId => onPositionChange({ runId, turn: 0 })} />
      </header>
      {turn ? <>
        <div className="terminal-stage">
          <DecisionRail kind="skipped" options={notes?.alternatives ?? []} onOpen={(option, origin) => openDecision('skipped', option, origin)} />
          <section className="terminal-transcript" aria-labelledby="transcript-title">
            <h2 id="transcript-title">Conversation log</h2>
            <div ref={feed} className="terminal-feed" role="region" aria-label="Conversation transcript" tabIndex={0}
              onScroll={followScroll} onWheel={interruptScroll} onTouchStart={interruptScroll} onKeyDown={interruptScroll}>
              <ol ref={list} className="terminal-thread">
                {run.turns.map((entry, turnIndex) => <LogTurn key={entry.id} turn={entry}
                  index={turnIndex} name={run.target} active={turnIndex === index} upcoming={turnIndex > index} />)}
              </ol>
            </div>
          </section>
          <DecisionRail kind="taken" options={notes ? [notes.chosen] : []} onOpen={(option, origin) => openDecision('taken', option, origin)} />
        </div>
        <ConversationTimeline turns={run.turns} index={index} playing={playing} onSeek={seek}
          onPlayback={() => {
            if (!playing && !hasNext) seek(0)
            setPlaying(!playing)
          }} />
      </> : <div className="terminal-empty">
        <p>No conversation recorded for this selection.</p>
        <button type="button" onClick={() => onPositionChange({ runId: replayRuns[0].id, turn: 0 })}>Open sample recording</button>
      </div>}
      {decision && decision.turn.id === turn?.id && <DecisionDetail decision={decision} onDismiss={() => setDecision(null)} />}
    </section>
  )
}

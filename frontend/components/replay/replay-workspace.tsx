import { useEffect, useLayoutEffect, useRef, useState, type UIEvent } from 'react'
import { animate, useReducedMotion } from 'motion/react'
import { clampTurn } from '@/lib/replay-model'
import { practiceReplay, type PracticeStep, type RecordedDecision } from '@/lib/practice-replay'
import { ConversationTimeline } from './conversation-timeline'
import { DecisionDetail, DecisionRail, type Decision } from './decision-detail'

function LogTurn({ turn, index, active, upcoming }: {
  turn: PracticeStep
  index: number
  active: boolean
  upcoming: boolean
}) {
  return (
    <li className="terminal-turn" data-active={active || undefined} data-upcoming={upcoming || undefined}
      aria-current={active ? 'step' : undefined} aria-hidden={upcoming || undefined}>
      <div className="terminal-turn-content">
        <header>
          <span>[{String(index + 1).padStart(2, '0')}]</span>
          <time dateTime={turn.sentAt}>{turn.sentAt.slice(5, 10)} · {turn.time}</time>
          <span>{turn.channel}</span>
        </header>
        <p><strong>agent&gt;</strong> {turn.body}</p>
        <p><strong>persona&gt;</strong> {turn.reply}</p>
        <p className="terminal-reaction">[{turn.reaction}]</p>
      </div>
    </li>
  )
}

export default function ReplayWorkspace({ index, onSeek }: {
  index: number
  onSeek: (index: number) => void
}) {
  const [playing, setPlaying] = useState(false)
  const [decision, setDecision] = useState<Decision | null>(null)
  const reduceMotion = useReducedMotion()
  const feed = useRef<HTMLDivElement>(null)
  const list = useRef<HTMLOListElement>(null)
  const scrollMotion = useRef<{ stop: () => void } | null>(null)
  const aligned = useRef(false)
  const scrollSelection = useRef<number | null>(null)
  const { steps, persona, title, result } = practiceReplay
  const turn = steps[index]
  const hasNext = index < steps.length - 1

  function seek(value: number) {
    setPlaying(false)
    setDecision(null)
    onSeek(clampTurn(value, steps.length))
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
      onSeek(index + 1)
      if (index + 1 === steps.length - 1) setPlaying(false)
    }, 3300)
    return () => window.clearTimeout(timer)
  }, [playing, hasNext, index, onSeek, steps.length])

  useEffect(() => {
    const pauseWhenHidden = () => { if (document.hidden) setPlaying(false) }
    document.addEventListener('visibilitychange', pauseWhenHidden)
    return () => document.removeEventListener('visibilitychange', pauseWhenHidden)
  }, [])

  function openDecision(kind: Decision['kind'], option: RecordedDecision, origin: HTMLButtonElement) {
    setPlaying(false)
    setDecision({ ...option, kind, turn, origin })
  }

  return (
    <section className="terminal-console" aria-labelledby="terminal-title">
      <header className="terminal-header">
        <div>
          <h1 id="terminal-title"><span aria-hidden="true">&gt;_</span> {title}</h1>
          <p>Recorded practice · {persona} AI persona</p>
        </div>
        <span className="terminal-recording-state">{hasNext ? 'Read-only replay' : result}</span>
      </header>
      <div className="terminal-stage">
        <DecisionRail kind="skipped" options={turn.skipped} onOpen={(option, origin) => openDecision('skipped', option, origin)} />
        <section className="terminal-transcript" aria-labelledby="transcript-title">
          <h2 id="transcript-title">Conversation log <small>Summarized · simulation clock</small></h2>
          <div ref={feed} className="terminal-feed" role="region" aria-label="Conversation transcript" tabIndex={0}
            onScroll={followScroll} onWheel={interruptScroll} onTouchStart={interruptScroll} onKeyDown={interruptScroll}>
            <ol ref={list} className="terminal-thread">
              {steps.map((entry, turnIndex) => <LogTurn key={entry.id} turn={entry}
                index={turnIndex} active={turnIndex === index} upcoming={turnIndex > index} />)}
            </ol>
          </div>
        </section>
        <DecisionRail kind="taken" options={turn.taken} onOpen={(option, origin) => openDecision('taken', option, origin)} />
      </div>
      <ConversationTimeline turns={steps} index={index} playing={playing} onSeek={seek}
        onPlayback={() => {
          if (!playing && !hasNext) seek(0)
          setPlaying(!playing)
        }} />
      {decision && decision.turn.id === turn?.id && <DecisionDetail decision={decision} onDismiss={() => setDecision(null)} />}
    </section>
  )
}

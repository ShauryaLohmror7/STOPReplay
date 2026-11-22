import { useLayoutEffect, useRef, type MouseEvent } from 'react'
import { ArrowUpRight, X } from 'lucide-react'
import type { RecordedTurn } from '@/lib/replay-runs'
import { SourceMark } from './source-mark'

export type Decision = {
  title: string
  reason: string
  kind: 'taken' | 'skipped'
  turn: RecordedTurn
  origin: HTMLButtonElement
}

export function DecisionRail({ kind, options, onOpen }: {
  kind: Decision['kind']
  options: readonly Pick<Decision, 'title' | 'reason'>[]
  onOpen: (option: Pick<Decision, 'title' | 'reason'>, origin: HTMLButtonElement) => void
}) {
  const label = kind === 'taken' ? 'Decisions taken' : 'Decisions not taken'

  return (
    <aside className={`decision-rail decision-rail--${kind}`} aria-label={label}>
      <h2><span aria-hidden="true">{kind === 'taken' ? '+' : '−'}</span>{label}</h2>
      {options.length ? <ul>
        {options.map(option => (
          <li key={option.title}>
            <button type="button" onClick={event => onOpen(option, event.currentTarget)} aria-haspopup="dialog">
              <span><strong>{option.title}</strong><ArrowUpRight size={14} aria-hidden="true" /></span>
              <p>{option.reason}</p>
            </button>
          </li>
        ))}
      </ul> : <p className="terminal-muted">No decision notes recorded.</p>}
    </aside>
  )
}

function httpSource(source: string) {
  try {
    const url = new URL(source)
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : undefined
  } catch {
    return undefined
  }
}

export function DecisionDetail({ decision, onDismiss }: { decision: Decision; onDismiss: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const { turn, origin, kind, title, reason } = decision
  const href = httpSource(turn.finding.source)

  useLayoutEffect(() => {
    const dialogNode = dialog.current
    if (!dialogNode) return
    const box = origin.getBoundingClientRect()
    dialogNode.style.setProperty('--decision-x', `${(box.x + box.width / 2 - window.innerWidth / 2) * 0.27}px`)
    dialogNode.style.setProperty('--decision-y', `${(box.y + box.height / 2 - window.innerHeight / 2) * 0.27}px`)
    dialogNode.showModal()
    return () => {
      dialogNode.close()
      if (origin.isConnected) origin.focus({ preventScroll: true })
    }
  }, [origin])

  function dismissFromBackdrop(event: MouseEvent<HTMLDialogElement>) {
    if (event.target !== event.currentTarget) return
    const box = event.currentTarget.getBoundingClientRect()
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) onDismiss()
  }

  return (
    <dialog ref={dialog} className={`decision-detail decision-detail--${kind}`} aria-labelledby="decision-title"
      onCancel={event => { event.preventDefault(); onDismiss() }} onClick={dismissFromBackdrop}>
      <header>
        <p>{kind === 'taken' ? '+ Taken' : '− Not taken'} <span>· {turn.time}</span></p>
        <button type="button" onClick={onDismiss} aria-label="Close decision"><X size={18} /></button>
      </header>
      <h2 id="decision-title">{title}</h2>
      <p className="decision-reason">{reason}</p>
      <div className="decision-source">
        <h3>Evidence at this turn</h3>
        <p>{turn.finding.title}</p>
        <blockquote>{turn.finding.quote}</blockquote>
        <div className="decision-citation">
          <SourceMark source={turn.finding.source} />
          {href ? <a href={href} target="_blank" rel="noreferrer">{turn.finding.source}</a> : <span>{turn.finding.source}</span>}
        </div>
        <p className="terminal-muted">{turn.finding.uncertainty}</p>
      </div>
      <p className="decision-disclaimer">Demo annotation · synthetic recording</p>
    </dialog>
  )
}

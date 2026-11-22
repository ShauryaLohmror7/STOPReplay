import { useLayoutEffect, useRef, type MouseEvent } from 'react'
import { ArrowUpRight, X } from 'lucide-react'
import type { PracticeStep, RecordedDecision } from '@/lib/practice-replay'
import { SourceMark } from './source-mark'

export type Decision = RecordedDecision & {
  kind: 'taken' | 'skipped'
  turn: PracticeStep
  origin: HTMLButtonElement
}

export function DecisionRail({ kind, options, onOpen }: {
  kind: Decision['kind']
  options: readonly RecordedDecision[]
  onOpen: (option: RecordedDecision, origin: HTMLButtonElement) => void
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

export function DecisionDetail({ decision, onDismiss }: { decision: Decision; onDismiss: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const { turn, origin, kind, title, reason, source } = decision

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
        <p>{turn.reaction}</p>
        <blockquote>{turn.reply}</blockquote>
        <div className="decision-citation"><SourceMark source={source} /><span>{source}</span></div>
      </div>
      <p className="decision-disclaimer">Recorded practice · evidence summary</p>
    </dialog>
  )
}

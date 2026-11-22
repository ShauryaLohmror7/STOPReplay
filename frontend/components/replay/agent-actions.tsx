import { useState } from 'react'
import { motion } from 'motion/react'
import { PixelIcon, type PixelIconName } from '@/components/ui/pixel-icon'
import { actionsForTurn, insightForTurn } from '@/lib/replay-insights'
import type { RecordedTurn } from '@/lib/replay-runs'

const icons: Record<string, PixelIconName> = { storage: 'storage', model: 'analysis', simulator: 'signal' }
const roles = { storage: 'Preserves sources and historical state.', model: 'Interprets available evidence and records a finding.', simulator: 'Records a contact or a returned simulator event.' }

export function AgentActions({ turn, animate, onConversation }: { turn: RecordedTurn; animate: boolean; onConversation: () => void }) {
  const [selected, setSelected] = useState(0)
  const actions = actionsForTurn(turn)
  const action = actions[selected]
  const annotation = insightForTurn(turn)
  return <div className="agent-actions">
    <div className="agent-action-caption"><span>RECORDED OPERATIONS</span><span>{actions.length} STEPS</span></div>
    <ol className="agent-action-map" aria-label="Agent operation sequence">
      {actions.map((item, i) => <li key={item.id}>
        <button className={selected === i ? 'is-selected' : ''} aria-pressed={selected === i} onClick={() => setSelected(i)} aria-label={`Inspect action ${i + 1}: ${item.title}`}>
          <span className="agent-action-node"><PixelIcon name={icons[item.service]} size={24}/><i className={item.status}/></span>
          <span>{item.service === 'model' ? 'ANALYZE' : item.service === 'storage' ? 'MEMORY' : 'SIMULATOR'}</span><small>{String(i + 1).padStart(2, '0')}</small>
        </button>
        {i < actions.length - 1 && <span className="agent-packet-line" aria-hidden="true"><i style={{ animationPlayState: animate ? 'running' : 'paused', animationDelay: `${i * -.6}s` }}/></span>}
      </li>)}
    </ol>
    {action ? <motion.section key={action.id} className="agent-operation-detail" initial={animate ? { opacity: 1, y: 4 } : false} animate={{ opacity: 1, y: 0 }} transition={{ duration: animate ? .18 : 0 }} aria-label="Selected operation">
      <div><span className="agent-operation-order">{String(selected + 1).padStart(2, '0')}</span><h3>{action.title}</h3><span className={`agent-operation-status ${action.status}`}>{action.status === 'ok' ? <PixelIcon name="check" size={12}/> : <PixelIcon name="flag" size={12}/>} {action.status}</span></div>
      <p>{action.detail}</p><footer><span>{roles[action.service]}</span>{action.code && <code>{action.code}</code>}</footer>
      <div className="agent-operation-controls"><button disabled={selected === 0} onClick={() => setSelected(selected - 1)}><PixelIcon name="chevronLeft" size={12}/> Previous action</button><button disabled={selected === actions.length - 1} onClick={() => setSelected(selected + 1)}>Next action <PixelIcon name="chevronRight" size={12}/></button></div>
    </motion.section> : <p className="trace-caveat">No operation trace was recorded for this turn.</p>}
    {annotation ? <section className="agent-decision" aria-label="Decision and alternatives">
      <header><PixelIcon name="network"/><h3>The decision fork</h3><span>DEMO ANNOTATION</span></header>
      <div className="agent-choice agent-choice--chosen"><span className="agent-choice-branch" aria-hidden="true"/><div><span className="agent-choice-label"><PixelIcon name="check" size={12}/> TAKEN</span><h4>{annotation.chosen.title}</h4><p>{annotation.chosen.reason}</p></div></div>
      {annotation.alternatives.map((option, i) => <details key={option.title} className="agent-choice agent-choice--alternative"><summary><span className="agent-choice-branch" aria-hidden="true"/><span><small>NOT TAKEN / {String(i + 1).padStart(2, '0')}</small>{option.title}</span><PixelIcon name="plus" size={12}/></summary><p>{option.reason}</p></details>)}
      <p className="agent-annotation-note">Illustrative alternatives and rationale, authored for this demo. Alternatives were not executed.</p>
    </section> : <p className="trace-caveat">Decision rationale and alternatives were not recorded.</p>}
    <button className="agent-open-conversation" onClick={onConversation}><PixelIcon name="message"/> See the conversation at this turn <PixelIcon name="arrowRight"/></button>
  </div>
}

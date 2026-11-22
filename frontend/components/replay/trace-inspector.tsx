import { useState } from 'react'
import { PixelIcon } from '@/components/ui/pixel-icon'
import { insightForTurn } from '@/lib/replay-insights'
import { TraceTabs } from './trace-tabs'
import { snapshotForRun, type RecordedTurn } from '@/lib/replay-runs'

const inspectionTabs = [{ id: 'analysis', label: 'Analysis' }, { id: 'evidence', label: 'Evidence' }] as const
type Snapshot = ReturnType<typeof snapshotForRun>

export function TraceInspector({ turn, snapshot, onSelect }: { turn: RecordedTurn; snapshot: Snapshot; onSelect: (index: number) => void }) {
  const [view, setView] = useState<'analysis' | 'evidence'>('analysis')
  const { incidents, contactsToIncident, index, history } = snapshot
  const annotation = insightForTurn(turn)
  return <aside className="trace-inspector" aria-label="Selected turn inspector">
    <TraceTabs label="Inspect selected turn" tabs={inspectionTabs} selected={view} onChange={setView}>
      <div className="trace-inspection-content" key={`${turn.id}-${view}`}>
        {view === 'analysis' ? <>
          <div className={`agent-signal agent-signal--${annotation?.signal.tone ?? 'neutral'}`}>
            <span className="agent-signal-symbol"><PixelIcon name={annotation?.signal.tone === 'neutral' ? 'signal' : 'flag'} size={32}/></span>
            <span className="trace-label">THIS TURN / OBSERVED</span><h3>{annotation?.signal.title ?? turn.reaction}</h3><p>{annotation?.signal.summary ?? turn.finding.uncertainty}</p>
          </div>
          {turn.incident && <section className="agent-disclosure-site" aria-label="Disclosure location">
            <div className="agent-disclosure-bridge" aria-hidden="true"><PixelIcon name="message" size={24}/><span><i/><i/><i/></span><PixelIcon name="storage" size={24}/></div>
            <span className="trace-label">WHERE INFORMATION CROSSED</span>
            <dl><div><dt>Channel</dt><dd>{turn.channel}</dd></div><div><dt>Field</dt><dd>{turn.incident.label}</dd></div><div><dt>Value</dt><dd><mark className="agent-leaked-value">{turn.incident.value}</mark></dd></div></dl>
            <button className="trace-text-button" onClick={()=>setView('evidence')}>Inspect the submitted evidence <PixelIcon name="arrowUpRight" size={12}/></button>
          </section>}
          <div className="agent-analysis-note"><span className="trace-label">CONVERSATION → OBSERVATION</span><blockquote>“{turn.finding.quote}”</blockquote><p>{turn.reasoning.adaptation}</p></div>
          <p className="trace-caveat">{turn.reasoning.limitation}</p>
          <button className="trace-text-button" onClick={()=>setView('evidence')}><PixelIcon name="search" size={12}/> Source &amp; uncertainty <PixelIcon name="arrowRight" size={12}/></button>
        </> : <>
          <div className="trace-finding-kind"><PixelIcon name="search"/><span>{turn.finding.kind}</span><code>{turn.finding.id}</code></div>
          <h3 className="trace-finding-title">{turn.finding.title}</h3>
          <blockquote className="trace-source-quote">“{turn.finding.quote}”</blockquote>
          <div className="trace-source"><span className="trace-label">CITED SOURCE</span><code>{turn.finding.source}</code></div>
          <div className="trace-uncertainty"><span className="trace-label">UNCERTAINTY</span><p>{turn.finding.uncertainty}</p></div>
          {turn.finding.previous !== undefined && <button className="trace-text-button" onClick={() => onSelect(turn.finding.previous!)}><PixelIcon name="history"/> View previous finding <PixelIcon name="arrowUpRight"/></button>}
        </>}
      </div>
    </TraceTabs>
    <section className="trace-outcome" aria-labelledby="trace-outcome-heading">
      <header><h3 id="trace-outcome-heading">Outcome</h3><span>AS OF {String(index + 1).padStart(2, '0')}</span></header>
      <div className="trace-outcome-summary"><strong>{String(incidents.length).padStart(2, '0')}</strong><div><span>recorded {incidents.length === 1 ? 'incident' : 'incidents'}</span><small>{contactsToIncident === undefined ? 'FIRST INCIDENT NOT REACHED' : `${contactsToIncident} CONTACTS TO FIRST INCIDENT`}</small></div></div>
      {incidents.length ? <ul className="trace-disclosures">{incidents.map(incident => <li key={incident.id}>
        <div><span>{incident.type}</span><small>{turn.incident?.id === incident.id ? 'NEW THIS TURN' : 'EARLIER IN RUN'}</small></div>
        <p>{incident.label}<strong>{incident.value}</strong></p><code>{incident.source}</code><button className="agent-disclosure-jump" onClick={()=>onSelect(history.findIndex(event=>event.incident?.id===incident.id))}>Jump to disclosure <PixelIcon name="arrowUpRight" size={12}/></button>
      </li>)}</ul> : <p className="trace-caveat">{turn.reaction === 'Link opened' ? 'Link opened. No disclosure recorded.' : 'No incident recorded at this point.'}</p>}
      <details className="trace-details"><summary>Scoring context <span aria-hidden="true">+</span></summary><dl>
        <div><dt>Topic-hit / own angle</dt><dd>Not provided</dd></div><div><dt>Mail &amp; page craft</dt><dd>Not rated</dd></div><div><dt>Official score</dt><dd>Unavailable</dd></div>
      </dl><p>Demo incidents are fixture labels, not jury-confirmed results.</p></details>
    </section>
  </aside>
}

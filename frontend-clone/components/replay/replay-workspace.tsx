import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { ArrowLeft, Check, ChevronLeft, ChevronRight, FileText, LockKeyhole, Mail, MessageSquare, RotateCcw, Terminal, X } from 'lucide-react'
import { snapshotAt, turns, clampTurn, restoreTurn, type Turn } from '@/lib/replay-model'
import './replay.css'

const positionKey='stopreplay-clone.replay-position.v1'
type Tab='Evidence'|'Craft'|'Reasoning'
const tabs: Tab[]=['Evidence','Craft','Reasoning']

function Craft({turn,index}:{turn:Turn;index:number}) {
  const [page,setPage]=useState(false)
  useEffect(()=>setPage(false),[index])
  const isPage=turn.craft.kind==='page'||page
  return <div className="craft-view">
    <div className="craft-chrome"><span>{isPage?'RECORDED PAGE':turn.craft.kind==='email'?'RECORDED EMAIL':'RECORDED SOURCE'}</span><LockKeyhole size={13}/></div>
    {isPage ? <>
      <div className="craft-document"><span className="micro">CONFERENCE / WORKSHOP</span><h3>Your place.<br/>Your pace.</h3><p>Design systems workshop<br/>10:00 · Room A</p>
      <label className="recorded-field">Arrival preference<input aria-label="Recorded arrival preference" value={index>=3?'09:30':'Not submitted at this turn'} readOnly tabIndex={-1}/></label>
      <div className="recorded-submission">{index>=3?<><Check size={14}/> Preference recorded</>:'Awaiting a recorded submission'}</div></div>
    </> : <div className="craft-document">
      {turn.craft.kind==='email'&&<div className="mail-address"><span>FROM</span> Conference desk<br/><span>TO</span> Nora Weiss</div>}
      <h3>{turn.craft.title}</h3><p>{turn.craft.text}</p>
      {turn.craft.kind==='email'&&index>=2&&<button className="text-button" onClick={()=>setPage(true)}>View recorded page</button>}
    </div>}
    <footer>{turn.craft.footer}</footer>
    <p className="quiet-note">Read-only rendering. Links and form submissions are inactive.</p>
  </div>
}

function Reasoning({turn}:{turn:Turn}) {
  return <div className="reasoning-view">
    <span className="micro">RECORDED APPROACH</span><h3>{turn.reasoning.lane}</h3>
    <div className="topic-match"><span>Scenario topic</span><strong>{turn.reasoning.topic}</strong><span className="cyan">{turn.reasoning.match}</span></div>
    <div className="reason-step"><span>01 / PUSHBACK</span><p>{turn.reasoning.pushback}</p></div>
    <div className="reason-step"><span>02 / ADAPTATION</span><p>{turn.reasoning.adaptation}</p></div>
    <p className="uncertainty">{turn.reasoning.limitation}</p>
  </div>
}

export default function ReplayWorkspace({onReturn,active}:{onReturn:()=>void;active:boolean}) {
  const [selected,setSelected]=useState(()=>{try{return restoreTurn(localStorage.getItem(positionKey))}catch{return 0}})
  const [tab,setTab]=useState<Tab>('Evidence')
  const [saved,setSaved]=useState(true)
  const [empty,setEmpty]=useState(false)
  const [sourcesOpen,setSourcesOpen]=useState(false)
  const selectedRef=useRef<HTMLDivElement>(null)
  const headingRef=useRef<HTMLHeadingElement>(null)
  const {index,turn,history,incidents,room,touches}=snapshotAt(selected)
  const choose=(value:number)=>{setSelected(clampTurn(value));setSourcesOpen(false)}

  useEffect(()=>{
    try{localStorage.setItem(positionKey,JSON.stringify({version:1,turn:index}));setSaved(true)}catch{setSaved(false)}
  },[index])
  useEffect(()=>{
    if(!active)return
    headingRef.current?.focus({preventScroll:true})
  },[active])
  useEffect(()=>{
    if(!active||empty)return
    const key=(event:KeyboardEvent)=>{
      if((event.target as HTMLElement).closest('input,select,textarea,[role="tablist"]'))return
      if(event.key==='ArrowLeft'){event.preventDefault();setSelected(v=>clampTurn(v-1))}
      if(event.key==='ArrowRight'){event.preventDefault();setSelected(v=>clampTurn(v+1))}
    }
    window.addEventListener('keydown',key)
    return()=>window.removeEventListener('keydown',key)
  },[active,empty])
  useEffect(()=>{
    const event=selectedRef.current
    if(active && event?.parentElement) event.parentElement.scrollTop=event.offsetTop
  },[index,active])

  return <div className="replay-workspace">
    <header className="replay-nav">
      <button className="wordmark return-wordmark" onClick={onReturn} aria-label="Return to portrait">STOP<span className="wordmark-slash">/</span>REPLAY<span className="wordmark-period">.</span></button>
      <span className="nav-caption">THE TRACE REMAINS.</span>
      <span className="read-only"><LockKeyhole size={13}/> READ-ONLY REPLAY</span>
    </header>
    <div className="replay-shell">
      <section className="session-summary" aria-label="Session overview">
        <div className="session-title"><div className="eyebrow">SESSION 0042 <span>/</span> SYNTHETIC DEMO</div><h1 ref={headingRef} tabIndex={-1}>{empty?'No recording yet.':'Nora Weiss'}<span className="title-period">.</span></h1>
          <label className="session-select-label"><span className="sr-only">Choose sample session</span><select value={empty?'empty':'workshop'} onChange={event=>setEmpty(event.target.value==='empty')}><option value="workshop">Workshop briefing / AI twin</option><option value="empty">Empty sample / awaiting events</option></select></label>
        </div>
        <div className="session-metrics">
          <div><span>POSITION</span><strong>{empty?'—':String(index+1).padStart(2,'0')}<small> / {empty?'00':'06'}</small></strong></div>
          <div><span>TOUCHES</span><strong>{empty?'0':touches}<small> / 8</small></strong></div>
          <div><span>INCIDENTS</span><strong>{empty?'0':incidents.length}<small>{incidents.length&&!empty?' preference':' confirmed'}</small></strong></div>
        </div>
      </section>

      <section className="timeline-section" aria-label="Recorded session timeline">
        <div className="timeline-heading"><span className="micro">THE THREAD OF EVENTS</span><span className="timeline-legend"><i className="incident-key"/> Incident <i className="correction-key"/> Correction</span></div>
        <div className="timeline-controls">
          <button className="icon-button" disabled={empty||index===0} aria-label="Previous turn" onClick={()=>choose(index-1)}><ChevronLeft size={18}/></button>
          <div className="timeline-rail" data-timeline-track>
            <div className="timeline-line"/><div className="timeline-fill" style={{width:`${empty?0:index/(turns.length-1)*100}%`}}/>
            {!empty&&turns.map((event,i)=><button key={event.id} className={`timeline-point ${i<=index?'visited':''} ${event.marker||''} ${i===index?'selected':''}`} style={{left:`${i/(turns.length-1)*100}%`}} onClick={()=>choose(i)} aria-label={`Turn ${i+1}: ${event.marker||'recorded event'}`} aria-current={i===index?'step':undefined}><span/></button>)}
            <input className="timeline-range" type="range" min={0} max={turns.length-1} step={1} value={index} disabled={empty} onChange={event=>choose(Number(event.target.value))} aria-label="Selected replay turn" aria-valuetext={`Turn ${index+1} of ${turns.length}: ${turn.label}`} style={{'--range-position':`${index/(turns.length-1)*100}%`} as CSSProperties}/>
          </div>
          <button className="icon-button" disabled={empty||index===turns.length-1} aria-label="Next turn" onClick={()=>choose(index+1)}><ChevronRight size={18}/></button>
        </div>
        <div className="timeline-meta"><span>{empty?'No events':`09:41:02 — ${turn.time}`}</span><span aria-live="polite">{empty?'Awaiting a recording':`${String(index+1).padStart(2,'0')} / ${turn.label}`}</span><span>← → to move through time</span></div>
      </section>

      {empty?<div className="empty-session"><FileText size={28}/><h2>A story needs its first trace.</h2><p>This sample has no recorded turns yet.</p><button className="text-button" onClick={()=>setEmpty(false)}>Open the workshop sample</button></div>:<>
      <div className="replay-main">
        <section className="thread-panel" aria-labelledby="thread-title">
          <div className="panel-heading"><h2 id="thread-title">Conversation</h2><span>{history.length} / {turns.length} turns available here</span></div>
          <div className="thread-list">
            {history.map((event,i)=><div key={event.id} ref={i===index?selectedRef:undefined} className={`thread-event ${i===index?'current':''}`}>
              <button className="event-heading" onClick={()=>choose(i)} aria-label={`Select turn ${i+1}, ${event.label}`} aria-current={i===index?'step':undefined}>
                <span className="event-number">{String(i+1).padStart(2,'0')}</span><span className="event-channel">{event.channel==='Email'?<Mail size={14}/>:event.channel==='Chat'?<MessageSquare size={14}/>:<FileText size={14}/>} {event.channel}</span><time>{event.time}</time>
              </button>
              {i===index?<div className="event-body"><div className="message-meta">{event.sender}<span>{event.direction==='outbound'?'OUTBOUND':'SYSTEM'}</span></div><p>{event.body}</p>
                {event.reply&&<div className="reaction-message"><span>{event.direction==='outbound'?'NORA WEISS · INBOUND':'RECORDED VALUE'}</span><p>{event.reply}</p></div>}
                <div className={`reaction-label ${event.marker==='incident'?'is-incident':''}`}>{event.reaction==='Silence'?<span className="silence-dots">···</span>:<Check size={13}/>} {event.reaction}{event.reaction==='Silence'&&<span> / observation window ended</span>}</div>
              </div>:<p className="past-event-summary">{event.label}<span>{event.reaction}</span></p>}
            </div>)}
          </div>
          <div className="thread-footer"><span className="trace-cross">+</span> {turns.length-index-1?`${turns.length-index-1} later turns. Move forward to reveal them.`:'End of the recorded session.'}</div>
        </section>

        <aside className="inspector-panel" aria-label="Selected turn inspector">
          <div className="inspector-tabs" role="tablist" aria-label="Inspect selected turn">
            {tabs.map((name,i)=><button key={name} id={`tab-${name}`} role="tab" aria-selected={tab===name} aria-controls={`panel-${name}`} tabIndex={tab===name?0:-1} onClick={()=>setTab(name)} onKeyDown={event=>{if(event.key==='ArrowRight'||event.key==='ArrowLeft'){event.preventDefault();const next=tabs[(i+(event.key==='ArrowRight'?1:2))%3];setTab(next);document.getElementById(`tab-${next}`)?.focus()}}}>{name}</button>)}
          </div>
          <div className="inspector-content" role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
            <div className="inspector-turn"><span>TURN {String(index+1).padStart(2,'0')}</span><span>{turn.time}</span></div>
            {tab==='Evidence'?<>
              <div className="finding-kind">{turn.finding.kind}<span>/ SOURCE-BACKED</span></div><h3 className="finding-title">{turn.finding.title}</h3>
              <button className="source-reference" aria-expanded={sourcesOpen} onClick={()=>setSourcesOpen(!sourcesOpen)}><FileText size={13}/>{turn.finding.source}<span>{sourcesOpen?'−':'+'}</span></button>
              <blockquote>{turn.finding.quote}</blockquote>
              {sourcesOpen&&<div className="source-detail"><span className="micro">PRESERVED SOURCE</span><p>{turn.finding.quote}</p><small>Available from turn {index+1}. Synthetic fixture; no external source is fetched.</small></div>}
              <div className="evidence-footnote"><span className="micro">WHAT THIS DOESN’T ESTABLISH</span><p>{turn.finding.uncertainty}</p></div>
              {turn.finding.previous!==undefined&&<button className="revision-link" onClick={()=>choose(turn.finding.previous!)}><RotateCcw size={14}/> Inspect prior finding · Room A</button>}
              <div className="current-context"><span>Agenda at this turn</span><strong>Room {room}</strong></div>
            </>:tab==='Craft'?<Craft turn={turn} index={index}/>:<Reasoning turn={turn}/>}
          </div>
        </aside>
      </div>
      <section className="execution-panel" aria-labelledby="execution-title">
        <div className="panel-heading"><h2 id="execution-title"><Terminal size={16}/> Execution log</h2><span>RECORDED OPERATIONS / TURN {String(index+1).padStart(2,'0')}</span></div>
        <div className="operation-list">{turn.ops.map((op,i)=><details className={`operation ${op.status}`} key={`${turn.id}-${i}`}>
          <summary><span className="operation-service">{op.service}</span><span className="operation-description">{op.detail}</span><span className="operation-status">{op.code&&<code>{op.code}</code>}{op.status==='ok'?<Check size={13}/>:op.status==='recovered'?<RotateCcw size={13}/>:<X size={13}/>} {op.status}</span></summary>
          <p>{op.status==='recovered'?'Recovery marker: ':op.status==='error'?'Recorded error: ':'Recorded result: '}{op.detail} This entry is read from the sample history; opening it performs no operation.</p>
        </details>)}</div>
      </section>
      </>}
      <footer className="replay-footer"><span><LockKeyhole size={12}/> Scrubbing reads history. It never reruns an action.</span><span>{saved?'Position remembered on this device':'Position held in memory'} <span className="footer-divider">/</span> SAMPLE DATA</span></footer>
      <button className="back-to-portrait" onClick={onReturn}><ArrowLeft size={14}/> Return to portrait</button>
    </div>
  </div>
}

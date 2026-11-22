import { createRef, useRef, useState } from 'react'
import { motion, useInView, useScroll, useTransform } from 'motion/react'
import { PixelIcon, type PixelIconName } from '@/components/ui/pixel-icon'
import { AnimatedBeam } from '@/components/ui/animated-beam'

const modules = [
  {name:'Research',caption:'Find the signals',icon:'search' as PixelIconName,input:'Public sources',output:'Cited records',description:'Collect relevant public information. Keep the source attached to every observation.'},
  {name:'Store',caption:'Preserve the evidence',icon:'storage' as PixelIconName,input:'Records + events',output:'Versioned history',description:'Keep sources, events and checkpoints in order. New evidence adds to the record.'},
  {name:'Analyze',caption:'Read the context',icon:'analysis' as PixelIconName,input:'Evidence + prior findings',output:'Findings + uncertainty',description:'Separate observation from inference. Cite the evidence and revise findings when it changes.'},
  {name:'Decide',caption:'Choose the next move',icon:'network' as PixelIconName,input:'Findings + reactions',output:'Next simulated contact',description:'Choose a channel and approach. Adapt to pushback while keeping the conversation consistent.'},
  {name:'Contact',caption:'Observe the reaction',icon:'signal' as PixelIconName,input:'Channel + message',output:'Target reaction',description:'Contact the AI twin through the simulator. Replies, opens, submissions and silence return as evidence.'},
]

export function AgentArchitecture({ animate }: { animate: boolean }) {
  const graphRef=useRef<HTMLDivElement>(null)
  const notesRef=useRef<HTMLDivElement>(null)
  const graphVisible=useInView(graphRef,{amount:.5})
  const {scrollYProgress}=useScroll({target:graphRef,offset:['start end','start 36%']})
  const {scrollYProgress:notesProgress}=useScroll({target:notesRef,offset:['start end','start 48%']})
  const graphOffset=useTransform(scrollYProgress,[0,1],[26,0])
  const notesOffset=useTransform(notesProgress,[0,1],[23,0])
  const [iconRefs]=useState(()=>modules.map(()=>createRef<HTMLSpanElement>()))
  const [selected,setSelected]=useState(0)
  const [revision,setRevision]=useState(0)
  const module=modules[selected]

  return <section className="architecture-system" aria-labelledby="architecture-title">
    <header className="system-heading">
      <span className="arch-kicker">INSIDE THE SYSTEM</span>
      <h2 id="architecture-title">The logic behind <span>the trace.</span></h2>
      <p>Five modules. A shared memory. Every turn preserved.</p>
    </header>

    <motion.div className="system-flow" role="group" aria-label="Agent module architecture" style={animate?{y:graphOffset}:undefined}>
      <div className="system-stages" ref={graphRef}>
        {modules.map((item,i)=>{
          return <button key={item.name} className={`system-stage ${selected===i?'is-selected':''}`}
            aria-pressed={selected===i} aria-controls="module-readout" onClick={()=>setSelected(i)}>
            <span className="system-stage-number" aria-hidden="true"><i/>{String(i+1).padStart(2,'0')}</span>
            <span className="system-stage-icon" ref={iconRefs[i]}><PixelIcon name={item.icon} size={32}/></span>
            <span className="system-stage-name">{item.name}</span>
            <span className="system-stage-caption">{item.caption}</span>
          </button>
        })}
        {modules.slice(1).map((item,i)=><AnimatedBeam key={item.name} className="system-stage-link"
          containerRef={graphRef} fromRef={iconRefs[i]} toRef={iconRefs[i+1]}
          active={animate&&graphVisible} singlePass glow={false} delay={i*.16} duration={.82}
          gradientStopColor="var(--site-signal)" startXOffset={26} endXOffset={-26}
          pathColor="#ffffff" pathOpacity={.16} pathWidth={.75}/>) }
      </div>
      <div className="system-return" aria-label="The target reaction returns to stored evidence">
        <svg viewBox="0 0 1000 50" preserveAspectRatio="none" aria-hidden="true">
          <path d="M900 0V24H894V30H306V24H300V0M296 5V0H304V5"/>
        </svg>
        <span><PixelIcon name="return" size={16} aria-hidden="true"/> Reaction becomes evidence</span>
      </div>
      <div id="module-readout" className="system-readout" data-module={selected} aria-live="polite" aria-atomic="true">
        <div className="system-readout-title"><span>{String(selected+1).padStart(2,'0')} /</span><strong>{module.name}</strong></div>
        <p>{module.description}</p>
        <dl><div><dt>IN</dt><dd>{module.input}</dd></div><div><dt>OUT</dt><dd>{module.output}</dd></div></dl>
      </div>
      <div className="system-memory-path" aria-label="Versioned history flows through reporting into read-only replay">
        <PixelIcon name="storage" size={16} aria-hidden="true"/><span>Versioned history</span><PixelIcon name="arrowRight" size={16} aria-hidden="true"/>
        <span>Reporting</span><PixelIcon name="arrowRight" size={16} aria-hidden="true"/><span>Read-only replay</span>
      </div>
    </motion.div>

    <motion.div className="system-notes" ref={notesRef} style={animate?{y:notesOffset}:undefined}>
      <section className="system-note" aria-labelledby="adaptation-title">
        <span className="system-note-label">01 / ADAPTATION</span>
        <h3 id="adaptation-title">A reply changes the plan.</h3>
        <p>The next move responds to what happened.</p>
        <div className="adaptation-trace" aria-label="Illustrative pushback and adaptation">
          <span>“Can you verify that?”</span><PixelIcon name="arrowRight" size={16} aria-hidden="true"/>
          <span>Check the source.<br/>Revise the approach.</span>
        </div>
      </section>
      <section className="system-note" aria-labelledby="memory-title">
        <span className="system-note-label">02 / MEMORY</span>
        <h3 id="memory-title">History keeps both versions.</h3>
        <p>A correction adds context. Earlier turns stay intact.</p>
        <div className="memory-trace" role="group" aria-label="Illustrative history revision">
          <button onClick={()=>setRevision(0)} aria-pressed={revision===0}><span>TURN 01</span><strong>Room A</strong></button>
          <span className="memory-trace-line" aria-hidden="true"/><PixelIcon name="arrowRight" size={16} aria-hidden="true"/>
          <button onClick={()=>setRevision(1)} aria-pressed={revision===1}><span>TURN 05</span><strong>Room B</strong></button>
          <p aria-live="polite">{revision===0?'The original evidence.':'The cited correction.'}</p>
        </div>
      </section>
    </motion.div>
    <p className="system-footnote">System design · Illustrative traces · Simulator-only execution</p>
  </section>
}

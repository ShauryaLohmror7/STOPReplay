import { useEffect, useRef, useState } from 'react'
import { motion, useTransform, useReducedMotion, type MotionValue } from 'motion/react'
import { PixelIcon } from '@/components/ui/pixel-icon'
import { AgentArchitecture } from './agent-architecture'
import { FlowButton } from '@/components/ui/flow-button'
import { ChannelNetwork } from './channel-network'
import { ArchitectureSignal } from '@/components/ui/scroll-signal'
import type { AppView } from '@/lib/navigation'
import './architecture.css'

export default function ArchitecturePage({active,progress,onNavigate}:{active:boolean;progress:MotionValue<number>;onNavigate:(view:AppView)=>void}) {
  const headingRef=useRef<HTMLHeadingElement>(null)
  const reduced=useReducedMotion()
  const [paused,setPaused]=useState(false)
  const animate=active&&!paused&&!reduced
  const reveal=useTransform(progress,[.48,.9],[0,1])
  const textReveal=useTransform(progress,[.88,1],[0,1])
  const contentY=useTransform(progress,[.45,1],[24,0])
  useEffect(()=>{if(active) headingRef.current?.focus({preventScroll:true})},[active])
  return <div className={`architecture-page ${animate?'':'motion-paused'}`}>
    <motion.div className="site-trace-field" aria-hidden="true" style={{opacity:reveal}}/>
    <motion.div className="architecture-controls" style={{opacity:reveal}}><button className="motion-control" onClick={()=>setPaused(!paused)} aria-pressed={paused} aria-label={paused?'Resume architecture animation':'Pause architecture animation'}>{paused?<PixelIcon name="play" size={12}/>:<PixelIcon name="pause" size={12}/>} {paused?'Resume motion':'Pause motion'}</button></motion.div>
    <div className="architecture-shell">
      <section className="channels-section channels-section--lead" aria-labelledby="channels-title">
        <header className="architecture-hero">
          <h1 id="channels-title" ref={headingRef} tabIndex={-1}><motion.span className="headline-lead" style={{opacity:reveal}}>Trust opens doors.</motion.span><motion.span className="streak-headline" data-streak-headline style={{opacity:textReveal}}>Replay the breach.</motion.span></h1>
          <motion.p className="channel-summary" style={{opacity:reveal}}>Every channel connects to one replayable conversation.</motion.p>
          <motion.button className="architecture-quick-replay" style={{opacity:reveal}} onClick={()=>onNavigate('replay')}>Enter the replay <PixelIcon name="arrowUpRight"/></motion.button>
        </header>
        <motion.div style={{opacity:reveal,y:contentY}}>
          <ChannelNetwork active={active} paused={paused}/>
          <p className="channel-scope">All channels shown are simulated through revel8. Calls are conducted in text.</p>
        </motion.div>
      </section>
      <motion.div className="architecture-content" style={{opacity:reveal,y:contentY}}>
        <ArchitectureSignal frozen={!animate} />
        <AgentArchitecture animate={animate} />
        <section className="architecture-cta" aria-label="Explore the replay">
          <span className="cta-trace" aria-hidden="true"/>
          <p>Follow the next trace.</p>
          <FlowButton text="Try it for yourself" onClick={()=>onNavigate('replay')} aria-describedby="try-note"/>
          <span id="try-note">Explore a recorded demo</span>
        </section>
        <footer className="architecture-footer"><span>STOP / REPLAY</span><span>A thousand traces. One human.</span></footer>
      </motion.div>
    </div>
  </div>
}

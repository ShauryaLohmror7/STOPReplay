import { Component, lazy, Suspense, useCallback, useState, type ReactNode } from 'react'
import { motion, useMotionValue, useTransform } from 'motion/react'
import { PortraitReveal } from '@/components/ui/portrait-reveal'
import './components/replay/replay.css'
const ReplayWorkspace=lazy(()=>import('@/components/replay/replay-workspace'))

class RecordingBoundary extends Component<{children:ReactNode},{failed:boolean}> {
  state={failed:false}
  static getDerivedStateFromError(){return{failed:true}}
  render(){return this.state.failed?<div className="replay-loading"><h1>Recording couldn’t load.</h1><p>The saved source is unchanged.</p><button className="text-button" onClick={()=>window.location.reload()}>Reload recording</button></div>:this.props.children}
}
export default function App(){
  const [entered,setEntered]=useState(()=>new URLSearchParams(window.location.search).get('view')==='replay')
  const handoff=useMotionValue(entered?1:0)
  const opacity=useTransform(handoff,[.3,1],[0,1])
  const x=useTransform(handoff,[0,1],['12vw','0vw'])
  const returnToPortrait=useCallback(()=>{setEntered(false);handoff.set(0);window.scrollTo({top:0,behavior:'instant'})},[handoff])
  const updateExit=useCallback((value:number)=>handoff.set(value),[handoff])
  return <main className={entered?'experience experience--replay':'experience'}>
    <motion.div className="workspace-layer" style={{opacity,x}} inert={!entered} aria-hidden={!entered}>
      <RecordingBoundary><Suspense fallback={<div className="replay-loading">Opening recorded history…</div>}><ReplayWorkspace active={entered} onReturn={returnToPortrait}/></Suspense></RecordingBoundary>
    </motion.div>
    {!entered&&<div className="portrait-overlay"><PortraitReveal onExitProgress={updateExit} onEntered={()=>setEntered(true)}/></div>}
  </main>
}

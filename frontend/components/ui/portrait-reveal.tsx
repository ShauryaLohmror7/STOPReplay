"use client"

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"
import { animate, motion, useMotionValue, useMotionValueEvent, useReducedMotion, useTransform } from "motion/react"
import { createPortraitScene, type PortraitScene } from "@/lib/portrait-particles"
import { cn } from "@/lib/utils"

export type PortraitRevealProps = {
  imageSrc?: string
  imageAlt?: string
  className?: string
  children?: ReactNode
  onExitProgress?: (value: number) => void
  onEntered?: () => void
}

export function PortraitReveal({
  imageSrc = "/portraits/electric-gaze.webp",
  imageAlt = "Electric Gaze: a coarse ASCII portrait with a cyan light across the eyes",
  className,
  children,
  onExitProgress,
  onEntered,
}: PortraitRevealProps) {
  const sectionRef = useRef<HTMLElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const sceneRef = useRef<PortraitScene | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const reducedMotion = useReducedMotion()
  const [status, setStatus] = useState<"loading" | "ready" | "static" | "error">("loading")
  const [complete, setComplete] = useState(false)
  const [videoReady, setVideoReady] = useState(false)
  const assembly = useMotionValue(0)
  const departure = useMotionValue(0)
  const departingRef = useRef(false)
  const exitAnimationRef = useRef<ReturnType<typeof animate> | null>(null)
  const exitCallbacks = useRef({onExitProgress,onEntered})
  exitCallbacks.current = {onExitProgress,onEntered}
  const labelOpacity = useTransform(departure,[0,.25],[1,0])
  const labelX = useTransform(departure,[0,1],["0vw","-35vw"])
  const finalOpacity = useTransform(()=>Math.max(0,Math.min(1,(assembly.get()-.9)*10))*(1-Math.min(1,departure.get()*9)))
  const particleOpacity = useTransform(()=>departure.get()>0?1:1-Math.max(0,Math.min(1,(assembly.get()-.9)*10)))
  const animationRef = useRef<ReturnType<typeof animate> | null>(null)
  const targetRef = useRef(0)
  const showStill = Boolean(reducedMotion) || status === "static"
  useEffect(() => { sectionRef.current?.focus({preventScroll:true}) }, [])

  const reveal = useCallback((target: number) => {
    if (targetRef.current === target) return
    targetRef.current = target
    animationRef.current?.stop()
    if (reducedMotion || status === "static") assembly.set(target)
    else animationRef.current = animate(assembly, target, {
      duration: 4 * Math.abs(target - assembly.get()), ease: "linear",
    })
  }, [assembly, reducedMotion, status])

  const depart = useCallback(() => {
    if (departingRef.current || !exitCallbacks.current.onEntered) return
    departingRef.current = true
    videoRef.current?.pause()
    sceneRef.current?.prepareHeadline(document.querySelector<HTMLElement>('[data-streak-headline]'))
    exitAnimationRef.current = animate(departure,1,{
      duration: reducedMotion || status === "static" ? 0 : 2.4, ease: "linear",
      onComplete: () => exitCallbacks.current.onEntered?.(),
    })
  },[departure,reducedMotion,status])

  useEffect(() => {
    if (status !== "ready" && status !== "static") return
    let touchY = 0, wheelDistance = 0
    const gesture = (direction: number) => {
      if (departingRef.current) return
      if (direction > 0 && assembly.get() >= 1) depart()
      else if (assembly.get() < 1 || direction < 0) reveal(direction > 0 ? 1 : 0)
    }
    const wheel = (event: WheelEvent) => {
      event.preventDefault()
      const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? window.innerHeight : 1
      const delta = event.deltaY * unit
      if (delta === 0) return
      // Trackpads begin with tiny deltas. Accept the whole gesture without requiring a pause.
      if (Math.sign(delta) !== Math.sign(wheelDistance)) wheelDistance = 0
      wheelDistance += delta
      if (Math.abs(wheelDistance) >= 2) {
        gesture(wheelDistance)
        wheelDistance = 0
      }
    }
    const touchStart=(event:TouchEvent)=>{touchY=event.touches[0].clientY}
    const touchMove=(event:TouchEvent)=>{
      const delta=touchY-event.touches[0].clientY
      if(Math.abs(delta)>10){gesture(delta);touchY=event.touches[0].clientY}
    }
    const key=(event:KeyboardEvent)=>{
      if((event.target as HTMLElement).closest('button,a,input,textarea,select'))return
      if(['ArrowDown','PageDown',' ','End'].includes(event.key)){event.preventDefault();gesture(1)}
      if(['ArrowUp','PageUp','Home'].includes(event.key)){event.preventDefault();gesture(-1)}
    }
    window.addEventListener('wheel',wheel,{passive:false})
    window.addEventListener('touchstart',touchStart,{passive:true})
    window.addEventListener('touchmove',touchMove,{passive:true})
    window.addEventListener('keydown',key)
    return()=>{
      window.removeEventListener('wheel',wheel)
      window.removeEventListener('touchstart',touchStart)
      window.removeEventListener('touchmove',touchMove)
      window.removeEventListener('keydown',key)
    }
  },[reveal,depart,status,assembly])
  useEffect(()=>()=>{animationRef.current?.stop();exitAnimationRef.current?.stop()},[])
  useMotionValueEvent(departure,'change',value=>{
    sceneRef.current?.setExit(value)
    exitCallbacks.current.onExitProgress?.(value)
  })

  useMotionValueEvent(assembly, "change", (value) => {
    sceneRef.current?.setProgress(value)
    setComplete(value >= 1)
  })

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    let cancelled = false
    let scene: PortraitScene | null = null
    const image = new Image()
    image.crossOrigin = "anonymous"
    image.decoding = "async"
    setStatus("loading")
    image.onload = () => {
      if (cancelled) return
      if (reducedMotion) { setStatus("static"); return }
      try {
        scene = createPortraitScene({
          canvas, image, initialProgress: assembly.get(),
          onContextLost: () => {
            scene?.destroy()
            sceneRef.current = null
            setStatus("static")
          },
        })
        sceneRef.current = scene
        setStatus("ready")
      } catch (error) {
        console.warn("Portrait particles unavailable; using the original still.", error)
        setStatus("static")
      }
    }
    image.onerror = () => {
      if (!cancelled) {
        console.warn("Electric Gaze artwork could not be loaded.")
        setStatus("error")
      }
    }
    image.src = imageSrc
    return () => {
      cancelled = true
      image.onload = null
      image.onerror = null
      scene?.destroy()
      if (sceneRef.current === scene) sceneRef.current = null
    }
  }, [imageSrc, reducedMotion, assembly])

  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    if (complete && !reducedMotion) void video.play().catch(() => {})
    else { video.pause(); video.currentTime = 0; setVideoReady(false) }
  }, [complete, reducedMotion])

  return (
    <>
      <section ref={sectionRef} tabIndex={-1} className={cn("portrait-story", className)} aria-label="Interactive portrait introduction">
        <div className="portrait-stage">
          {complete && <motion.header className="intro-header" style={{opacity:labelOpacity,x:labelX}}>
            <span className="wordmark" aria-label="STOP Replay">
              STOP<span className="wordmark-slash">/</span>REPLAY<span className="wordmark-period">.</span>
            </span>
          </motion.header>}
          <div className="portrait-art" role="img" aria-label={imageAlt}>
            <motion.canvas ref={canvasRef} className="portrait-canvas" style={{opacity: showStill ? 0 : particleOpacity}} aria-hidden="true" />
            <motion.div className="original-art" style={{opacity: finalOpacity}}>
              <img src={imageSrc} alt="" />
              {!showStill && <video
                ref={videoRef} src="/portraits/electric-gaze.mp4" poster={imageSrc}
                style={{position:'absolute',inset:0,opacity:videoReady?1:0}}
                onTimeUpdate={event=>{if(event.currentTarget.currentTime>0)setVideoReady(true)}}
                onError={()=>setVideoReady(false)}
                loop muted playsInline preload="auto" aria-hidden="true"
              />}
            </motion.div>
          </div>
          {status==="error"&&<div className="asset-status"><p>The portrait couldn’t load.</p><button className="retry-button" onClick={()=>exitCallbacks.current.onEntered?.()}>Explore the architecture</button></div>}
          <button className="intro-gesture-surface" onClick={()=>complete?depart():reveal(1)} disabled={status==='loading'||status==='error'} aria-label={complete?'Explore the architecture':'Reveal portrait'}><span className="sr-only">{complete?'Explore the architecture':'Reveal portrait'}</span></button>
          {complete && <motion.p className="intro-tagline" style={{opacity:labelOpacity,x:labelX}}>A thousand traces. One human.</motion.p>}
        </div>
      </section>
      {children ? <div className="intro-continuation">{children}</div> : null}
    </>
  )
}

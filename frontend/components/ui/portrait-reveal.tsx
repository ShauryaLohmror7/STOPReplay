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
}

export function PortraitReveal({
  imageSrc = "/portraits/electric-gaze.webp",
  imageAlt = "Electric Gaze: a coarse ASCII portrait with a cyan light across the eyes",
  className,
  children,
}: PortraitRevealProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const sceneRef = useRef<PortraitScene | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const reducedMotion = useReducedMotion()
  const [status, setStatus] = useState<"loading" | "ready" | "static" | "error">("loading")
  const [complete, setComplete] = useState(false)
  const assembly = useMotionValue(0)
  const animationRef = useRef<ReturnType<typeof animate> | null>(null)
  const targetRef = useRef(0)
  const finalOpacity = useTransform(assembly, [0.9, 1], [0, 1])
  const particleOpacity = useTransform(assembly, [0.9, 1], [1, 0])
  const showStill = Boolean(reducedMotion) || status === "static"

  const reveal = useCallback((target: number) => {
    if (targetRef.current === target) return
    targetRef.current = target
    animationRef.current?.stop()
    if (reducedMotion || status === "static") assembly.set(target)
    else animationRef.current = animate(assembly, target, {
      duration: 4 * Math.abs(target - assembly.get()), ease: "linear",
    })
  }, [assembly, reducedMotion, status])

  useEffect(() => {
    if (status !== "ready" && status !== "static") return
    let touchY = 0
    const wheel = (event: WheelEvent) => { if (Math.abs(event.deltaY) > 4) reveal(event.deltaY > 0 ? 1 : 0) }
    const touchStart = (event: TouchEvent) => { touchY = event.touches[0].clientY }
    const touchMove = (event: TouchEvent) => {
      const delta = touchY - event.touches[0].clientY
      if (Math.abs(delta) > 12) { reveal(delta > 0 ? 1 : 0); touchY = event.touches[0].clientY }
    }
    const key = (event: KeyboardEvent) => {
      if ((event.target as HTMLElement).closest("button,a,input,textarea,select")) return
      if (["ArrowDown", "PageDown", " ", "End"].includes(event.key)) reveal(1)
      if (["ArrowUp", "PageUp", "Home"].includes(event.key)) reveal(0)
    }
    window.addEventListener("wheel", wheel, {passive:true})
    window.addEventListener("touchstart", touchStart, {passive:true})
    window.addEventListener("touchmove", touchMove, {passive:true})
    window.addEventListener("keydown", key)
    return () => {
      animationRef.current?.stop()
      window.removeEventListener("wheel", wheel)
      window.removeEventListener("touchstart", touchStart)
      window.removeEventListener("touchmove", touchMove)
      window.removeEventListener("keydown", key)
    }
  }, [reveal, status])

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
    else { video.pause(); video.currentTime = 0 }
  }, [complete, reducedMotion])

  return (
    <>
      <section className={cn("portrait-story", className)} aria-label="Interactive portrait introduction">
        <div className="portrait-stage">
          {complete && <header className="intro-header">
            <span className="wordmark" aria-label="STOP Replay">
              STOP<span className="wordmark-slash">/</span>REPLAY<span className="wordmark-period">.</span>
            </span>
          </header>}
          <div className="portrait-art" role="img" aria-label={imageAlt}>
            <motion.canvas ref={canvasRef} className="portrait-canvas" style={{opacity: showStill ? 0 : particleOpacity}} aria-hidden="true" />
            <motion.div className="original-art" style={{opacity: finalOpacity}}>
              {showStill ? <img src={imageSrc} alt="" /> : <video
                ref={videoRef} src="/portraits/electric-gaze.mp4" poster={imageSrc}
                loop muted playsInline preload="auto" aria-hidden="true"
              />}
            </motion.div>
          </div>
          {complete && <p className="intro-tagline">A thousand traces. One human.</p>}
        </div>
      </section>
      {children ? <div className="intro-continuation">{children}</div> : null}
    </>
  )
}

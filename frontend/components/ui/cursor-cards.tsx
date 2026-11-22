"use client"

import { createContext, useContext, useEffect, useMemo, useRef, type ReactNode } from 'react'
import { motion, useMotionTemplate, useMotionValue, useReducedMotion, type MotionValue } from 'motion/react'
import { cn } from '@/lib/utils'

type Pointer = { x: number; y: number; active: boolean }
const PointerContext = createContext<MotionValue<Pointer> | null>(null)

// The supplied cursor-border + interior-light treatment, using MotionValues so
// pointer movement never rerenders the conversation or its sibling panels.
export function CursorCardsContainer({ children, className, proximityRange = 400 }: { children: ReactNode; className?: string; proximityRange?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const pointer = useMotionValue<Pointer>({ x: 0, y: 0, active: false })
  const reduced = useReducedMotion()
  useEffect(() => {
    if (reduced || !window.matchMedia('(pointer: fine)').matches) return
    let frame = 0
    let pending: Pointer = { x: 0, y: 0, active: false }
    const move = (event: PointerEvent) => {
      pending = { x: event.clientX, y: event.clientY, active: event.pointerType !== 'touch' }
      if (frame) return
      frame = requestAnimationFrame(() => {
        frame = 0
        const bounds = ref.current?.getBoundingClientRect()
        if (!bounds) return
        pointer.set({ ...pending, active: pending.active && pending.x >= bounds.left - proximityRange && pending.x <= bounds.right + proximityRange && pending.y >= bounds.top - proximityRange && pending.y <= bounds.bottom + proximityRange })
      })
    }
    const clear = () => {
      cancelAnimationFrame(frame); frame = 0
      pointer.set({ x: 0, y: 0, active: false })
    }
    document.addEventListener('pointermove', move, { passive: true })
    document.addEventListener('pointerleave', clear)
    window.addEventListener('blur', clear)
    window.addEventListener('scroll', clear, { passive: true })
    return () => {
      clear()
      document.removeEventListener('pointermove', move)
      document.removeEventListener('pointerleave', clear)
      window.removeEventListener('blur', clear)
      window.removeEventListener('scroll', clear)
    }
  }, [pointer, proximityRange, reduced])
  return <PointerContext.Provider value={pointer}><div ref={ref} className={cn('cursor-cards', className)}>{children}</div></PointerContext.Provider>
}

export function CursorCard({ children, className, illuminationRadius = 260, illuminationColor = '#6bbed236', illuminationOpacity = .8, primaryHue = '#6bbed2', secondaryHue = '#28515d', borderColor = '#1c2529' }: {
  children: ReactNode; className?: string; illuminationRadius?: number; illuminationColor?: string; illuminationOpacity?: number; primaryHue?: string; secondaryHue?: string; borderColor?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const pointer = useContext(PointerContext)
  const x = useMotionValue(-1000)
  const y = useMotionValue(-1000)
  const opacity = useMotionValue(0)
  const reduced = useReducedMotion()
  const values = useMemo(() => ({ x, y, opacity }), [x, y, opacity])
  useEffect(() => {
    if (!pointer || reduced) return
    return pointer.on('change', point => {
      const bounds = ref.current?.getBoundingClientRect()
      const near = point.active && bounds && point.x >= bounds.left - 100 && point.x <= bounds.right + 100 && point.y >= bounds.top - 100 && point.y <= bounds.bottom + 100
      values.x.set(near ? Math.round((point.x - bounds.left) / 8) * 8 : -1000)
      values.y.set(near ? Math.round((point.y - bounds.top) / 8) * 8 : -1000)
      values.opacity.set(near ? illuminationOpacity : 0)
    })
  }, [pointer, reduced, illuminationOpacity, values])
  const border = useMotionTemplate`radial-gradient(${illuminationRadius}px circle at ${x}px ${y}px, ${primaryHue}, ${secondaryHue}, ${borderColor} 100%)`
  const light = useMotionTemplate`radial-gradient(${illuminationRadius}px circle at ${x}px ${y}px, ${illuminationColor}, transparent 100%)`
  return <div ref={ref} className={cn('cursor-card', className)}>
    <motion.div aria-hidden="true" className="cursor-card-border" style={{ background: border }}/>
    <div aria-hidden="true" className="cursor-card-surface"/>
    <motion.div aria-hidden="true" className="cursor-card-light" style={{ background: light, opacity }}/>
    <div aria-hidden="true" className="cursor-card-registration"><i/><i/><i/><i/></div>
    <div className="cursor-card-content">{children}</div>
  </div>
}

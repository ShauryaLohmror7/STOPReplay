import { useEffect, useRef } from 'react'
import { useReducedMotion, useScroll, type MotionValue } from 'motion/react'

const cyan = '#6bbed2'
const white = '#cdd7dc'
const clamp = (value: number) => Math.min(1, Math.max(0, value))
const ease = (value: number) => value * value * (3 - 2 * value)

function noise(seed: number) {
  const n = Math.sin(seed * 127.1 + 311.7) * 43758.5453
  return n - Math.floor(n)
}

function square(ctx: CanvasRenderingContext2D, x: number, y: number, size: number, alpha: number, color = cyan) {
  ctx.globalAlpha = clamp(alpha)
  ctx.fillStyle = color
  ctx.fillRect(Math.round(x), Math.round(y), size, size)
}

function drawRoute(ctx: CanvasRenderingContext2D, width: number, height: number, progress: number) {
  const count = width < 540 ? 40 : 65
  const head = 0.22 + progress * 0.92
  for (let branch = 0; branch < 5; branch++) {
    const destination = width * (0.12 + branch * 0.19)
    const center = width * 0.5
    const travel = head - Math.abs(branch - 2) * 0.041
    const knees = 0.35 + Math.abs(branch - 2) * 0.043
    for (let i = 0; i < count; i++) {
      const seed = branch * 121 + i
      const t = i / (count - 1)
      const fork = ease(clamp((t - knees) / 0.30))
      const spread = (noise(seed + 937) - 0.5) * (30 + width * 0.062)
      const x = center + (destination - center) * fork + spread * (1 - ease(progress))
      const driftY = (noise(seed + 157) - 0.5) * 19 * (1 - progress)
      const y = Math.min(height - 3, Math.max(2, height * (0.06 + 0.86 * t) + driftY))
      const packet = Math.max(0, 1 - Math.abs(t - travel) / 0.18)
      const alpha = 0.08 + noise(seed + 92) * 0.09 + (t <= travel ? 0.18 : 0) + packet * 0.61
      square(ctx, x, y, i % 8 === 0 ? 2 : 1, alpha, i % 7 === 0 ? white : cyan)
      if (i % 3 === 0) {
        square(ctx, x + (noise(seed + 277) - 0.5) * 19, y - 2, 1, alpha * 0.27)
      }
    }
    const lastY = Math.round(height * 0.92)
    const lastX = Math.round(destination)
    square(ctx, lastX - 3, lastY, 7, 0.25 + progress * 0.62, cyan)
    square(ctx, lastX - 12, lastY + 2, 2, progress * 0.42, white)
    square(ctx, lastX + 10, lastY + 2, 2, progress * 0.42, white)
  }
}

function drawScanner(ctx: CanvasRenderingContext2D, width: number, height: number, progress: number) {
  const head = 0.12 + 0.76 * progress
  const columns = Math.max(38, Math.floor(width / 4))
  const depth = Math.min(24, height * 0.34)
  const center = height * 0.5
  for (let i = 0; i < columns; i++) {
    const t = i / (columns - 1)
    const x = width * (0.045 + t * 0.91)
    const distance = Math.abs(t - head)
    const focus = Math.pow(Math.max(0, 1 - distance / 0.32), 2)
    const envelope = Math.sin(t * Math.PI) * (0.82 + 0.18 * Math.cos(t * 16))
    for (let lane = 0; lane < 7; lane++) {
      const n = i * 17 + lane * 31
      const wave = Math.sin(t * 12 + lane * 0.63 - progress * 6)
      const y = center + (wave * depth * 0.43 + (lane - 3) * 3) * envelope
      const scatter = (noise(n + 81) - 0.5) * (19 - 17 * focus)
      const alpha = envelope * (0.105 + 0.57 * focus) * (0.55 + 0.45 * noise(n))
      square(ctx, x + (noise(n + 18) - 0.5) * 9, y + scatter, lane % 3 === 0 ? 2 : 1, alpha, lane === 3 ? white : cyan)
    }
    if (i % 5 === 0) square(ctx, x, center + 22, 1, 0.18 + focus * 0.29, white)
  }

  const scanX = width * (0.045 + head * 0.91)
  for (let i = 0; i < 13; i++) {
    square(ctx, scanX, center - 25 + i * 4, i % 6 === 0 ? 3 : 1, i % 6 === 0 ? 0.9 : 0.44, cyan)
  }
}

export function SignalCanvas({ progress, kind, frozen = false }: {
  progress: MotionValue<number>
  kind: 'route' | 'scanner'
  frozen?: boolean
}) {
  const ref = useRef<HTMLCanvasElement>(null)
  const reduced = useReducedMotion()

  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    let frame = 0
    let width = 0
    let height = 0
    const fixed = frozen || reduced

    const paint = () => {
      frame = 0
      if (!width || !height) return
      ctx.clearRect(0, 0, width, height)
      const value = fixed ? (kind === 'route' ? 1 : 0.5) : clamp(progress.get())
      if (kind === 'route') drawRoute(ctx, width, height, value)
      else drawScanner(ctx, width, height, value)
      ctx.globalAlpha = 1
    }

    const resize = () => {
      width = canvas.clientWidth
      height = canvas.clientHeight
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = Math.round(width * dpr)
      canvas.height = Math.round(height * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      paint()
    }

    const observer = new ResizeObserver(resize)
    observer.observe(canvas)
    resize()
    const unsubscribe = fixed ? undefined : progress.on('change', () => {
      if (!frame) frame = requestAnimationFrame(paint)
    })
    return () => {
      observer.disconnect()
      unsubscribe?.()
      cancelAnimationFrame(frame)
    }
  }, [frozen, kind, progress, reduced])

  return <canvas className="scroll-signal-canvas" ref={ref} aria-hidden="true" />
}

export function ArchitectureSignal({ frozen }: { frozen: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end 32%'] })

  return (
    <div ref={ref} className="architecture-signal" aria-hidden="true">
      <SignalCanvas kind="route" progress={scrollYProgress} frozen={frozen} />
    </div>
  )
}

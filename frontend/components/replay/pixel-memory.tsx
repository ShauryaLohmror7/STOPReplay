import { useEffect, useRef } from 'react'
import type { SignalTone } from '@/lib/replay-insights'

const points: { x: number; y: number; z: number; id: number }[] = []
for (let x = -3; x <= 3; x++) for (let y = -3; y <= 3; y++) for (let z = -3; z <= 3; z++) {
  if (Math.max(Math.abs(x), Math.abs(y), Math.abs(z)) === 3) points.push({ x, y, z, id: points.length })
}
const colors = { neutral: [107, 190, 210], positive: [134, 218, 166], negative: [243, 126, 139] } as const

// A low-resolution projection of a real 3D point lattice. Geometry is decorative;
// its density is not presented as a score or a percentage of leaked information.
export function PixelMemory({ turn, tone, animate }: { turn: number; tone: SignalTone; animate: boolean }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const phase = useRef(0)
  useEffect(() => {
    const node = canvas.current
    const ctx = node?.getContext('2d')
    if (!node || !ctx) return
    let frame = 0, last = 0, visible = true
    const draw = () => {
      ctx.clearRect(0, 0, 240, 138)
      ctx.imageSmoothingEnabled = false
      const angle = .62 + phase.current * .12 + turn * .07
      const cos = Math.cos(angle), sin = Math.sin(angle)
      const projected = points.map(p => {
        const x = p.x * cos - p.z * sin, z = p.x * sin + p.z * cos
        return { ...p, px: Math.round(119 + x * 11), py: Math.round(66 + (p.y * .86 + z * .48) * 11), depth: z * .86 - p.y * .48 }
      }).sort((a, b) => a.depth - b.depth)
      ctx.fillStyle = '#233a46'
      for (let x = 38; x < 210; x += 8) for (let y = 115; y < 133; y += 8) ctx.fillRect(x, y, 1, 1)
      for (const p of projected) {
        const isEdge = [p.x, p.y, p.z].filter(v => Math.abs(v) === 3).length >= 2
        const active = (p.id + turn * 5) % 19 === 0
        const alpha = Math.max(.12, .43 + p.depth * .065) * (isEdge ? 1 : .45)
        const color = active ? colors[tone] : colors.neutral
        ctx.fillStyle = `rgba(${color.join(',')},${active ? .95 : alpha})`
        const size = active ? 3 : isEdge ? 2 : 1
        ctx.fillRect(p.px, p.py, size, size)
      }
      for (let i = 0; i < 10; i++) {
        const progress = (phase.current * .18 + i * .13) % 1
        const outbound = tone === 'negative'
        const x = outbound ? 159 + progress * 69 : 18 + progress * 59
        const y = 44 + ((i * 17) % 48)
        ctx.fillStyle = `rgba(${colors[tone].join(',')},${Math.sin(progress * Math.PI) * .75})`
        ctx.fillRect(Math.round(x), y, i % 3 === 0 ? 3 : 2, 2)
      }
    }
    const tick = (now: number) => {
      if (now - last >= 1000 / 24) { phase.current += last ? Math.min((now - last) / 1000, .1) : 0; last = now; draw() }
      if (animate && visible && !document.hidden) frame = requestAnimationFrame(tick)
    }
    const sync = () => {
      cancelAnimationFrame(frame); last = 0; draw()
      if (animate && visible && !document.hidden) frame = requestAnimationFrame(tick)
    }
    const observer = new IntersectionObserver(entries => { visible = entries[0].isIntersecting; sync() })
    observer.observe(node)
    document.addEventListener('visibilitychange', sync)
    sync()
    return () => { cancelAnimationFrame(frame); observer.disconnect(); document.removeEventListener('visibilitychange', sync) }
  }, [turn, tone, animate])
  return <figure className={`pixel-memory pixel-memory--${tone}`} aria-label={`Decorative pixel memory cube at turn ${turn + 1}`}>
    <canvas width={240} height={138} ref={canvas} aria-hidden="true"/>
    <figcaption><span>SESSION MEMORY</span><span>T{String(turn + 1).padStart(2, '0')}</span></figcaption>
  </figure>
}

"use client"

import { useId, type CSSProperties } from 'react'
import { LayoutGroup, motion, useReducedMotion } from 'motion/react'
import { PixelIcon } from '@/components/ui/pixel-icon'

type RunItem = { id: string; name: string; target: string; turnCount: number }

// Supplied floating navigation lamp, adapted from links to recorded run selection.
export function RunNavigation({ items, selected, selectedTurn, onChange }: { items: readonly RunItem[]; selected: number; selectedTurn: number; onChange: (index: number) => void }) {
  const id = useId()
  const reduced = useReducedMotion()
  return <section className="run-navigation" aria-label="Choose a recorded run">
    <LayoutGroup id={id}>
      <div className="run-tabs" role="tablist" aria-label="Recorded runs">
        {items.map((item, index) => <button key={item.id} id={`run-${item.id}`} role="tab" aria-controls="replay-recording" aria-selected={index === selected} tabIndex={index === selected ? 0 : -1}
          onClick={() => onChange(index)} onKeyDown={event => {
            let next = index
            if (event.key === 'ArrowRight') next = (index + 1) % items.length
            else if (event.key === 'ArrowLeft') next = (index + items.length - 1) % items.length
            else if (event.key === 'Home') next = 0
            else if (event.key === 'End') next = items.length - 1
            else return
            event.preventDefault(); onChange(next)
            document.getElementById(`run-${items[next].id}`)?.focus()
          }}>
          <span className="run-tab-title"><PixelIcon name="layers" size={16}/><span>{item.name}</span></span><span className="run-cells" aria-hidden="true">{item.turnCount ? Array.from({length:item.turnCount}, (_, turn) => <i key={turn} className={index === selected && turn <= selectedTurn ? "is-read" : undefined}/>) : <span>NO RECORDING</span>}</span>
          {index === selected && <motion.div layoutId="lamp" className="run-lamp" initial={false} transition={reduced ? { duration: 0 } : { type: 'spring', stiffness: 300, damping: 30 }}>
            <div className="run-lamp-line"><i/><i/><i/></div>
          </motion.div>}
        </button>)}
      </div>
    </LayoutGroup>
    <label className="run-drag-label"><span className="sr-only">Drag to choose a run</span>
      <input type="range" min={0} max={items.length - 1} step={1} value={selected} onChange={event => onChange(Number(event.target.value))}
        aria-valuetext={`${items[selected].name}, ${items[selected].target}`} style={{ '--range-position': `${selected / Math.max(1, items.length - 1) * 100}%` } as CSSProperties}/>
    </label>
    <span className="run-navigation-caption">DRAG THROUGH RECORDINGS</span>
  </section>
}

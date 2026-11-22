import { useEffect, useState, type MouseEvent } from 'react'
import { Crosshair, Terminal, Users } from 'lucide-react'
import { restoreReplayPosition, type ReplayPosition } from '@/lib/replay-runs'
import ReplayWorkspace from './replay-workspace'
import { Founders, Methods } from './replay-catalog'
import './terminal-replay.css'

const positionKey = 'stopreplay-clone.replay-position.v2'
const oldPositionKey = 'stopreplay-clone.replay-position.v1'
const sections = [
  { id: 'conversations', label: 'Terminal', icon: Terminal },
  { id: 'methods', label: 'Attack methods', icon: Crosshair },
  { id: 'founders', label: 'Founders', icon: Users },
] as const
type Section = typeof sections[number]['id']

function readSection(): Section {
  const value = new URLSearchParams(window.location.search).get('section')
  return sections.find(section => section.id === value)?.id ?? 'conversations'
}

function sectionHref(section: Section) {
  return section === 'conversations' ? '/?view=replay' : `/?view=replay&section=${section}`
}

function readPosition(): ReplayPosition {
  try {
    return restoreReplayPosition(localStorage.getItem(positionKey) ?? localStorage.getItem(oldPositionKey))
  } catch {
    return restoreReplayPosition(null)
  }
}

export default function ReviewWorkspace() {
  const [section, setSection] = useState(readSection)
  const [position, setPosition] = useState(readPosition)

  function navigate(next: Section) {
    if (next === section) return
    window.history.pushState(null, '', sectionHref(next))
    setSection(next)
    window.scrollTo({ top: 0, behavior: 'instant' })
  }

  function followLink(event: MouseEvent<HTMLAnchorElement>, next: Section) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
    event.preventDefault()
    navigate(next)
  }

  useEffect(() => {
    const onPopState = () => setSection(readSection())
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  useEffect(() => {
    try {
      localStorage.setItem(positionKey, JSON.stringify({ version: 2, ...position }))
    } catch {
      // Replay remains usable with storage disabled.
    }
  }, [position])

  return (
    <div className="terminal-workspace">
      <nav className="terminal-menu" aria-label="Replay sections">
        {sections.map(({ id, label, icon: Icon }) => (
          <a key={id} href={sectionHref(id)} onClick={event => followLink(event, id)} aria-current={section === id ? 'page' : undefined}>
            <Icon size={16} strokeWidth={1.7} aria-hidden="true" />
            {label}
          </a>
        ))}
      </nav>
      {section === 'conversations' && <ReplayWorkspace key={position.runId} position={position} onPositionChange={setPosition} />}
      {section === 'methods' && <Methods onOpen={(runId, turn) => { setPosition({ runId, turn }); navigate('conversations') }} />}
      {section === 'founders' && <Founders />}
    </div>
  )
}

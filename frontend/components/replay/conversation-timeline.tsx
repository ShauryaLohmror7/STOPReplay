import { AudioLines, Pause, Play, RotateCcw } from 'lucide-react'
import type { RecordedTurn } from '@/lib/replay-runs'

type ConversationTimelineProps = {
  turns: readonly RecordedTurn[]
  index: number
  playing: boolean
  onSeek: (index: number) => void
  onPlayback: () => void
}

const notchCount = 87

export function ConversationTimeline({ turns, index, playing, onSeek, onPlayback }: ConversationTimelineProps) {
  const turn = turns[index]
  if (!turn) return null

  const last = turns.length - 1
  const ended = index === last
  const playbackLabel = playing ? 'Pause replay' : ended ? 'Replay from the beginning' : 'Play conversation'
  const progress = last > 0 ? index / last : 0.5

  return (
    <footer className="conversation-player" aria-label="Conversation timeline">
      <div className="conversation-player-label">
        <span><AudioLines size={15} aria-hidden="true" />Turn timeline</span>
        <div><span className="conversation-clock-turn">{String(index + 1).padStart(2, '0')} / {String(turns.length).padStart(2, '0')}</span><time className="conversation-clock" dateTime={turn.time}>{turn.time}</time></div>
      </div>
      <div className="conversation-transport">
        {last > 0 && (
          <button type="button" className="conversation-play" aria-label={playbackLabel} title={playbackLabel} onClick={onPlayback}>
            {playing ? <Pause size={17} fill="currentColor" /> : ended ? <RotateCcw size={17} /> : <Play size={17} fill="currentColor" />}
          </button>
        )}
        <div className="conversation-scrubber">
          <div className="conversation-track" aria-hidden="true">
            <svg className="conversation-ruler" viewBox="0 0 860 50" preserveAspectRatio="none">
              <line x1="0" x2="860" y1="25" y2="25" />
              {Array.from({ length: notchCount }, (_, tick) => {
                const x = tick * 10
                const half = tick % 10 === 0 ? 20 : tick % 5 === 0 ? 15 : tick % 2 === 0 ? 8 : 5
                return <path key={tick} d={`M${x} ${25 - half}v${half * 2}`} className={tick / (notchCount - 1) <= progress ? 'is-past' : undefined} />
              })}
            </svg>
            {turns.map((event, marker) => (
              <span className={`conversation-marker${marker <= index && event.incident ? ' conversation-marker--incident' : ''}`} key={event.id} style={{ left: `${(last > 0 ? marker / last : 0.5) * 100}%` }} />
            ))}
            <span className="conversation-track-fill" style={{ width: `${progress * 100}%` }} />
            <span className="conversation-playhead" style={{ left: `${progress * 100}%` }}><i /><i /><i /></span>
          </div>
          <input
            type="range"
            aria-label="Conversation position"
            aria-valuetext={`${turn.time} · ${turn.label} · Turn ${index + 1} of ${turns.length}`}
            min={0}
            max={last > 0 ? last : 2}
            value={last > 0 ? index : 1}
            disabled={last === 0}
            onChange={event => onSeek(event.currentTarget.valueAsNumber)}
          />
        </div>
      </div>
    </footer>
  )
}

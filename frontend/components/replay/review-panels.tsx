import { Fragment, useState, type ReactNode } from 'react'
import { ArrowDownRight, ArrowRight, ArrowUpRight, AudioLines, Check, Database, FileText, Fingerprint, Layers3, Play, Search, ShieldCheck } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import { founderRuns, replayRuns, snapshotForRun, type ReplayRun } from '@/lib/replay-runs'
import { RecordingPicker } from './review-recording-picker'
import { SourceMark } from './source-mark'

function Reveal({ children, className }: { children: ReactNode; className?: string }) {
  const reduced = useReducedMotion()
  return (
    <motion.div
      className={className}
      initial={reduced ? false : { y: 16 }}
      whileInView={{ y: 0 }}
      viewport={{ once: true, amount: 0.12 }}
      transition={{ duration: reduced ? 0 : 0.5, ease: [0.2, 0.75, 0.3, 1] }}
    >
      {children}
    </motion.div>
  )
}

function PageHeader({ label, title, description, accessory }: {
  label: string
  title: string
  description: string
  accessory?: ReactNode
}) {
  return (
    <header className="review-heading">
      <div>
        <p className="review-kicker"><span aria-hidden="true" />{label}</p>
        <h1>{title}<span>.</span></h1>
        <p className="review-subtitle">{description}</p>
      </div>
      {accessory}
    </header>
  )
}

type RecordingPanelProps = {
  run: ReplayRun
  onChooseRun: (runId: string) => void
  onOpenTurn: (index: number) => void
}

function SourceButton({ onClick, label }: { onClick: () => void; label: string }) {
  return <button type="button" className="review-source-button" onClick={onClick}>{label}<ArrowUpRight size={14} aria-hidden="true" /></button>
}

function SourceCitation({ source, time, onOpen }: { source: string; time: string; onOpen: () => void }) {
  return (
    <div className="review-evidence-footer">
      <div className="review-citation">
        <SourceMark source={source} />
        <div><span>Source <time dateTime={time}>{time}</time></span><strong>{source}</strong></div>
      </div>
      <SourceButton label="Open source exchange" onClick={onOpen} />
    </div>
  )
}

function NoRecording() {
  return <p className="review-empty">This slot has no recorded events. Choose a recording to continue.</p>
}

export function OutcomesPanel({ run, onChooseRun, onOpenTurn }: RecordingPanelProps) {
  const snapshot = snapshotForRun(run.id, run.turns.length - 1)
  const replies = snapshot.history.filter(turn => turn.direction === 'outbound' && turn.reply).length
  const channels = [...new Set(snapshot.history.filter(turn => turn.direction === 'outbound').map(turn => turn.channel))]
  const hasDisclosure = snapshot.incidents.length > 0
  const stats = [
    { label: 'Contacts recorded', value: snapshot.contacts },
    { label: 'Persona replies', value: replies },
    { label: 'Confirmed disclosures', value: snapshot.incidents.length },
  ]

  return (
    <article className="review-page">
      <PageHeader
        label="Full recording"
        title="Scenarios & outcomes"
        description="See which channels were used and what the recording actually captured."
        accessory={<RecordingPicker runId={run.id} onChoose={onChooseRun} />}
      />
      {snapshot.turn ? (
        <>
          <Reveal className="review-glass review-summary">
            <div className="review-summary-title">
              <div>
                <p className="review-context">{run.target} · {channels.join(' / ') || 'Session record'}</p>
                <h2>{run.scenario}</h2>
              </div>
              <span className={`review-outcome-badge${hasDisclosure ? ' review-outcome-badge--finding' : ''}`}>
                <span aria-hidden="true" />{hasDisclosure ? 'Disclosure recorded' : 'No disclosure recorded'}
              </span>
            </div>
            <dl className="review-metrics">
              {stats.map(stat => <div key={stat.label}><dt>{stat.label}</dt><dd>{stat.value}</dd></div>)}
            </dl>
            <div className="review-outcome-strip" aria-label="Recorded event shortcuts">
              {snapshot.history.map((turn, index) => (
                <button type="button" key={turn.id} className={turn.incident ? 'is-disclosure' : undefined}
                  aria-label={`Open exchange: ${turn.label}`} title={`${turn.time} · ${turn.label}`} onClick={() => onOpenTurn(index)}>
                  <span aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>
                </button>
              ))}
            </div>
          </Reveal>
          <Reveal className="review-block">
            <div className="review-section-heading"><h2>Event record</h2><span>{run.name}</span></div>
            <ol className="review-event-list review-glass">
              {snapshot.history.map((turn, index) => (
                <li key={turn.id}>
                  <time dateTime={turn.time}>{turn.time}</time>
                  <div className="review-event-name"><strong>{turn.label}</strong><span>{turn.channel}</span></div>
                  <span className={`review-tag${turn.incident ? ' review-tag--finding' : ''}`}>{turn.incident ? 'Disclosure recorded' : turn.reaction === 'Silence' ? 'No reply' : turn.reaction}</span>
                  <SourceButton label="Replay" onClick={() => onOpenTurn(index)} />
                </li>
              ))}
            </ol>
          </Reveal>
        </>
      ) : <NoRecording />}
    </article>
  )
}

export function EvidencePanel({ run, onChooseRun, onOpenTurn }: RecordingPanelProps) {
  const { history, incidents } = snapshotForRun(run.id, run.turns.length - 1)
  const findings = history
    .map((turn, index) => ({ finding: turn.finding, index }))
    .filter(({ finding, index }) => history.findIndex(turn => turn.finding.id === finding.id) === index)

  return (
    <article className="review-page">
      <PageHeader
        label="Full recording"
        title="Evidence"
        description={history.length ? `Information gathered in ${run.target}’s demo recording, with the original sources.` : 'Information gathered from recorded sessions, with the original sources.'}
        accessory={<RecordingPicker runId={run.id} onChoose={onChooseRun} />}
      />
      {history.length > 0 ? (
        <>
          <Reveal className="review-block">
            <div className="review-section-heading"><h2>Confirmed disclosures</h2><span>{incidents.length} recorded</span></div>
            {incidents.length ? (
              <div className="review-evidence-grid">
                {incidents.map(incident => {
                  const index = history.findIndex(turn => turn.incident?.id === incident.id)
                  const event = history[index]
                  return (
                    <section className="review-glass review-evidence-card" key={incident.id}>
                      <Fingerprint size={21} aria-hidden="true" />
                      <p className="review-context">{incident.label}</p>
                      <h3>{incident.value}</h3>
                      <SourceCitation source={incident.source} time={event.time} onOpen={() => onOpenTurn(index)} />
                    </section>
                  )
                })}
              </div>
            ) : <p className="review-empty">No disclosure was recorded in this session.</p>}
          </Reveal>
          <div className="review-block">
            <div className="review-section-heading"><h2>Information gathered</h2><span>{findings.length} entries</span></div>
            <div className="review-evidence-grid">
              {findings.map(({ finding, index }) => (
                <Reveal key={finding.id} className="review-glass review-source-note">
                  <span className="review-tag">{finding.kind === 'Inference' ? 'Inference' : 'Recorded fact'}</span>
                  <h3>{finding.title}</h3>
                  <blockquote>“{finding.quote}”</blockquote>
                  <p>{finding.uncertainty}</p>
                  <SourceCitation source={finding.source} time={history[index].time} onOpen={() => onOpenTurn(index)} />
                  {finding.previous !== undefined && <SourceButton label="Earlier version" onClick={() => onOpenTurn(finding.previous!)} />}
                </Reveal>
              ))}
            </div>
          </div>
        </>
      ) : <NoRecording />}
    </article>
  )
}

const stages = [
  { label: 'Recorder', icon: AudioLines, detail: 'Keeps the recorded messages, channel, timestamp, and reactions together.', output: 'Session transcript' },
  { label: 'Ledger', icon: Database, detail: 'Keeps events in order and places corrections alongside the original record.', output: 'Ordered event history' },
  { label: 'Evidence reviewer', icon: ShieldCheck, detail: 'Ties confirmed disclosures to source events and separates observations from inferences.', output: 'Source-linked findings' },
  { label: 'Replay', icon: Layers3, detail: 'Reads the selected position in the recording so the timeline and transcript stay in sync.', output: 'Interactive timeline' },
] as const

export function ProcessPanel({ onEvidence }: { onEvidence: () => void }) {
  const [selected, setSelected] = useState(0)
  const reduced = useReducedMotion()
  const stage = stages[selected]

  return (
    <article className="review-page">
      <PageHeader label="Recorded review flow" title="From signal to evidence" description="Follow the handoffs that turn a recording into something you can inspect." />
      <Reveal className="review-glass review-process">
        <div className="review-process-grid" aria-label="Review stages">
          {stages.map(({ icon: Icon, label }, index) => (
            <Fragment key={label}>
              {index > 0 && <div className="review-connector" aria-hidden="true"><i /><i /><i /></div>}
              <motion.button className="review-stage" type="button" aria-pressed={selected === index} onClick={() => setSelected(index)}
                whileHover={reduced ? undefined : { y: -2 }} whileTap={reduced ? undefined : { scale: .975 }}
                transition={{ type: 'spring', stiffness: 380, damping: 28 }}
                onPointerMove={event => {
                  const bounds = event.currentTarget.getBoundingClientRect()
                  event.currentTarget.style.setProperty('--stage-x', `${event.clientX - bounds.left}px`)
                  event.currentTarget.style.setProperty('--stage-y', `${event.clientY - bounds.top}px`)
                }}>
                <svg className="review-stage-orbit" viewBox="0 0 220 122" preserveAspectRatio="none" aria-hidden="true">
                  <rect x="1" y="1" width="218" height="120" rx="22" pathLength="100" />
                </svg>
                <span className="review-stage-icon"><Icon size={25} strokeWidth={1.45} aria-hidden="true" /></span>
                <span>{label}</span>
              </motion.button>
            </Fragment>
          ))}
        </div>
        <div className="review-stage-detail" aria-live="polite">
          <div><p className="review-context">{stage.output}</p><h2>{stage.label}</h2></div>
          <p>{stage.detail}</p>
        </div>
      </Reveal>
      <Reveal className="review-handoff">
        <motion.div className="review-draw-line" aria-hidden="true" initial={reduced ? false : { scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }} transition={{ duration: reduced ? 0 : 0.7 }} />
        <div>
          <h2>Trace it to the source.</h2>
          <p>Open a finding and jump to the exchange that supports it.</p>
          <button type="button" className="review-cta" onClick={onEvidence}>Explore evidence<ArrowRight size={16} aria-hidden="true" /></button>
        </div>
      </Reveal>
    </article>
  )
}

const pixelMarks = [
  ['00100', '01110', '11011', '01110', '00100'],
  ['01100', '11010', '10101', '01011', '00110'],
  ['10001', '01110', '01110', '01110', '10001'],
]

function ProfileMark({ index }: { index: number }) {
  return (
    <span className={`review-avatar review-avatar--${index % pixelMarks.length}`} aria-hidden="true">
      {pixelMarks[index % pixelMarks.length].join('').split('').map((lit, cell) => <i key={cell} data-lit={lit === '1' || undefined} />)}
    </span>
  )
}

export function DemoPanel({ runId, onOpenRun }: { runId: string; onOpenRun: (runId: string) => void }) {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(runId)
  const matching = founderRuns.filter(run => run.target.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()))
  const selectedRun = matching.find(run => run.id === selected) ?? matching[0]

  return (
    <article className="review-page">
      <PageHeader label="Demo runner" title="Founder AI twins" description="Choose a founder profile to view its saved session." />
      <Reveal className="review-demo-controls">
        <form onSubmit={event => { event.preventDefault(); if (selectedRun) onOpenRun(selectedRun.id) }}>
          <label className="review-search">
            <Search size={17} aria-hidden="true" />
            <input type="search" aria-label="Filter founder profiles" placeholder="Find a founder" value={query} onChange={event => setQuery(event.currentTarget.value)} />
          </label>
          <fieldset>
            <legend className="sr-only">Founder profiles</legend>
            {matching.length ? (
              <div className="review-profiles">
                {matching.map(run => {
                  const checked = selectedRun?.id === run.id
                  return (
                    <label key={run.id} className="review-glass review-profile" data-selected={checked || undefined}>
                      <input type="radio" name="demo-profile" checked={checked} onChange={() => setSelected(run.id)} />
                      <ProfileMark index={founderRuns.indexOf(run)} />
                      <span className="review-profile-name">{run.target}</span>
                      <span className="review-context">{run.scenario}</span>
                      {checked ? <Check className="review-profile-icon" size={17} aria-hidden="true" /> : <ArrowDownRight className="review-profile-icon" size={17} aria-hidden="true" />}
                    </label>
                  )
                })}
              </div>
            ) : <p className="review-empty" role="status">No founder profiles match your search.</p>}
          </fieldset>
          <div className="review-demo-action">
            <p><FileText size={16} aria-hidden="true" /> {selectedRun?.turns.length ? 'Saved recording available' : 'No founder recordings loaded yet'}</p>
            <div className="review-demo-buttons">
              <button className="review-source-button" type="button" onClick={() => onOpenRun(replayRuns[0].id)}>
                Play fictional sample<Play size={14} aria-hidden="true" />
              </button>
              <button className="review-cta" type="submit" disabled={!selectedRun}>
                Open founder profile<ArrowRight size={15} aria-hidden="true" />
              </button>
            </div>
          </div>
        </form>
      </Reveal>
    </article>
  )
}

import { useState } from 'react'
import { ArrowUpRight } from 'lucide-react'
import { founderRuns, replayRuns, snapshotForRun } from '@/lib/replay-runs'

const methods = [
  {
    runId: 'demo-01',
    character: 'Dragon',
    palette: ['#274f36', '#73ef83', '#b8ffb4', '#216849', '#ffb56c'],
    sprite: [
      '.....11..........', '....1321.........', '...132221...1....', '..1322321..121...',
      '.1222222231221...', '12222222422221...', '12322222222221..1', '.1122114222221.13',
      '....1222222221131', '...1223322222221.', '..12333222222221.', '.122332242222221.',
      '.111122441224421.', '....12244122441..', '....11211.11211..', '.....11....11....',
    ],
  },
  {
    runId: 'demo-02',
    character: 'Sword',
    palette: ['#36463d', '#88a69a', '#dbffde', '#658a71', '#dd9a52'],
    sprite: [
      '............1111.', '...........13321.', '..........133221.', '.........1332241.',
      '........1332241..', '.......1332241...', '......1332241....', '...11.132241.....',
      '..154113241......', '..15511441.......', '...15411111......', '....1555441......',
      '...15511541......', '.115511.11.......', '155411...........', '15411............',
    ],
  },
  {
    runId: 'demo-04',
    character: 'Sentinel',
    palette: ['#34544e', '#6cd8c1', '#d2fff0', '#3f9d87', '#ebffb9'],
    sprite: [
      '.......151.......', '........1........', '......11111......', '....113333311....',
      '...13222222231...', '...12222222221...', '..1121111122111..', '..1421515122411..',
      '..1421111122411..', '..1122222222111..', '...114444411.....', '....13222231.....',
      '...11224422111...', '...13221122331...', '....111..111.....', '.....22..22......',
    ],
  },
]

function MethodSprite({ sprite, palette }: { sprite: readonly string[]; palette: readonly string[] }) {
  const shadows = sprite.flatMap((row, y) => [...row].flatMap((paint, x) => {
    const color = palette[Number(paint) - 1]
    return color ? [`${x * 4}px ${y * 4}px ${color}`] : []
  })).join(',')
  return <span className="method-sprite" aria-hidden="true"><span style={{ boxShadow: shadows }} /></span>
}

export function Methods({ onOpen }: { onOpen: (runId: string, turn: number) => void }) {
  return (
    <section className="terminal-catalog" aria-labelledby="methods-title">
      <h1 id="methods-title">Attack methods</h1>
      <p className="terminal-muted">Methods and outcomes in the sample recordings.</p>
      <div className="method-list">
        {methods.map(method => {
          const run = replayRuns.find(item => item.id === method.runId)
          if (!run?.turns.length) return null
          const { incidents, contacts } = snapshotForRun(run.id, run.turns.length - 1)
          const related = run.turns.findIndex(turn => turn.incident)
          const disclosures = incidents.filter(incident => incident.type === 'Disclosure').length
          return (
            <article className="method-entry" key={run.id}>
              <div className="method-illustration"><MethodSprite sprite={method.sprite} palette={method.palette} /></div>
              <div>
                <p className="catalog-meta">{method.character}</p>
                <h2>{run.turns[0].reasoning.lane}</h2>
                <p className="terminal-muted">{run.scenario}</p>
              </div>
              <div className="method-result">
                <strong>{disclosures ? `${disclosures} confirmed disclosure${disclosures === 1 ? '' : 's'}` : 'No disclosure recorded'}</strong>
                <p className="terminal-muted">{contacts} recorded {contacts === 1 ? 'contact' : 'contacts'}</p>
              </div>
              <button type="button" onClick={() => onOpen(run.id, Math.max(0, related))}>Open recording <ArrowUpRight size={15} aria-hidden="true" /></button>
            </article>
          )
        })}
      </div>
    </section>
  )
}

export function Founders() {
  const [selectedId, setSelectedId] = useState(founderRuns[0].id)
  const founder = founderRuns.find(profile => profile.id === selectedId) ?? founderRuns[0]

  return (
    <section className="terminal-catalog" aria-labelledby="founders-title">
      <h1 id="founders-title">Founders</h1>
      <div className="founder-lineup" role="group" aria-label="Choose a founder">
        {founderRuns.map(profile => (
          <button className="founder-choice" key={profile.id} type="button" aria-pressed={founder.id === profile.id}
            aria-controls="founder-details" onClick={() => setSelectedId(profile.id)}>
            <span className="founder-art">
              <img src={`/founders/${profile.id}.webp`} alt="" width={426} height={537} />
            </span>
            <strong>{profile.name}</strong>
            <span>{profile.scenario}</span>
          </button>
        ))}
      </div>
      <div className="founder-file" id="founder-details" aria-live="polite">
        <div key={founder.id}>
          <h2>{founder.name}</h2>
          <p>{founder.scenario}</p>
          <p className="catalog-meta">Source · challenge founder roster</p>
        </div>
        <div>
          <h3>Imported findings</h3>
          <p className="terminal-muted">No collection export is loaded for this founder.</p>
        </div>
      </div>
    </section>
  )
}

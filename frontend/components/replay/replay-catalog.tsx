import { useState } from 'react'
import { ArrowUpRight } from 'lucide-react'
import { founderRuns } from '@/lib/replay-runs'

// The 14 headings from ATTACK_LANES.md. The demo displays the catalog labels and artwork.
const methods = [
  { label: 'Enterprise Procurement RFP Matrix', color: '#9ee3ad', pixels: '011111110/120000021/120222021/120000021/120222021/120000021/120222021/122222221/011111110' },
  { label: 'Design Partner Latency Cohort', color: '#6be2d3', pixels: '000000000/000000100/000001210/000012110/001021010/012210010/121000010/110000010/011111110' },
  { label: 'Async Websocket Leak & CVE Advisory', color: '#ffb476', pixels: '010000010/001111100/012222210/121212121/122222221/011212110/010121010/001010100/010000010' },
  { label: 'Alumni Spotlight & Directory Verification', color: '#acbdf4', pixels: '000010000/001121100/112222211/012222210/011111120/001222020/001111020/000000120/000000000' },
  { label: 'Sports League Timing & Bib Roster', color: '#f1d67a', pixels: '000111000/000020000/001111100/012222210/122212221/122112221/122222221/012222210/001111100' },
  { label: 'Continuing Professional Education (CPD) Audit', color: '#8ed4ef', pixels: '011111110/122222221/120000021/120111021/120000021/122212221/011121110/000121000/000101000' },
  { label: 'Municipal Street Works & Resident Notice', color: '#ffb874', pixels: '000010000/000121000/000121000/001222100/001111100/012222210/012222210/111111111/122222221' },
  { label: 'Former Colleague Reconnect', color: '#c7a6ed', pixels: '001110000/012221000/120001000/120011100/120121221/012210021/001100021/000122210/000011100' },
  { label: 'Creative Contributor Release & Licensing', color: '#f5a0ac', pixels: '000001110/100012210/210122100/021221000/001210000/001220000/010000000/100000000/111110000' },
  { label: 'Boutique Specialist Advisory Consultation', color: '#7eeabf', pixels: '000111000/001222100/001212100/001222100/000121000/001222100/012222210/122222221/111111111' },
  { label: 'Consumer Restitution / Travel Disruption Claim', color: '#91ccf2', pixels: '000010000/100121001/122222221/001222100/000121000/000121000/001222100/001111100/000000000' },
  { label: 'Priority Courier Delivery Rescheduling', color: '#dfcf8c', pixels: '001111100/012222210/121111121/122212221/122212221/122212221/122212221/011111110/000000000' },
  { label: "Gary’s Double Twist / IT Quarantine Warning", color: '#f99691', pixels: '110000011/121111121/012222210/012212210/012212210/012222210/001212100/000121000/000010000' },
  { label: 'Corporate Security Training Completion Bonus', color: '#82f79d', pixels: '000111000/001222100/112222211/012121210/012222210/001222100/000121000/000121000/001111100' },
]

function MethodSprite({ pixels, color }: { pixels: string; color: string }) {
  const shadows = pixels.split('/').flatMap((row, y) => [...row].flatMap((paint, x) => {
    if (paint === '0') return []
    const fill = paint === '1' ? `color-mix(in srgb, ${color} 50%, #142119)` : color
    return [`${x * 4}px ${y * 4}px ${fill}`]
  })).join(',')
  return <span className="lane-sprite" aria-hidden="true"><span style={{ boxShadow: shadows }} /></span>
}

export function Methods() {
  return (
    <section className="terminal-catalog" aria-labelledby="methods-title">
      <h1 id="methods-title">Attack methods</h1>
      <p className="terminal-muted">14 documented simulator scenarios</p>
      <ol className="lane-catalog">
        {methods.map(({ label, color, pixels }, index) => (
          <li key={label}>
            <MethodSprite pixels={pixels} color={color} />
            <div>
              <p className="catalog-meta">LANE {String(index + 1).padStart(2, '0')}</p>
              <h2>{label}</h2>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}

const officialRoster = 'https://www.revel8.ai/grounding'
const fundingNote = 'https://www.revel8.ai/blog/revel8-secures-eu7-million-to-fight-ai-powered-cyberattacks'
const imprint = 'https://www.revel8.ai/imprint'

// Role summaries are corroborated against the company factsheet. Journal claims about
// contacts, relationships, and possible namesakes are outside this profile display.
const founderEvidence: Record<string, { journal: string; facts: { title: string; body: string; label: string; href: string }[] }> = {
  'founder-jm': {
    journal: 's_48a1336622.json',
    facts: [
      { title: 'Leadership', body: 'Co-founded revel8 in 2024 and serves as co-CEO.', label: 'revel8 factsheet', href: officialRoster },
      { title: 'Focus', body: 'Leads the business and go-to-market side of revel8.', label: 'revel8 founder bio', href: 'https://www.revel8.ai/de/author-julius' },
      { title: 'Public work', body: 'Authored the company’s September 2025 seed-round announcement.', label: 'revel8 announcement', href: fundingNote },
    ],
  },
  'founder-tm': {
    journal: 's_12be7046a2.json',
    facts: [
      { title: 'Leadership', body: 'Co-founded revel8 in 2024 and serves as co-CEO.', label: 'revel8 factsheet', href: officialRoster },
      { title: 'Focus', body: 'Leads product at revel8.', label: 'revel8 author byline', href: 'https://www.revel8.ai/magazine/what-is-osint-based-social-engineering-training' },
      { title: 'Company role', body: 'Listed as a managing director of revel8 GmbH.', label: 'revel8 imprint', href: imprint },
    ],
  },
  'founder-rs': {
    journal: 's_7d1a34d5ac.json',
    facts: [
      { title: 'Leadership', body: 'Co-founded revel8 in 2024 and serves as CTO.', label: 'revel8 factsheet', href: officialRoster },
      { title: 'Background', body: 'Worked at Celonis before co-founding revel8.', label: 'revel8 announcement', href: fundingNote },
      { title: 'Public work', body: 'Authored revel8’s July 2025 STACKIT Marketplace announcement.', label: 'revel8 announcement', href: 'https://www.revel8.ai/blog/revel8-is-now-live-on-the-stackit-marketplace---cybersecurity-awareness-built-for-europe' },
    ],
  },
}

export function Founders() {
  const [selectedId, setSelectedId] = useState(founderRuns[0].id)
  const founder = founderRuns.find(profile => profile.id === selectedId) ?? founderRuns[0]
  const evidence = founderEvidence[founder.id]

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
        <div>
          <h2>{founder.name}</h2>
          <p>{founder.scenario}</p>
          <p className="catalog-meta">Profile in journal · {evidence.journal}</p>
        </div>
        <div>
          <h3>Public professional information</h3>
          <dl className="founder-evidence">
            {evidence.facts.map(fact => (
              <div key={fact.title}>
                <dt>{fact.title}</dt>
                <dd>{fact.body}</dd>
                <dd><a href={fact.href} target="_blank" rel="noreferrer">{fact.label}<ArrowUpRight size={12} aria-hidden="true" /></a></dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </section>
  )
}

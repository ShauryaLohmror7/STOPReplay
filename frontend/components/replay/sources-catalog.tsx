import { useState } from 'react'
import {
  BookOpen,
  Briefcase,
  Code,
  Compass,
  Database,
  ExternalLink,
  FileText,
  Globe,
  Image as ImageIcon,
  Mic,
  Network,
  Search,
  Server,
  Share2,
  Shield,
  Sparkles,
  User,
  Users,
  Video
} from 'lucide-react'
import { getSourcesForRun, type ChannelStat } from '@/lib/sources-data'
import { RecordingPicker } from './review-recording-picker'
import './sources-replay.css'

// Logos matching the Architecture page (/channels/) with terminal-green styling
const CHANNEL_ASSETS: Record<string, { logo?: string; icon: any }> = {
  linkedin: { logo: 'linkedin.svg', icon: Briefcase },
  social: { logo: 'instagram.svg', icon: Share2 },
  whatsapp: { logo: 'whatsapp.svg', icon: Share2 },
  discord: { logo: 'discord.svg', icon: Code },
  slack: { logo: 'slack.svg', icon: Share2 },
  telegram: { logo: 'telegram.svg', icon: Share2 },
  signal: { logo: 'signal.svg', icon: Shield },
  x: { logo: 'x.svg', icon: Share2 },
  github: { logo: 'github.svg', icon: Code },
  youtube: { logo: 'youtube.svg', icon: Video },
  hackernews: { logo: 'hackernews.svg', icon: Code },
  reddit: { logo: 'reddit.svg', icon: Share2 },
  company_web: { icon: Globe },
  dns: { icon: Server },
  podcast: { icon: Mic },
  academic: { icon: BookOpen },
  registry: { icon: Search },
  web: { icon: Compass },
}

function SourceChannelIcon({ channelId }: { channelId: string }) {
  const asset = CHANNEL_ASSETS[channelId]
  if (asset?.logo) {
    return (
      <img
        src={`/channels/${asset.logo}`}
        alt=""
        width="18"
        height="18"
        className="channel-terminal-logo"
      />
    )
  }
  const IconComponent = asset?.icon ?? Compass
  return <IconComponent size={16} strokeWidth={1.6} />
}

export function SourcesCatalog({
  runId,
  onSelectRun
}: {
  runId: string
  onSelectRun: (runId: string) => void
}) {
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null)
  const data = getSourcesForRun(runId)

  const hasData = data.totalFacts > 0

  return (
    <section className="sources-catalog" aria-labelledby="sources-heading">
      {/* ── 1. Header with Title & Run Selector ── */}
      <div className="terminal-header">
        <div>
          <h1 id="sources-heading">
            <span>Sources</span> & Intelligence
          </h1>
          <div className="sources-hero-meta">
            <span>Target: <strong>{data.target}</strong></span>
            <span>•</span>
            <span>{data.role}</span>
            <span>•</span>
            <span className="sources-badge">
              <Database size={11} aria-hidden="true" /> Supabase Synced
            </span>
          </div>
        </div>
        <RecordingPicker runId={runId} onChoose={onSelectRun} />
      </div>

      {!hasData ? (
        <div className="sources-empty-state">
          <Database size={32} style={{ marginBottom: 12, opacity: 0.6 }} />
          <h3>No Sources Recorded for {data.target}</h3>
          <p>This slot is awaiting an active intelligence extraction pipeline run.</p>
        </div>
      ) : (
        <>
          {/* ── 2. Source Channels & Stream Convergence Bridge ── */}
          <div className="sources-stream-section">
            <div className="sources-stream-header">
              <h2>
                <Network size={16} /> Multi-Channel OSINT Ingestion
              </h2>
              <span>{data.channels.length} Source Vectors Discovered</span>
            </div>

            {/* Channels Ribbon */}
            <div className="sources-channels-grid">
              {data.channels.map((chan: ChannelStat) => (
                <div
                  key={chan.id}
                  className="channel-pill"
                  data-selected={selectedChannel === chan.id || undefined}
                  style={{
                    borderColor: selectedChannel === chan.id ? 'var(--terminal-green)' : undefined,
                    background: selectedChannel === chan.id ? '#122c1d' : undefined
                  }}
                  onClick={() => setSelectedChannel(prev => (prev === chan.id ? null : chan.id))}
                >
                  <div className="channel-pill-icon">
                    <SourceChannelIcon channelId={chan.id} />
                  </div>
                  <div className="channel-pill-info">
                    <span className="channel-pill-name">{chan.name}</span>
                    <span className="channel-pill-count">
                      <strong>{chan.factsCount}</strong> facts ({chan.sourcesCount} {chan.sourcesCount === 1 ? 'src' : 'srcs'})
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Convergence Bridge (Sleek Connection Stream) */}
            <div className="convergence-bridge">
              <svg className="convergence-lines-svg" viewBox="0 0 1000 38" preserveAspectRatio="none">
                <path className="convergence-path" d="M 50,2 Q 300,34 500,34" />
                <path className="convergence-path" d="M 250,2 Q 400,34 500,34" />
                <path className="convergence-path" d="M 500,2 L 500,34" />
                <path className="convergence-path" d="M 750,2 Q 600,34 500,34" />
                <path className="convergence-path" d="M 950,2 Q 700,34 500,34" />
              </svg>

              <div className="convergence-hub">
                <div className="hub-metric-group">
                  <div className="hub-metric">
                    <span className="hub-metric-label">Total Verified Facts</span>
                    <div className="hub-metric-value">
                      {data.totalFacts} <small>facts</small>
                    </div>
                  </div>
                  <div className="hub-metric">
                    <span className="hub-metric-label">Provenance Sources</span>
                    <div className="hub-metric-value">
                      {data.totalSources} <small>records</small>
                    </div>
                  </div>
                  <div className="hub-metric">
                    <span className="hub-metric-label">Assertability Rate</span>
                    <div className="hub-metric-value">
                      {data.assertableRate.toFixed(0)}% <small>grounded</small>
                    </div>
                  </div>
                </div>

                <div className="hub-status">
                  <span className="hub-pulse" />
                  <span>Durable Database Checkpoint</span>
                </div>
              </div>
            </div>
          </div>

          {/* ── 3. Practical Categorization & Metrics ── */}
          <div className="sources-metrics-section">
            <h2 className="sources-section-title">
              <Database size={18} /> Practical Intelligence Categories
            </h2>
            <p className="sources-section-desc">
              Normalized entity records partitioned across operational reconnaissance domains.
            </p>

            <div className="practical-grid">
              {/* Images & Visual Media */}
              <div className="practical-card">
                <div className="practical-card-top">
                  <div>
                    <div className="practical-card-label">Visual Media & Photos</div>
                    <div className="practical-card-detail">Profile pictures & headshots</div>
                  </div>
                  <div className="practical-card-icon">
                    <ImageIcon size={18} />
                  </div>
                </div>
                <div className="practical-card-number">{data.practicalMetrics.images}</div>
                {data.practicalMetrics.sampleImages && data.practicalMetrics.sampleImages.length > 0 && (
                  <div className="practical-image-strip">
                    {data.practicalMetrics.sampleImages.map((src, i) => (
                      <img key={i} src={src} alt="Verified photo" className="practical-thumb" />
                    ))}
                  </div>
                )}
              </div>

              {/* Files & Registrations */}
              <div className="practical-card">
                <div className="practical-card-top">
                  <div>
                    <div className="practical-card-label">Legal & Registrations</div>
                    <div className="practical-card-detail">German HRB, VAT & imprint docs</div>
                  </div>
                  <div className="practical-card-icon">
                    <FileText size={18} />
                  </div>
                </div>
                <div className="practical-card-number">{data.practicalMetrics.files}</div>
              </div>

              {/* Professional Roles */}
              <div className="practical-card">
                <div className="practical-card-top">
                  <div>
                    <div className="practical-card-label">Professional Info</div>
                    <div className="practical-card-detail">Roles, projects & corporate duties</div>
                  </div>
                  <div className="practical-card-icon">
                    <Briefcase size={18} />
                  </div>
                </div>
                <div className="practical-card-number">{data.practicalMetrics.professional}</div>
              </div>

              {/* Personal Info */}
              <div className="practical-card">
                <div className="practical-card-top">
                  <div>
                    <div className="practical-card-label">Personal & Academic</div>
                    <div className="practical-card-detail">Alumni degrees, sports & talks</div>
                  </div>
                  <div className="practical-card-icon">
                    <User size={18} />
                  </div>
                </div>
                <div className="practical-card-number">{data.practicalMetrics.personal}</div>
              </div>

              {/* Relationships & Org Structure */}
              <div className="practical-card">
                <div className="practical-card-top">
                  <div>
                    <div className="practical-card-label">Org Relationships</div>
                    <div className="practical-card-detail">Co-founders, colleagues & hosts</div>
                  </div>
                  <div className="practical-card-icon">
                    <Users size={18} />
                  </div>
                </div>
                <div className="practical-card-number">{data.practicalMetrics.relationships}</div>
              </div>

              {/* Contact Endpoints */}
              <div className="practical-card">
                <div className="practical-card-top">
                  <div>
                    <div className="practical-card-label">Contact & DNS Routing</div>
                    <div className="practical-card-detail">Email, MX host & social handles</div>
                  </div>
                  <div className="practical-card-icon">
                    <Server size={18} />
                  </div>
                </div>
                <div className="practical-card-number">{data.practicalMetrics.contacts}</div>
              </div>
            </div>
          </div>

          {/* ── 4. Analysis Results & Top Inferences ── */}
          <div className="sources-analysis-section">
            <div className="analysis-header-row">
              <div className="analysis-lane-pill">
                <span className="lane-tag">{data.analysis.unlockedLane}</span>
                <span className="weaponized-count">
                  <strong>{data.analysis.factsUsed}</strong> facts weaponized in attack
                </span>
              </div>
              <div className="sources-badge">
                <Shield size={12} /> 0-pt Hallucination Risk
              </div>
            </div>

            {/* Psychological Hook */}
            <div className="analysis-hook-box">
              <div className="analysis-hook-label">Psychological Pretext Hook</div>
              <p className="analysis-hook-text">“{data.analysis.psychologicalHook}”</p>
            </div>

            {/* Top Inferences List */}
            <h3 style={{ font: '400 15px "Departure Mono", monospace', color: 'var(--terminal-green)', margin: '0 0 14px' }}>
              <Sparkles size={14} style={{ display: 'inline', marginRight: 6 }} /> Top Evidence-Backed Inferences
            </h3>

            <div className="inferences-list">
              {data.analysis.inferences.map((inf, i) => (
                <article key={i} className="inference-card">
                  <div className="inference-card-header">
                    <span className="inference-card-title">{inf.title}</span>
                    <span className={`inference-kind-badge ${inf.kind.toLowerCase().replace(' ', '-')}`}>
                      {inf.kind}
                    </span>
                  </div>

                  <blockquote className="inference-quote">“{inf.quote}”</blockquote>

                  <div className="inference-footer">
                    <span className="inference-source-cite">
                      <ExternalLink size={12} /> {inf.source}
                    </span>
                    {inf.uncertainty && (
                      <span className="inference-uncertainty">
                        Note: {inf.uncertainty}
                      </span>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </div>
        </>
      )}
    </section>
  )
}

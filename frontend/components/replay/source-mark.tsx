import { CalendarDays, FileText, History, Link2, MessageSquare, Radio, type LucideIcon } from 'lucide-react'

const platforms = [
  { host: 'linkedin.com', label: 'LinkedIn', icon: 'linkedin.svg' },
  { host: 'instagram.com', label: 'Instagram', icon: 'instagram.png' },
  { host: 'slack.com', label: 'Slack', icon: 'slack.svg' },
  { host: 'discord.com', label: 'Discord', icon: 'discord.svg' },
  { host: 'whatsapp.com', label: 'WhatsApp', icon: 'whatsapp.svg' },
  { host: 't.me', label: 'Telegram', icon: 'telegram.svg' },
  { host: 'x.com', label: 'X', icon: 'x.svg' },
  { host: 'messenger.com', label: 'Messenger', icon: 'messenger.png' },
]

function getPlatform(source: string) {
  try {
    const url = new URL(source)
    if (url.protocol !== 'https:' && url.protocol !== 'http:') return undefined
    const host = url.hostname.toLowerCase().replace(/\.$/, '')
    return platforms.find(platform => host === platform.host || host.endsWith(`.${platform.host}`))
  } catch {
    return undefined
  }
}

export function SourceMark({ source }: { source: string }) {
  const platform = getPlatform(source)
  if (platform) {
    return (
      <span className="source-mark" title={platform.label}>
        <img src={`/channels/${platform.icon}`} alt={platform.label} width={16} height={16} />
      </span>
    )
  }

  const [Icon, label]: [LucideIcon, string] = /^(review-)?agenda\b/i.test(source) ? [CalendarDays, 'Agenda']
    : /^reply-/i.test(source) ? [MessageSquare, 'Recorded reply']
    : /^sim-event-/i.test(source) ? [Radio, 'Simulator event']
    : /^recovery-log-/i.test(source) ? [History, 'Recovery log']
    : /^https?:\/\//i.test(source) ? [Link2, 'Web source']
    : [FileText, 'Recorded source']

  return <span className="source-mark" role="img" aria-label={label} title={label}><Icon size={15} strokeWidth={1.7} aria-hidden="true" /></span>
}

import { createRef, useEffect, useRef, useState } from 'react'
import { CalendarDays, FileText, Mail, MessageCircle, MessagesSquare, Phone, ShieldCheck, Video, Voicemail, type LucideIcon } from 'lucide-react'
import { AnimatedBeam } from '@/components/ui/animated-beam'
import Padlock from '@/components/ui/padlock'

type Channel = { name: string; logo?: string; icon?: LucideIcon; label?: string }
// Familiar brand marks lead each side. Teams messages and calls share one logo.
const leftChannels: Channel[] = [
  {name:'WhatsApp',logo:'whatsapp.svg'},
  {name:'Instagram',logo:'instagram.png'},
  {name:'Telegram',logo:'telegram.svg'},
  {name:'Slack',logo:'slack.svg'},
  {name:'Discord',logo:'discord.svg'},
  {name:'LinkedIn',logo:'linkedin.svg'},
  {name:'Email',icon:Mail},
  {name:'SMS',icon:MessageCircle},
  {name:'Calendar invite',label:'Calendar',icon:CalendarDays},
  {name:'Shared document',label:'Document',icon:FileText},
]
const rightChannels: Channel[] = [
  {name:'iMessage',logo:'imessage.png'},
  {name:'Messenger',logo:'messenger.png'},
  {name:'Teams messages and calls',logo:'microsoftteams.png'},
  {name:'Signal',logo:'signal.svg'},
  {name:'X',logo:'x.svg'},
  {name:'Phone call',icon:Phone},
  {name:'Video call',icon:Video},
  {name:'Live chat',icon:MessagesSquare},
  {name:'Voicemail',icon:Voicemail},
  {name:'MFA prompt',icon:ShieldCheck},
]
const channels = [...leftChannels, ...rightChannels]

function ChannelIcon({channel}:{channel:Channel}) {
  if(channel.logo) return <img src={`/channels/${channel.logo}`} className={channel.logo.endsWith('.png')?'is-app-icon':undefined} alt="" width="28" height="28"/>
  const Icon=channel.icon!
  return <Icon size={25} strokeWidth={1.4} aria-hidden="true"/>
}

export function ChannelNetwork({active,paused=false}:{active:boolean;paused?:boolean}) {
  const containerRef=useRef<HTMLDivElement>(null)
  const centerRef=useRef<HTMLDivElement>(null)
  const [nodeRefs]=useState(()=>channels.map(()=>createRef<HTMLSpanElement>()))
  const [opened,setOpened]=useState(false)
  // A small page movement fully opens the lock, independent of section height.
  // Keep it open while exploring; returning to the top resets it.
  useEffect(()=>{
    if(!active){setOpened(false);return}
    if(paused)return
    const update=()=>{
      if(window.scrollY>=16)setOpened(true)
      else if(window.scrollY<=2)setOpened(false)
    }
    update()
    window.addEventListener('scroll',update,{passive:true})
    return()=>window.removeEventListener('scroll',update)
  },[active,paused])

  function nodes(group:Channel[],offset:number) {
    return group.map((channel,j)=><div key={channel.name} className="channel-node" role="img" aria-label={channel.name}>
      <span ref={nodeRefs[j+offset]} className="channel-logo"><ChannelIcon channel={channel}/></span>
      {!channel.logo&&<span className="channel-node-label" aria-hidden="true">{channel.label??channel.name}</span>}
    </div>)
  }
  return <div className="channel-frame">
    <div className="channel-network channel-network--lock" ref={containerRef}>
      <div className="channel-cluster channel-cluster--left">{nodes(leftChannels,0)}</div>
      <div className="channel-lock" ref={centerRef}>
        <Padlock className="channel-padlock" theme="dark" intensity={1} open={opened} paused={!active||paused}
          aria-label={opened?'Open padlock':'Closed padlock — scroll to open'}/>
      </div>
      <div className="channel-cluster channel-cluster--right">{nodes(rightChannels,leftChannels.length)}</div>
      {channels.map((channel,i)=>{
        const left = i < leftChannels.length
        const row = Math.floor((left ? i : i - leftChannels.length) / 3)
        return <AnimatedBeam key={channel.name} className="channel-link"
          containerRef={containerRef} fromRef={centerRef} toRef={nodeRefs[i]}
          active={active && opened && !paused} singlePass pixelated={false} glow={false}
          curvature={0} startXOffset={left ? -20 : 20} startYOffset={20}
          endXOffset={left ? 18 : -18}
          pathColor="#ffffff" pathWidth={.9} pathOpacity={.16} beamOpacity={.92}
          gradientStopColor="#91d9ed" duration={1.0 + row * .07} delay={.19 + row * .06}
        />
      })}
    </div>
  </div>
}

export const channelCount=channels.length
export const channelNames=channels.map(channel=>channel.name)

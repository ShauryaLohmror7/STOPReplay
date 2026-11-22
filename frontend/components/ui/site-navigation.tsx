import { viewHref, type AppView } from '@/lib/navigation'
import { PixelIcon } from './pixel-icon'
const pages = [{ view: 'portrait', name: 'Intro' }, { view: 'architecture', name: 'Architecture' }, { view: 'replay', name: 'Replay' }] as const
export function SiteNavigation({ view, onNavigate, onPreload }: { view: AppView; onNavigate: (view: AppView) => void; onPreload: () => void }) {
  return <header className={`site-navigation ${view === 'portrait' ? 'site-navigation--intro' : ''}`}>
    <a className="site-wordmark" href="/" aria-label="STOPReplay intro" onClick={event => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
      event.preventDefault(); onNavigate('portrait')
    }}>STOP<span>/</span>REPLAY<span>.</span></a>
    <nav aria-label="Main navigation">{pages.map(page => <a key={page.view} href={viewHref(page.view)} aria-current={view === page.view ? 'page' : undefined}
      onPointerEnter={page.view === 'replay' ? onPreload : undefined} onFocus={page.view === 'replay' ? onPreload : undefined}
      onClick={event => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
        event.preventDefault(); onNavigate(page.view)
      }}><span>{page.name}</span>{page.view === 'replay' && <PixelIcon name="arrowUpRight" size={12}/>}</a>)}</nav>
    <span className="site-mode"><PixelIcon name="lock" size={12}/>{view === 'replay' ? 'RECORDED / READ ONLY' : 'STOPREPLAY LAB'}</span>
  </header>
}

import { Component, lazy, Suspense, useCallback, useEffect, useState, type ReactNode } from 'react'
import { useMotionValue } from 'motion/react'
import { PortraitReveal } from '@/components/ui/portrait-reveal'
import { SiteNavigation } from '@/components/ui/site-navigation'
import ArchitecturePage from '@/components/architecture/architecture-page'
import { viewFromSearch, viewHref, type AppView } from '@/lib/navigation'
import './components/replay/replay.css'
import './styles/pixel-system.css'
import './styles/site-navigation.css'
const loadReplay = () => import('@/components/replay/review-workspace')
const ReplayWorkspace = lazy(loadReplay)
const preloadReplay = () => { void loadReplay().catch(() => {}) }
class ViewBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() { return this.state.failed ? <div className="replay-loading"><h1>This view couldn’t load.</h1><button className="text-button" onClick={() => window.location.reload()}>Reload this page</button></div> : this.props.children }
}
export default function App() {
  const [view, setView] = useState<AppView>(() => viewFromSearch(window.location.search))
  const handoff = useMotionValue(view === 'portrait' ? 0 : 1)
  const showView = useCallback((next: AppView) => {
    handoff.set(next === 'portrait' ? 0 : 1)
    setView(next)
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [handoff])
  const navigate = useCallback((next: AppView) => {
    if (viewFromSearch(window.location.search) !== next) window.history.pushState(null, '', viewHref(next))
    showView(next)
  }, [showView])
  useEffect(() => {
    const pop = () => showView(viewFromSearch(window.location.search))
    window.addEventListener('popstate', pop)
    return () => window.removeEventListener('popstate', pop)
  }, [showView])
  useEffect(() => { document.title = `STOPReplay — ${view === 'portrait' ? 'Intro' : view === 'architecture' ? 'Architecture' : 'Agent replay'}` }, [view])
  const updateExit = useCallback((value: number) => handoff.set(value), [handoff])
  const enterArchitecture = useCallback(() => navigate('architecture'), [navigate])
  const entered = view !== 'portrait'
  return <>
    <SiteNavigation view={view} onNavigate={navigate} onPreload={preloadReplay}/>
    <main className={entered ? 'experience experience--replay site-content' : 'experience'}>
      <ViewBoundary key={view}>
        {view === 'replay' ? <Suspense fallback={<div className="replay-loading" role="status">Opening recorded history…</div>}><ReplayWorkspace/></Suspense>
          : <div className="architecture-layer" inert={!entered} aria-hidden={!entered}><ArchitecturePage active={entered} progress={handoff} onNavigate={navigate}/></div>}
        {view === 'portrait' && <div className="portrait-overlay"><PortraitReveal onExitProgress={updateExit} onEntered={enterArchitecture}/></div>}
      </ViewBoundary>
    </main>
  </>
}

export type AppView = 'portrait' | 'architecture' | 'replay'
export function viewFromSearch(search: string): AppView {
  const requested = new URLSearchParams(search).get('view')
  return requested === 'architecture' || requested === 'replay' ? requested : 'portrait'
}
export function viewHref(view: AppView) { return view === 'portrait' ? '/' : `/?view=${view}` }

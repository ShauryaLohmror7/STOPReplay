import { useId, type ReactNode } from 'react'

// Independent view tabs never change the selected recorded turn.
export function TraceTabs<T extends string>({ label, tabs, selected, onChange, children }: {
  label: string; tabs: readonly { id: T; label: string }[]; selected: T;
  onChange: (id: T) => void; children: ReactNode;
}) {
  const id = useId()
  return <>
    <div className="trace-tabs" role="tablist" aria-label={label}>
      {tabs.map((tab, index) => <button key={tab.id} id={`${id}-${tab.id}`} role="tab"
        aria-selected={selected === tab.id} aria-controls={`${id}-panel`} tabIndex={selected === tab.id ? 0 : -1}
        onClick={() => onChange(tab.id)} onKeyDown={event => {
          let next = index
          if (event.key === 'ArrowRight') next = (index + 1) % tabs.length
          else if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length
          else if (event.key === 'Home') next = 0
          else if (event.key === 'End') next = tabs.length - 1
          else return
          event.preventDefault()
          onChange(tabs[next].id)
          document.getElementById(`${id}-${tabs[next].id}`)?.focus()
        }}>{tab.label}</button>)}
    </div>
    <div id={`${id}-panel`} className="trace-tab-panel" role="tabpanel" aria-labelledby={`${id}-${selected}`} tabIndex={0}>{children}</div>
  </>
}

import { useEffect, useState } from 'react'

const SECTIONS = [
  { id: 'signal',      label: 'Top Signal' },
  { id: 'graph',       label: 'Graph' },
  { id: 'heatmap',     label: 'Heatmap' },
  { id: 'signals',     label: 'Signals' },
  { id: 'predictions', label: 'Predictions' },
]

export function SectionNav() {
  const [active, setActive] = useState('signal')

  useEffect(() => {
    const observers: IntersectionObserver[] = []

    SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id)
      if (!el) return
      const obs = new IntersectionObserver(
        ([entry]) => { if (entry.isIntersecting) setActive(id) },
        { rootMargin: '-10% 0px -85% 0px', threshold: 0 },
      )
      obs.observe(el)
      observers.push(obs)
    })

    return () => observers.forEach(o => o.disconnect())
  }, [])

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <nav
      aria-label="Page sections"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 10,
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg)',
        overflowX: 'auto',
        scrollbarWidth: 'none',
      }}
    >
      <div style={{ display: 'flex', padding: '0 40px' }}>
        {SECTIONS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => scrollTo(id)}
            style={{
              padding: '9px 16px',
              fontSize: '0.8125rem',
              fontWeight: active === id ? 600 : 400,
              color: active === id ? 'var(--text-1)' : 'var(--text-3)',
              background: 'none',
              border: 'none',
              borderBottom: `2px solid ${active === id ? 'var(--accent)' : 'transparent'}`,
              cursor: 'pointer',
              transition: 'color 0.15s, border-color 0.15s',
              whiteSpace: 'nowrap',
              marginBottom: -1,
            }}
          >
            {label}
          </button>
        ))}
      </div>
    </nav>
  )
}

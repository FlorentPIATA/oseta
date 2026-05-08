import cytoscape from 'cytoscape'
import { useEffect, useRef, useState } from 'react'
import { useCorrelationMatrix } from '../hooks/useCorrelationMatrix'
import type { HeatmapCell } from '../types/correlation'

type View = 'table' | 'graph'

function getCSSVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function lagLabel(days: number): string {
  if (days < 7) return `${days}d`
  const w = Math.floor(days / 7)
  const d = days % 7
  return d > 0 ? `${w}w ${d}d` : `${w}w`
}

function buildGraph(cells: HeatmapCell[]) {
  const leads = cells.filter(c => c.is_significant && c.lag_days > 0)
  const leadCount: Record<string, number> = {}
  leads.forEach(c => { leadCount[c.sector_a_code] = (leadCount[c.sector_a_code] || 0) + 1 })

  const nodeIds = new Set<string>()
  leads.forEach(c => { nodeIds.add(c.sector_a_code); nodeIds.add(c.sector_b_code) })

  const nodes = [...nodeIds].map(id => ({
    data: {
      id, label: id,
      size: 48 + (leadCount[id] || 0) * 14,
      isLeader: (leadCount[id] || 0) > 0,
    },
  }))
  const edges = leads.map(c => ({
    data: {
      id:       `${c.sector_a_code}-${c.sector_b_code}`,
      source:   c.sector_a_code,
      target:   c.sector_b_code,
      label:    `${lagLabel(c.lag_days)} · r=${Math.abs(c.correlation).toFixed(2)}`,
      positive: c.correlation > 0,
      width:    Math.abs(c.correlation) < 0.5 ? 1 : Math.abs(c.correlation) < 0.7 ? 2.5 : 4.5,
    },
  }))
  return { nodes, edges }
}

export function LeadGraph() {
  const { data, isLoading } = useCorrelationMatrix('pearson')
  const [view, setView]     = useState<View>('table')
  const containerRef        = useRef<HTMLDivElement>(null)
  const cyRef               = useRef<cytoscape.Core | null>(null)

  const [colorScheme, setColorScheme] = useState<'light' | 'dark'>(() =>
    window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  )

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e: MediaQueryListEvent) => setColorScheme(e.matches ? 'dark' : 'light')
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  useEffect(() => {
    if (view !== 'graph') {
      cyRef.current?.destroy()
      cyRef.current = null
      return
    }
    if (!containerRef.current || !data?.cells.length) return

    const { nodes, edges } = buildGraph(data.cells)
    if (!nodes.length) return

    const nodeColor  = getCSSVar('--text-1')
    const nodeBg     = getCSSVar('--bg-2')
    const leaderBg   = getCSSVar('--accent-bg')
    const nodeBorder = getCSSVar('--border')
    const accentCol  = getCSSVar('--accent')
    const posEdge    = getCSSVar('--pos')
    const negEdge    = getCSSVar('--neg')
    const labelColor = getCSSVar('--text-3')
    const bgColor    = getCSSVar('--bg')

    cyRef.current?.destroy()
    cyRef.current = cytoscape({
      container: containerRef.current,
      elements: [...nodes, ...edges],
      style: [
        {
          selector: 'node',
          style: {
            label:              'data(label)',
            'font-family':      'monospace',
            'font-size':        '11px',
            'font-weight':      700,
            color:              nodeColor,
            'text-valign':      'center',
            'text-halign':      'center',
            'background-color': nodeBg,
            'border-color':     nodeBorder,
            'border-width':     1.5,
            width:              'data(size)',
            height:             'data(size)',
          },
        },
        {
          selector: 'node[?isLeader]',
          style: {
            'background-color': leaderBg,
            'border-color':     accentCol,
            'border-width':     2,
            color:              accentCol,
          },
        },
        {
          selector: 'edge',
          style: {
            label:                     'data(label)',
            'font-family':             'monospace',
            'font-size':               '8px',
            color:                     labelColor,
            'text-rotation':           'autorotate',
            'text-margin-y':           -8,
            'text-background-color':   bgColor,
            'text-background-opacity': 0.8,
            'text-background-padding': '2px',
            width:                     'data(width)',
            'line-color':              posEdge,
            'target-arrow-color':      posEdge,
            'target-arrow-shape':      'triangle',
            'curve-style':             'bezier',
            opacity:                   0.85,
          },
        },
        {
          selector: 'edge[!positive]',
          style: {
            'line-color':            negEdge,
            'target-arrow-color':    negEdge,
            'line-style':            'dashed',
            'line-dash-pattern':     [6, 3],
          },
        },
        {
          selector: 'node:selected',
          style: { 'border-color': accentCol, 'border-width': 3 },
        },
        {
          selector: '.faded',
          style: { opacity: 0.15 },
        },
      ],
      layout: {
        name: 'cose',
        padding: 36,
        nodeRepulsion: () => 8000,
        idealEdgeLength: () => 110,
        edgeElasticity: () => 80,
        gravity: 0.4,
        numIter: 1000,
        animate: true,
        animationDuration: 500,
        randomize: false,
      },
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
      minZoom: 0.4,
      maxZoom: 3,
    })

    cyRef.current.on('mouseover', 'node', e => {
      const node = e.target
      cyRef.current?.elements().addClass('faded')
      node.removeClass('faded')
      node.connectedEdges().removeClass('faded')
      node.connectedEdges().connectedNodes().removeClass('faded')
    })
    cyRef.current.on('mouseout', 'node', () => {
      cyRef.current?.elements().removeClass('faded')
    })

    return () => { cyRef.current?.destroy(); cyRef.current = null }
  }, [data, colorScheme, view])

  const signals = data?.cells
    .filter(c => c.is_significant && c.lag_days > 0)
    .sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation))
    ?? []

  const maxR = signals.length ? Math.max(...signals.map(c => Math.abs(c.correlation))) : 1

  return (
    <div>

      {/* Header + toggle */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <p style={{ fontSize: '0.6875rem', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-3)' }}>
          Leading Indicators
        </p>
        <div style={{ display: 'flex', borderRadius: 5, border: '1px solid var(--border)', overflow: 'hidden', fontSize: '0.6875rem' }}>
          {(['table', 'graph'] as const).map((v, i) => (
            <button
              key={v}
              onClick={() => setView(v)}
              style={{
                padding: '4px 10px',
                background: view === v ? 'var(--accent)' : 'transparent',
                color: view === v ? 'white' : 'var(--text-3)',
                border: 'none',
                borderRight: i === 0 ? '1px solid var(--border)' : 'none',
                cursor: 'pointer',
                fontWeight: view === v ? 600 : 400,
                transition: 'background 0.15s, color 0.15s',
                letterSpacing: '0.03em',
              }}
            >
              {v === 'table' ? 'Table' : 'Graph'}
            </button>
          ))}
        </div>
      </div>

      {/* Skeleton */}
      {isLoading && (
        <div className="animate-pulse" style={{ height: 260, borderRadius: 8, background: 'var(--bg-3)' }} />
      )}

      {/* ── Table view ────────────────────────────────────── */}
      {!isLoading && view === 'table' && (
        <>
          {!signals.length ? (
            <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--bg-2)', color: 'var(--text-3)', fontSize: '0.875rem' }}>
              No significant signals yet
            </div>
          ) : (
            <div style={{ borderRadius: 8, border: '1px solid var(--border)', overflow: 'hidden' }}>
              {/* Column headers */}
              <div style={{ display: 'grid', gridTemplateColumns: '28px 1fr 88px 52px 44px', gap: 8, padding: '7px 14px', background: 'var(--bg-2)', borderBottom: '1px solid var(--border)' }}>
                {[['#', 'left'], ['Leading → Lagging', 'left'], ['Strength', 'left'], ['r', 'right'], ['Lag', 'right']].map(([label, align]) => (
                  <span key={label} style={{ fontSize: '0.625rem', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-3)', textAlign: align as 'left' | 'right' }}>
                    {label}
                  </span>
                ))}
              </div>

              {/* Rows */}
              {signals.map((cell, i) => {
                const isPos  = cell.correlation > 0
                const color  = isPos ? 'var(--pos)' : 'var(--neg)'
                const barPct = (Math.abs(cell.correlation) / maxR * 100).toFixed(1)
                const rStr   = (cell.correlation > 0 ? '+' : '') + cell.correlation.toFixed(2)

                return (
                  <div
                    key={`${cell.sector_a_code}-${cell.sector_b_code}`}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '28px 1fr 88px 52px 44px',
                      gap: 8,
                      alignItems: 'center',
                      padding: '9px 14px',
                      borderBottom: i < signals.length - 1 ? '1px solid var(--border)' : 'none',
                      transition: 'background 0.1s',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-2)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    <span style={{ fontFamily: 'monospace', fontSize: '0.6875rem', color: 'var(--text-3)' }} className="stat">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, minWidth: 0 }}>
                      <span style={{ fontFamily: 'monospace', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-1)', background: 'var(--bg-2)', padding: '1px 6px', borderRadius: 3, whiteSpace: 'nowrap' }}>
                        {cell.sector_a_code}
                      </span>
                      <span style={{ color: 'var(--text-3)', fontSize: '0.75rem', flexShrink: 0 }}>→</span>
                      <span style={{ fontFamily: 'monospace', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-1)', background: 'var(--bg-2)', padding: '1px 6px', borderRadius: 3, whiteSpace: 'nowrap' }}>
                        {cell.sector_b_code}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <div style={{ flex: 1, height: 5, background: 'var(--bg-3)', borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{ width: `${barPct}%`, height: '100%', background: color, borderRadius: 3 }} />
                      </div>
                    </div>
                    <span style={{ fontFamily: 'monospace', fontSize: '0.8125rem', fontWeight: 600, color, textAlign: 'right' }} className="stat">
                      {rStr}
                    </span>
                    <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--text-3)', textAlign: 'right', whiteSpace: 'nowrap' }} className="stat">
                      {lagLabel(cell.lag_days)}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
          <p style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--text-3)' }}>
            Sorted by |r|. Green = positive lead, red = inverse.
          </p>
        </>
      )}

      {/* ── Graph view ────────────────────────────────────── */}
      {!isLoading && view === 'graph' && (
        <>
          <div
            ref={containerRef}
            style={{ height: 300, borderRadius: 8, border: '1px solid var(--border)', background: 'var(--bg-2)', overflow: 'hidden' }}
          >
            {!signals.length && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-3)', fontSize: '0.875rem' }}>
                No significant signals yet
              </div>
            )}
          </div>
          <p style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--text-3)' }}>
            Node size = sectors led · Thickness = |r| · Dashed = inverse · Hover to focus · Scroll to zoom
          </p>
        </>
      )}

    </div>
  )
}

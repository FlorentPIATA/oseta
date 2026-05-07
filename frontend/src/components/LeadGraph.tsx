import cytoscape from 'cytoscape'
import { useEffect, useRef } from 'react'
import { useCorrelationMatrix } from '../hooks/useCorrelationMatrix'
import type { HeatmapCell } from '../types/correlation'

function lagHuman(days: number): string {
  const w = Math.round(days / 7)
  return w <= 1 ? `${days}d` : `${w}w`
}

function buildGraph(cells: HeatmapCell[]) {
  const leads = cells.filter(c => c.is_significant && c.lag_days > 0)
  const nodeIds = new Set<string>()
  leads.forEach(c => { nodeIds.add(c.sector_a_code); nodeIds.add(c.sector_b_code) })

  const nodes = [...nodeIds].map(id => ({
    data: { id, label: id },
  }))
  const edges = leads.map(c => ({
    data: {
      id:     `${c.sector_a_code}-${c.sector_b_code}`,
      source: c.sector_a_code,
      target: c.sector_b_code,
      label:  `${lagHuman(c.lag_days)} · r=${Math.abs(c.correlation).toFixed(2)}`,
      positive: c.correlation > 0,
    },
  }))
  return { nodes, edges }
}

export function LeadGraph() {
  const { data, isLoading } = useCorrelationMatrix('pearson')
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef        = useRef<cytoscape.Core | null>(null)

  useEffect(() => {
    if (!containerRef.current || !data?.cells.length) return

    const { nodes, edges } = buildGraph(data.cells)
    if (!nodes.length) return

    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const nodeColor  = isDark ? '#e2e8f0' : '#1e293b'
    const nodeBg     = isDark ? '#1e2a3a' : '#f1f5f9'
    const nodeBorder = isDark ? '#334155' : '#cbd5e1'
    const posEdge    = isDark ? '#4ade80' : '#16a34a'
    const negEdge    = isDark ? '#f87171' : '#dc2626'
    const labelColor = isDark ? '#94a3b8' : '#64748b'

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
            'font-weight':      600,
            color:              nodeColor,
            'text-valign':      'center',
            'text-halign':      'center',
            'background-color': nodeBg,
            'border-color':     nodeBorder,
            'border-width':     1,
            width:              52,
            height:             52,
          },
        },
        {
          selector: 'edge',
          style: {
            label:               'data(label)',
            'font-family':       'monospace',
            'font-size':         '9px',
            color:               labelColor,
            'text-rotation':     'autorotate',
            'text-margin-y':     -8,
            width:               1.5,
            'line-color':        posEdge,
            'target-arrow-color': posEdge,
            'target-arrow-shape': 'triangle',
            'curve-style':       'bezier',
          },
        },
        {
          selector: 'edge[?positive]',
          style: { 'line-color': posEdge, 'target-arrow-color': posEdge },
        },
        {
          selector: 'edge[!positive]',
          style: { 'line-color': negEdge, 'target-arrow-color': negEdge },
        },
        {
          selector: 'node:selected',
          style: { 'border-color': isDark ? '#818cf8' : '#4f46e5', 'border-width': 2 },
        },
      ],
      layout: { name: 'circle', padding: 24 },
      userZoomingEnabled: false,
      userPanningEnabled: false,
      boxSelectionEnabled: false,
    })

    return () => { cyRef.current?.destroy(); cyRef.current = null }
  }, [data])

  return (
    <div>
      <p style={{ fontSize: '0.6875rem', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-3)', marginBottom: 12 }}>
        Leading Indicators
      </p>
      <div
        ref={containerRef}
        style={{
          height: 260,
          borderRadius: 8,
          border: '1px solid var(--border)',
          background: 'var(--bg-2)',
          overflow: 'hidden',
        }}
      >
        {isLoading && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-3)', fontSize: '0.875rem' }}>
            Loading…
          </div>
        )}
        {!isLoading && !data?.cells.length && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-3)', fontSize: '0.875rem' }}>
            No significant signals yet
          </div>
        )}
      </div>
      <p style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--text-3)' }}>
        Arrows point from leading sector to lagging sector. Green = positive correlation, red = inverse.
      </p>
    </div>
  )
}

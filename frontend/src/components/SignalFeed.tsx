import { useState } from 'react'
import { useCorrelationMatrix } from '../hooks/useCorrelationMatrix'
import type { HeatmapCell } from '../types/correlation'

function strengthLabel(r: number): { label: string; color: string } {
  const abs = Math.abs(r)
  if (abs >= 0.7) return { label: 'Strong',    color: 'var(--pos)' }
  if (abs >= 0.5) return { label: 'Moderate',  color: 'var(--accent)' }
  return               { label: 'Weak',      color: 'var(--text-3)' }
}

function lagHuman(days: number): string {
  const w = Math.round(days / 7)
  if (w === 0) return `${days} days`
  return w === 1 ? `1 week (${days}d)` : `${w} weeks (${days}d)`
}

function SignalCard({ cell, index }: { cell: HeatmapCell; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const isPos    = cell.correlation > 0
  const strength = strengthLabel(cell.correlation)
  const pLabel   = cell.p_value != null
    ? (cell.p_value < 0.001 ? 'p < 0.001' : `p = ${cell.p_value.toFixed(3)}`)
    : 'p = n/a'

  return (
    <div style={{ borderBottom: '1px solid var(--border)', padding: '16px 0' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--text-3)', paddingTop: 2, minWidth: 16 }} className="stat">
          {String(index + 1).padStart(2, '0')}
        </span>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
            <p style={{ fontWeight: 500, fontSize: '0.9375rem', color: 'var(--text-1)', margin: 0 }}>
              <span style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>{cell.sector_a_code}</span>
              {' '}
              <span style={{ color: 'var(--text-3)' }}>{isPos ? 'leads' : 'inversely leads'}</span>
              {' '}
              <span style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>{cell.sector_b_code}</span>
            </p>
            <span style={{ fontSize: '0.75rem', fontWeight: 500, color: strength.color, padding: '1px 7px', borderRadius: 3, border: `1px solid ${strength.color}`, opacity: 0.85 }}>
              {strength.label}
            </span>
          </div>

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: '0.8125rem', color: 'var(--text-3)', fontFamily: 'monospace' }} className="stat">
            <span>r = {cell.correlation > 0 ? '+' : ''}{cell.correlation.toFixed(2)}</span>
            <span>{pLabel}</span>
            <span>lag = {lagHuman(cell.lag_days)}</span>
            <span>{cell.window_days}d window</span>
          </div>

          {expanded && (
            <div style={{ marginTop: 12, padding: '10px 12px', borderRadius: 6, background: 'var(--bg-2)', fontSize: '0.8125rem', color: 'var(--text-2)', lineHeight: 1.6 }}>
              <p style={{ margin: '0 0 6px', fontWeight: 500, color: 'var(--text-1)' }}>
                {cell.sector_a_name} × {cell.sector_b_name}
              </p>
              <p style={{ margin: '0 0 4px' }}>
                Method: Pearson correlation on daily close prices.
                {cell.lag_days > 0 && ` Optimal lag of ${cell.lag_days} days found by shifting the series and maximising |r|.`}
              </p>
              <p style={{ margin: 0, color: 'var(--text-3)', fontFamily: 'monospace', fontSize: '0.75rem' }} className="stat">
                r = {cell.correlation.toFixed(4)} · {pLabel} · lag = {cell.lag_days}d · n ≈ {cell.window_days} obs · method = Pearson
              </p>
            </div>
          )}

          <button
            onClick={() => setExpanded(e => !e)}
            style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--accent)', background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}
          >
            {expanded ? '↑ Less' : '↓ Details'}
          </button>
        </div>
      </div>
    </div>
  )
}

export function SignalFeed() {
  const { data, isLoading } = useCorrelationMatrix('pearson')

  const signals = data?.cells
    .filter(c => c.is_significant && c.lag_days > 0)
    .sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation))
    .slice(0, 5) ?? []

  return (
    <section>
      <p style={{ fontSize: '0.6875rem', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-3)', marginBottom: 4 }}>
        Signal Feed
      </p>

      {isLoading && (
        <div style={{ paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[1, 2, 3].map(i => (
            <div key={i} className="animate-pulse" style={{ height: 60, borderRadius: 4, background: 'var(--bg-3)' }} />
          ))}
        </div>
      )}

      {!isLoading && !signals.length && (
        <p style={{ paddingTop: 16, color: 'var(--text-3)', fontSize: '0.875rem' }}>
          No significant signals yet — correlations update daily at 05:00 UTC.
        </p>
      )}

      {signals.map((cell, i) => (
        <SignalCard key={`${cell.sector_a_code}-${cell.sector_b_code}`} cell={cell} index={i} />
      ))}
    </section>
  )
}

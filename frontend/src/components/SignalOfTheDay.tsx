import { useCorrelationMatrix } from '../hooks/useCorrelationMatrix'
import type { HeatmapCell } from '../types/correlation'

function pickTop(cells: HeatmapCell[]): HeatmapCell | null {
  const candidates = cells.filter(c => c.is_significant && c.lag_days > 0)
  if (!candidates.length) return null
  return candidates.reduce((best, c) =>
    Math.abs(c.correlation) > Math.abs(best.correlation) ? c : best
  )
}

function strengthLabel(r: number): string {
  const abs = Math.abs(r)
  if (abs >= 0.7) return 'strongly'
  if (abs >= 0.5) return 'moderately'
  return 'weakly'
}

function lagHuman(days: number): string {
  const w = Math.round(days / 7)
  return w <= 1 ? `${days} days` : `${w} weeks`
}

function buildNarrative(c: HeatmapCell): string {
  const dir    = c.correlation > 0 ? 'leads' : 'inversely leads'
  const str    = strengthLabel(c.correlation)
  const lag    = lagHuman(c.lag_days)
  const window = c.window_days
  return `${c.sector_a_name} ${str} ${dir} ${c.sector_b_name} by ${lag}. `
       + `This relationship has been statistically significant over a rolling ${window}-day window.`
}

const sectionBase: React.CSSProperties = {
  borderBottom: '1px solid var(--border)',
  padding: '32px 0 28px',
}

const primaryLabel: React.CSSProperties = {
  fontSize: '0.8125rem',
  fontWeight: 600,
  color: 'var(--text-1)',
  borderLeft: '2px solid var(--accent)',
  paddingLeft: 10,
  marginBottom: 16,
}

export function SignalOfTheDay() {
  const { data, isLoading } = useCorrelationMatrix('pearson')

  if (isLoading || !data) {
    return (
      <section style={sectionBase}>
        <div style={{ maxWidth: '72ch' }}>
          <div className="animate-pulse" style={{ height: 12, width: 80, borderRadius: 4, background: 'var(--bg-3)', marginBottom: 16 }} />
          <div className="animate-pulse" style={{ height: 20, borderRadius: 4, background: 'var(--bg-3)', marginBottom: 8 }} />
          <div className="animate-pulse" style={{ height: 20, width: '75%', borderRadius: 4, background: 'var(--bg-3)' }} />
        </div>
      </section>
    )
  }

  const top = pickTop(data.cells)

  if (!top) {
    const lastRun = data.computed_at
      ? `Last computed ${new Date(data.computed_at).toUTCString()}`
      : null

    return (
      <section style={sectionBase}>
        <p style={primaryLabel}>Top Signal</p>
        <p style={{ color: 'var(--text-3)', fontSize: '0.9375rem', marginBottom: lastRun ? 6 : 10 }}>
          No significant signals yet.
        </p>
        {lastRun
          ? <p style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>{lastRun}</p>
          : <button
              onClick={() => document.getElementById('admin')?.scrollIntoView({ behavior: 'smooth' })}
              style={{ fontSize: '0.8125rem', color: 'var(--accent)', background: 'none', border: 'none', padding: 0, cursor: 'pointer', textDecoration: 'underline', textUnderlineOffset: 3 }}
            >
              Run pipeline →
            </button>
        }
      </section>
    )
  }

  const isPos      = top.correlation > 0
  const accentCol  = isPos ? 'var(--pos)' : 'var(--neg)'
  const accentBg   = isPos ? 'var(--pos-bg)' : 'var(--neg-bg)'
  const pLabel     = top.p_value != null
    ? (top.p_value < 0.001 ? 'p < 0.001' : `p = ${top.p_value.toFixed(3)}`)
    : null

  return (
    <section style={sectionBase}>
      <p style={primaryLabel}>Top Signal</p>

      <p style={{ fontSize: '1.1875rem', lineHeight: 1.6, color: 'var(--text-1)', maxWidth: '68ch', marginBottom: 16 }}>
        {buildNarrative(top)}
      </p>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '3px 10px', borderRadius: 4, background: accentBg, color: accentCol, fontSize: '0.8125rem', fontFamily: 'monospace' }} className="stat">
          {top.sector_a_code} → {top.sector_b_code}
        </span>
        <span style={{ color: 'var(--text-3)', fontSize: '0.8125rem', fontFamily: 'monospace' }} className="stat">
          r = {top.correlation > 0 ? '+' : ''}{top.correlation.toFixed(2)}
        </span>
        <span style={{ color: 'var(--text-3)', fontSize: '0.8125rem' }}>·</span>
        <span style={{ color: 'var(--text-3)', fontSize: '0.8125rem', fontFamily: 'monospace' }} className="stat">
          lag = {top.lag_days}d
        </span>
        {pLabel && <>
          <span style={{ color: 'var(--text-3)', fontSize: '0.8125rem' }}>·</span>
          <span style={{ color: 'var(--text-3)', fontSize: '0.8125rem', fontFamily: 'monospace' }} className="stat">
            {pLabel}
          </span>
        </>}
        <span style={{ color: 'var(--text-3)', fontSize: '0.8125rem' }}>·</span>
        <span style={{ color: 'var(--text-3)', fontSize: '0.8125rem', fontFamily: 'monospace' }} className="stat">
          {top.window_days}d window
        </span>
      </div>

      {data.computed_at && (
        <p style={{ marginTop: 12, fontSize: '0.75rem', color: 'var(--text-3)' }}>
          Updated {new Date(data.computed_at).toUTCString()}
        </p>
      )}
    </section>
  )
}

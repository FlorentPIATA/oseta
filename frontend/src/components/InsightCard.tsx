import { useCorrelationMatrix } from '../hooks/useCorrelationMatrix'
import type { HeatmapCell } from '../types/correlation'

function pickTopInsight(cells: HeatmapCell[]): HeatmapCell | null {
  const candidates = cells.filter(c => c.is_significant && c.lag_days > 0)
  if (candidates.length === 0) return null
  return candidates.reduce((best, c) =>
    Math.abs(c.correlation) > Math.abs(best.correlation) ? c : best
  )
}

function directionLabel(r: number): string {
  return r > 0 ? 'positively leads' : 'negatively leads'
}

export function InsightCard() {
  const { data, isLoading } = useCorrelationMatrix('pearson')

  if (isLoading || !data) return null

  const top = pickTopInsight(data.cells)

  if (!top) {
    return (
      <div className="rounded-xl border border-gray-800 bg-gray-900 px-6 py-4 text-sm text-gray-500">
        Correlations updating — check back after 05:00 UTC
      </div>
    )
  }

  const absR = Math.abs(top.correlation).toFixed(2)
  const pLabel = top.p_value !== null && top.p_value !== undefined
    ? `p=${top.p_value.toExponential(1)}`
    : null

  return (
    <div className="rounded-xl border border-blue-900/50 bg-blue-950/30 px-6 py-4">
      <p className="text-xs font-semibold uppercase tracking-widest text-blue-400 mb-2">
        Top Signal
      </p>
      <p className="text-white text-sm leading-relaxed">
        <span className="font-mono font-bold text-blue-300">{top.sector_a_name}</span>
        {' '}{directionLabel(top.correlation)}{' '}
        <span className="font-mono font-bold text-blue-300">{top.sector_b_name}</span>
        {' '}by{' '}
        <span className="font-mono font-bold text-white">{top.lag_days} days</span>
        {' '}
        <span className="text-gray-400">
          (r={absR}
          {pLabel && `, ${pLabel}`}
          , {top.window_days}d window)
        </span>
      </p>
      {data.computed_at && (
        <p className="mt-2 text-xs text-gray-600">
          Last computed: {new Date(data.computed_at).toUTCString()}
        </p>
      )}
    </div>
  )
}

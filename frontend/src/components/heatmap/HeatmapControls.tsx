import type { MatrixFilters, CorrelationMethod } from '../../types/correlation'

interface Props {
  filters: MatrixFilters
  onChange: (f: MatrixFilters) => void
  computedAt: string | null
}

export function HeatmapControls({ filters, onChange, computedAt }: Props) {
  const set = <K extends keyof MatrixFilters>(key: K, value: MatrixFilters[K]) =>
    onChange({ ...filters, [key]: value })

  const formattedAt = computedAt
    ? new Date(computedAt).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
    : 'No data yet'

  return (
    <div className="flex flex-wrap items-center gap-6 px-6 py-4 bg-gray-900 border border-gray-800 rounded-xl">
      {/* Method toggle */}
      <div className="flex flex-col gap-1">
        <span className="text-xs text-gray-400 uppercase tracking-wider">Method</span>
        <div className="flex rounded-lg overflow-hidden border border-gray-700">
          {(['pearson', 'spearman'] as CorrelationMethod[]).map(m => (
            <button
              key={m}
              onClick={() => set('method', m)}
              className={[
                'px-4 py-1.5 text-sm font-medium transition-colors',
                filters.method === m
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700',
              ].join(' ')}
            >
              {m.charAt(0).toUpperCase() + m.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Min correlation slider */}
      <div className="flex flex-col gap-1 min-w-[160px]">
        <span className="text-xs text-gray-400 uppercase tracking-wider">
          Min |r| &nbsp;
          <span className="text-white font-mono">{filters.minCorrelation.toFixed(2)}</span>
        </span>
        <input
          type="range" min={0} max={1} step={0.05}
          value={filters.minCorrelation}
          onChange={e => set('minCorrelation', parseFloat(e.target.value))}
          className="accent-blue-500 w-full"
        />
      </div>

      {/* Lag slider */}
      <div className="flex flex-col gap-1 min-w-[160px]">
        <span className="text-xs text-gray-400 uppercase tracking-wider">
          Max lag &nbsp;
          <span className="text-white font-mono">{filters.lagMax}d</span>
        </span>
        <input
          type="range" min={0} max={60} step={5}
          value={filters.lagMax}
          onChange={e => set('lagMax', parseInt(e.target.value, 10))}
          className="accent-blue-500 w-full"
        />
      </div>

      {/* Last computed */}
      <div className="ml-auto flex flex-col items-end gap-0.5">
        <span className="text-xs text-gray-500 uppercase tracking-wider">Last computed</span>
        <span className="text-sm text-gray-300 font-mono">{formattedAt}</span>
      </div>
    </div>
  )
}

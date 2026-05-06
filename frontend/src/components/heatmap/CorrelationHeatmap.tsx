import { useState } from 'react'
import type { HeatmapCell, MatrixFilters } from '../../types/correlation'
import { useCorrelationMatrix, buildMatrixLookup } from '../../hooks/useCorrelationMatrix'
import { HeatmapControls } from './HeatmapControls'

const CELL_SIZE = 64

function corrToStyle(value: number): { background: string; color: string } {
  const abs = Math.abs(value)
  if (abs < 0.05) return { background: 'hsl(220 15% 18%)', color: '#9ca3af' }
  const hue = value > 0 ? 142 : 0
  const sat = Math.round(abs * 70)
  const light = Math.round(20 + abs * 22)
  return { background: `hsl(${hue} ${sat}% ${light}%)`, color: abs > 0.5 ? '#fff' : '#d1d5db' }
}

interface TooltipState {
  cell: HeatmapCell
  x: number
  y: number
}

interface CellProps {
  cell: HeatmapCell | undefined
  rowCode: string
  colCode: string
  onHover: (t: TooltipState | null, e?: React.MouseEvent) => void
}

function MatrixCell({ cell, rowCode, colCode, onHover }: CellProps) {
  if (rowCode === colCode) {
    return (
      <div
        style={{ width: CELL_SIZE, height: CELL_SIZE }}
        className="flex items-center justify-center bg-gray-800 rounded font-mono text-xs font-bold text-blue-400"
      >
        {rowCode}
      </div>
    )
  }

  if (!cell) {
    return (
      <div
        style={{ width: CELL_SIZE, height: CELL_SIZE }}
        className="rounded bg-gray-900 opacity-30"
      />
    )
  }

  const { background, color } = corrToStyle(cell.correlation)
  return (
    <div
      style={{ width: CELL_SIZE, height: CELL_SIZE, background, color }}
      className="rounded flex flex-col items-center justify-center cursor-pointer transition-opacity hover:opacity-80"
      onMouseEnter={e => onHover({ cell, x: e.clientX, y: e.clientY }, e)}
      onMouseLeave={() => onHover(null)}
    >
      <span className="font-mono text-sm font-semibold">{cell.correlation.toFixed(2)}</span>
      {cell.lag_days > 0 && (
        <span className="text-[10px] opacity-75">{cell.lag_days}d lag</span>
      )}
    </div>
  )
}

function Tooltip({ state }: { state: TooltipState }) {
  const { cell, x, y } = state
  return (
    <div
      className="fixed z-50 pointer-events-none bg-gray-800 border border-gray-600 rounded-lg p-3 text-sm shadow-xl"
      style={{ left: x + 14, top: y - 10 }}
    >
      <p className="font-semibold text-white mb-1">
        {cell.sector_a_name} → {cell.sector_b_name}
      </p>
      <p className="text-gray-300">r = <span className="font-mono text-white">{cell.correlation.toFixed(4)}</span></p>
      {cell.p_value !== null && (
        <p className="text-gray-300">p = <span className="font-mono text-white">{cell.p_value.toFixed(4)}</span>{cell.is_significant && ' ✓'}</p>
      )}
      <p className="text-gray-300">lag = <span className="font-mono text-white">{cell.lag_days} days</span></p>
      <p className="text-gray-300">window = <span className="font-mono text-white">{cell.window_days}d</span></p>
    </div>
  )
}

export function CorrelationHeatmap() {
  const [filters, setFilters] = useState<MatrixFilters>({
    method: 'pearson',
    minCorrelation: 0,
    lagMax: 60,
  })
  const [tooltip, setTooltip] = useState<TooltipState | null>(null)

  const { data, isLoading, isError } = useCorrelationMatrix(filters.method)
  const matrix = buildMatrixLookup(data?.cells ?? [], filters.minCorrelation, filters.lagMax)
  const sectors = data?.sectors ?? []

  return (
    <div className="flex flex-col gap-4">
      <HeatmapControls
        filters={filters}
        onChange={setFilters}
        computedAt={data?.computed_at ?? null}
      />

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 overflow-auto">
        {isLoading && (
          <div className="flex items-center justify-center h-64 text-gray-400">
            Loading correlation matrix…
          </div>
        )}
        {isError && (
          <div className="flex items-center justify-center h-64 text-red-400">
            Failed to load data. Is the API running?
          </div>
        )}
        {!isLoading && !isError && sectors.length === 0 && (
          <div className="flex flex-col items-center justify-center h-64 gap-2 text-gray-500">
            <p>No correlation data yet.</p>
            <p className="text-sm">Run the correlation job or POST /correlations/refresh</p>
          </div>
        )}

        {sectors.length > 0 && (
          <div className="flex flex-col gap-1">
            {sectors.map(row => (
              <div key={row} className="flex gap-1">
                {sectors.map(col => (
                  <MatrixCell
                    key={col}
                    cell={matrix.get(`${row}|${col}`)}
                    rowCode={row}
                    colCode={col}
                    onHover={(t) => setTooltip(t)}
                  />
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Color legend */}
      {sectors.length > 0 && (
        <div className="flex items-center gap-3 px-2">
          <span className="text-xs text-gray-500">−1.0</span>
          <div className="h-2 flex-1 rounded" style={{
            background: 'linear-gradient(to right, hsl(0 70% 35%), hsl(220 15% 18%), hsl(142 70% 35%))'
          }} />
          <span className="text-xs text-gray-500">+1.0</span>
        </div>
      )}

      {tooltip && <Tooltip state={tooltip} />}
    </div>
  )
}

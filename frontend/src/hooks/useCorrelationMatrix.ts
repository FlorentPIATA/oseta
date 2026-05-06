import { useQuery } from '@tanstack/react-query'
import { fetchCorrelationMatrix } from '../api/correlations'
import type { CorrelationMethod, HeatmapCell, HeatmapResponse } from '../types/correlation'

const REFETCH_INTERVAL_MS = 5 * 60 * 1000  // 5 min

export function useCorrelationMatrix(method: CorrelationMethod) {
  return useQuery<HeatmapResponse>({
    queryKey: ['correlations', method],
    queryFn: () => fetchCorrelationMatrix(method),
    refetchInterval: REFETCH_INTERVAL_MS,
    staleTime: REFETCH_INTERVAL_MS,
  })
}

export function buildMatrixLookup(
  cells: HeatmapCell[],
  minCorrelation: number,
  lagMax: number,
): Map<string, HeatmapCell> {
  const map = new Map<string, HeatmapCell>()
  for (const cell of cells) {
    if (Math.abs(cell.correlation) < minCorrelation) continue
    if (cell.lag_days > lagMax) continue
    const key = `${cell.sector_a_code}|${cell.sector_b_code}`
    const keyRev = `${cell.sector_b_code}|${cell.sector_a_code}`
    map.set(key, cell)
    map.set(keyRev, cell)
  }
  return map
}

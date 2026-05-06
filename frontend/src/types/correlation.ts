export type CorrelationMethod = 'pearson' | 'spearman'

export interface HeatmapCell {
  sector_a_code: string
  sector_b_code: string
  sector_a_name: string
  sector_b_name: string
  correlation: number
  p_value: number | null
  lag_days: number
  is_significant: boolean
  window_days: number
}

export interface HeatmapResponse {
  sectors: string[]
  cells: HeatmapCell[]
  computed_at: string | null
  method: CorrelationMethod
  total_pairs: number
}

export interface MatrixFilters {
  method: CorrelationMethod
  minCorrelation: number
  lagMax: number
}

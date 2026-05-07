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

export interface PipelineStatus {
  status: 'idle' | 'running' | 'success' | 'error'
  step: 'fetching_etfs' | 'fetching_fred' | 'computing' | 'predicting' | null
  triggered_at: string | null
  finished_at: string | null
  etf_new: number | null
  fred_new: number | null
  computed: number | null
  skipped: number | null
  predictions: number | null
  error: string | null
}

export interface RefreshStartedResponse {
  status: 'started' | 'already_running'
  triggered_at: string | null
}

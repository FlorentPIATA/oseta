export type PredictionStatus = 'pending' | 'realized' | 'partial' | 'failed'

export interface Prediction {
  id: number
  sector_id: number
  sector_code: string | null
  linked_sector_id: number | null
  linked_sector_code: string | null
  prediction_type: string
  horizon_days: number
  confidence_score: number
  predicted_direction: string
  predicted_magnitude: string
  status: PredictionStatus
  realized_at: string | null
  created_at: string
}

export interface TrackRecord {
  total: number
  pending: number
  realized: number
  partial: number
  failed: number
  accuracy: number | null
}

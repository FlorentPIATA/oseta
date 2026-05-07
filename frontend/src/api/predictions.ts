import type { Prediction, TrackRecord } from '../types/predictions'

const BASE = import.meta.env.VITE_API_URL ?? ''

export async function fetchPredictions(limit = 10): Promise<Prediction[]> {
  const res = await fetch(`${BASE}/predictions?limit=${limit}`)
  if (!res.ok) throw new Error(`API ${res.status}`)
  return res.json() as Promise<Prediction[]>
}

export async function fetchTrackRecord(): Promise<TrackRecord> {
  const res = await fetch(`${BASE}/predictions/track-record`)
  if (!res.ok) throw new Error(`API ${res.status}`)
  return res.json() as Promise<TrackRecord>
}

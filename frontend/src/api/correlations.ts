import type { CorrelationMethod, HeatmapResponse } from '../types/correlation'

const BASE = import.meta.env.VITE_API_URL ?? ''

export async function fetchCorrelationMatrix(
  method: CorrelationMethod,
): Promise<HeatmapResponse> {
  const url = `${BASE}/correlations/matrix?method=${method}&lag_max=60`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json() as Promise<HeatmapResponse>
}

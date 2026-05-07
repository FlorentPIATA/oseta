import type {
  CorrelationMethod,
  HeatmapResponse,
  PipelineStatus,
  RefreshStartedResponse,
} from '../types/correlation'

const BASE = import.meta.env.VITE_API_URL ?? ''

export async function fetchCorrelationMatrix(
  method: CorrelationMethod,
): Promise<HeatmapResponse> {
  const url = `${BASE}/correlations/matrix?method=${method}&lag_max=60`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json() as Promise<HeatmapResponse>
}

export async function triggerRefresh(masterKey: string): Promise<RefreshStartedResponse> {
  const res = await fetch(`${BASE}/correlations/refresh`, {
    method: 'POST',
    headers: { 'X-Master-Key': masterKey },
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json() as Promise<RefreshStartedResponse>
}

export async function fetchPipelineStatus(masterKey: string): Promise<PipelineStatus> {
  const res = await fetch(`${BASE}/correlations/pipeline-status`, {
    headers: { 'X-Master-Key': masterKey },
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json() as Promise<PipelineStatus>
}

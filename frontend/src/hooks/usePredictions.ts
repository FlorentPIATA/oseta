import { useQuery } from '@tanstack/react-query'
import { fetchPredictions, fetchTrackRecord } from '../api/predictions'
import type { Prediction, TrackRecord } from '../types/predictions'

export function useTrackRecord() {
  return useQuery<TrackRecord>({
    queryKey: ['track-record'],
    queryFn: fetchTrackRecord,
    staleTime: 10 * 60 * 1000,
  })
}

export function usePredictions(limit = 10) {
  return useQuery<Prediction[]>({
    queryKey: ['predictions', limit],
    queryFn: () => fetchPredictions(limit),
    staleTime: 10 * 60 * 1000,
  })
}

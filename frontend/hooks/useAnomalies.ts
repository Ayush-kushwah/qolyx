import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '@/lib/api'
import { AnomalyFilters } from '@/types'
import { toast } from 'sonner'

export const anomalyKeys = {
  all: ['anomalies'] as const,
  lists: () => [...anomalyKeys.all, 'list'] as const,
  list: (filters: AnomalyFilters) => [...anomalyKeys.lists(), filters] as const,
  health: () => [...anomalyKeys.all, 'health'] as const,
  progress: () => [...anomalyKeys.all, 'progress'] as const,
}

/**
 * Hook to retrieve statistical anomalies list based on filters and pagination.
 */
export function useAnomalies(filters: AnomalyFilters) {
  return useQuery({
    queryKey: anomalyKeys.list(filters),
    queryFn: () => api.fetchAnomalies(filters),
    placeholderData: (previousData) => previousData,
  })
}

/**
 * Hook to retrieve pipeline anomaly baseline readiness status.
 */
export function useAnomalyHealth() {
  return useQuery({
    queryKey: anomalyKeys.health(),
    queryFn: () => api.fetchAnomalyHealth(),
  })
}

/**
 * Hook to retrieve anomaly baseline training progress.
 */
export function useBaselineProgress() {
  return useQuery({
    queryKey: anomalyKeys.progress(),
    queryFn: () => api.fetchBaselineProgress(),
    refetchInterval: 30000, // Poll every 30 seconds
  })
}


/**
 * Hook to submit operator feedback for detected anomalies.
 */
export function useSubmitAnomalyFeedback() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      detectionId,
      feedbackType,
      userNotes,
      createdBy
    }: {
      detectionId: string
      feedbackType: string
      userNotes?: string
      createdBy?: string
    }) => api.submitAnomalyFeedback(detectionId, feedbackType, userNotes, createdBy),
    onSuccess: () => {
      toast.success('Feedback submitted successfully.')
      queryClient.invalidateQueries({ queryKey: anomalyKeys.all })
    },
    onError: () => {
      toast.error('Failed to submit anomaly feedback.')
    }
  })
}

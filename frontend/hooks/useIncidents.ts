import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '@/lib/api'
import { IncidentFilters, Incident, IncidentComment, IncidentRCA } from '@/types'
import { toast } from 'sonner'

// Query keys constants
export const incidentKeys = {
  all: ['incidents'] as const,
  lists: () => [...incidentKeys.all, 'list'] as const,
  list: (filters: IncidentFilters) => [...incidentKeys.lists(), filters] as const,
  details: () => [...incidentKeys.all, 'detail'] as const,
  detail: (id: string) => [...incidentKeys.details(), id] as const,
  stats: (tableName?: string) => [...incidentKeys.all, 'stats', tableName || 'all'] as const,
  timeline: (id: string) => [...incidentKeys.all, 'timeline', id] as const,
  comments: (id: string) => [...incidentKeys.all, 'comments', id] as const,
  rca: (id: string) => [...incidentKeys.all, 'rca', id] as const,
}

/**
 * Hook to retrieve a paginated and filtered list of incidents.
 */
export function useIncidents(filters: IncidentFilters) {
  return useQuery({
    queryKey: incidentKeys.list(filters),
    queryFn: () => api.fetchIncidents(filters),
    placeholderData: (previousData) => previousData, // keep previous data while fetching new pages
  })
}

/**
 * Hook to retrieve auto-refreshing summary statistics for incidents.
 * Automatically refetches every 30 seconds.
 */
export function useIncidentStats(tableName?: string) {
  return useQuery({
    queryKey: incidentKeys.stats(tableName),
    queryFn: () => api.fetchIncidentStats(tableName),
    refetchInterval: 30000, // 30 seconds auto-refresh
  })
}

/**
 * Hook to retrieve complete detail of a single incident.
 */
export function useIncidentDetail(id: string) {
  const queryClient = useQueryClient()

  // Fetch base incident data
  const incidentQuery = useQuery({
    queryKey: incidentKeys.detail(id),
    queryFn: () => api.fetchIncidentDetail(id),
  })

  // Fetch timeline events
  const timelineQuery = useQuery({
    queryKey: incidentKeys.timeline(id),
    queryFn: () => api.fetchIncidentTimeline(id),
    enabled: !!id,
  })

  // Fetch comments
  const commentsQuery = useQuery({
    queryKey: incidentKeys.comments(id),
    queryFn: () => api.fetchIncidentComments(id),
    enabled: !!id,
  })

  // Fetch RCA
  const rcaQuery = useQuery({
    queryKey: incidentKeys.rca(id),
    queryFn: () => api.fetchIncidentRCA(id),
    enabled: !!id,
    retry: false, // Don't spam retries if RCA doesn't exist yet
  })

  return {
    incident: incidentQuery.data,
    timeline: timelineQuery.data || [],
    comments: commentsQuery.data || [],
    rca: rcaQuery.data,
    isLoading: incidentQuery.isLoading || timelineQuery.isLoading || commentsQuery.isLoading,
    isError: incidentQuery.isError,
    error: incidentQuery.error,
    refetchAll: () => {
      incidentQuery.refetch()
      timelineQuery.refetch()
      commentsQuery.refetch()
      rcaQuery.refetch()
    }
  }
}

/**
 * Hook to acknowledge an open incident with optimistic updates.
 */
export function useAcknowledgeIncident() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id }: { id: string }) => api.acknowledgeIncident(id),
    onMutate: async ({ id }) => {
      // Cancel outgoing queries so they don't overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey: incidentKeys.detail(id) })
      await queryClient.cancelQueries({ queryKey: incidentKeys.lists() })

      // Snapshot the previous state
      const previousIncident = queryClient.getQueryData<Incident>(incidentKeys.detail(id))

      // Optimistically update the detail view
      if (previousIncident) {
        queryClient.setQueryData<Incident>(incidentKeys.detail(id), {
          ...previousIncident,
          state: 'ACKNOWLEDGED',
          acknowledged_at: new Date().toISOString()
        })
      }

      return { previousIncident }
    },
    onError: (err, { id }, context) => {
      // Rollback to snapshot if mutation failed
      if (context?.previousIncident) {
        queryClient.setQueryData(incidentKeys.detail(id), context.previousIncident)
      }
      toast.error('Failed to acknowledge incident. Please try again.')
    },
    onSuccess: (data, { id }) => {
      toast.success('Incident acknowledged successfully.')
      // Invalidate queries to sync with actual database
      queryClient.invalidateQueries({ queryKey: incidentKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: incidentKeys.lists() })
      queryClient.invalidateQueries({ queryKey: incidentKeys.timeline(id) })
      queryClient.invalidateQueries({ queryKey: incidentKeys.all })
    }
  })
}

/**
 * Hook to update an incident (e.g. change assignee or assigned team).
 */
export function useUpdateIncident() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { assigned_to?: string | null; assigned_team?: string | null } }) =>
      api.updateIncident(id, data),
    onSuccess: (data, { id }) => {
      toast.success('Incident updated successfully.')
      queryClient.invalidateQueries({ queryKey: incidentKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: incidentKeys.lists() })
      queryClient.invalidateQueries({ queryKey: incidentKeys.all })
    },
    onError: () => {
      toast.error('Failed to update incident.')
    }
  })
}

/**
 * Hook to resolve an incident with resolution notes and optimistic updates.
 */
export function useResolveIncident() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, resolutionNotes }: { id: string; resolutionNotes: string }) =>
      api.resolveIncident(id, resolutionNotes),
    onMutate: async ({ id, resolutionNotes }) => {
      await queryClient.cancelQueries({ queryKey: incidentKeys.detail(id) })
      await queryClient.cancelQueries({ queryKey: incidentKeys.lists() })

      const previousIncident = queryClient.getQueryData<Incident>(incidentKeys.detail(id))

      if (previousIncident) {
        queryClient.setQueryData<Incident>(incidentKeys.detail(id), {
          ...previousIncident,
          state: 'RESOLVED',
          resolution_notes: resolutionNotes,
          resolved_at: new Date().toISOString()
        })
      }

      return { previousIncident }
    },
    onError: (err, { id }, context) => {
      if (context?.previousIncident) {
        queryClient.setQueryData(incidentKeys.detail(id), context.previousIncident)
      }
      toast.error('Failed to resolve incident. Please try again.')
    },
    onSuccess: (data, { id }) => {
      toast.success('Incident resolved successfully.')
      queryClient.invalidateQueries({ queryKey: incidentKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: incidentKeys.lists() })
      queryClient.invalidateQueries({ queryKey: incidentKeys.timeline(id) })
      queryClient.invalidateQueries({ queryKey: incidentKeys.all })
    }
  })
}

/**
 * Hook to close a resolved incident.
 */
export function useCloseIncident() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id }: { id: string }) => api.closeIncident(id),
    onSuccess: (data, { id }) => {
      toast.success('Incident closed successfully.')
      queryClient.invalidateQueries({ queryKey: incidentKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: incidentKeys.lists() })
      queryClient.invalidateQueries({ queryKey: incidentKeys.timeline(id) })
      queryClient.invalidateQueries({ queryKey: incidentKeys.all })
    },
    onError: () => {
      toast.error('Failed to close incident.')
    }
  })
}

/**
 * Hook to reopen a resolved or closed incident.
 */
export function useReopenIncident() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id }: { id: string }) => api.reopenIncident(id),
    onSuccess: (data, { id }) => {
      toast.success('Incident reopened successfully.')
      queryClient.invalidateQueries({ queryKey: incidentKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: incidentKeys.lists() })
      queryClient.invalidateQueries({ queryKey: incidentKeys.timeline(id) })
      queryClient.invalidateQueries({ queryKey: incidentKeys.all })
    },
    onError: () => {
      toast.error('Failed to reopen incident.')
    }
  })
}

/**
 * Hook to append a comment to an incident with optimistic updates.
 */
export function useAddIncidentComment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, comment, createdBy }: { id: string; comment: string; createdBy: string }) =>
      api.addIncidentComment(id, comment, createdBy),
    onMutate: async ({ id, comment, createdBy }) => {
      await queryClient.cancelQueries({ queryKey: incidentKeys.comments(id) })

      const previousComments = queryClient.getQueryData<IncidentComment[]>(incidentKeys.comments(id)) || []

      const optimisticComment: IncidentComment = {
        id: Math.random().toString(), // temporary ID
        incident_id: id,
        comment,
        created_by: createdBy,
        created_at: new Date().toISOString()
      }

      queryClient.setQueryData<IncidentComment[]>(incidentKeys.comments(id), [
        ...previousComments,
        optimisticComment
      ])

      return { previousComments }
    },
    onError: (err, { id }, context) => {
      if (context?.previousComments) {
        queryClient.setQueryData(incidentKeys.comments(id), context.previousComments)
      }
      toast.error('Failed to add comment.')
    },
    onSuccess: (data, { id }) => {
      queryClient.invalidateQueries({ queryKey: incidentKeys.comments(id) })
      queryClient.invalidateQueries({ queryKey: incidentKeys.timeline(id) })
    }
  })
}

/**
 * Hook to manually trigger regeneration of the RCA.
 */
export function useRegenerateRCA() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id }: { id: string }) => api.regenerateRCA(id),
    onMutate: () => {
      toast.info('Regenerating Root Cause Analysis... please wait.')
    },
    onSuccess: (data, { id }) => {
      toast.success('Root Cause Analysis regenerated successfully.')
      queryClient.setQueryData<IncidentRCA>(incidentKeys.rca(id), data)
      queryClient.invalidateQueries({ queryKey: incidentKeys.rca(id) })
      queryClient.invalidateQueries({ queryKey: incidentKeys.timeline(id) })
    },
    onError: () => {
      toast.error('Failed to regenerate Root Cause Analysis.')
    }
  })
}

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '@/lib/api'
import { EscalationPolicyCreate } from '@/types'
import { toast } from 'sonner'

export const escalationKeys = {
  all: ['escalationPolicies'] as const,
}

/**
 * Hook to retrieve all configured escalation policies.
 */
export function useEscalationPolicies() {
  return useQuery({
    queryKey: escalationKeys.all,
    queryFn: () => api.fetchEscalationPolicies(),
  })
}

/**
 * Hook to create a new escalation routing policy.
 */
export function useCreateEscalationPolicy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: EscalationPolicyCreate) => api.createEscalationPolicy(data),
    onSuccess: () => {
      toast.success('Escalation Policy created successfully.')
      queryClient.invalidateQueries({ queryKey: escalationKeys.all })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to create Escalation Policy.')
    }
  })
}

/**
 * Hook to manually trigger a sweep of open incidents against escalation policies.
 */
export function useCheckEscalations() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => api.checkEscalations(),
    onSuccess: (data) => {
      toast.success(`Escalation sweep finished. ${data.escalated_count} incident(s) escalated.`)
      // Invalidate both incidents and escalation policies
      queryClient.invalidateQueries({ queryKey: ['incidents'] })
      queryClient.invalidateQueries({ queryKey: escalationKeys.all })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to trigger escalation sweep.')
    }
  })
}

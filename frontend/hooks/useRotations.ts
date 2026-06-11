import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '@/lib/api'
import { OncallRotationCreate } from '@/types'
import { toast } from 'sonner'

export const rotationKeys = {
  all: ['rotations'] as const,
}

/**
 * Hook to retrieve all on-call rotation schedules.
 */
export function useRotations() {
  return useQuery({
    queryKey: rotationKeys.all,
    queryFn: () => api.fetchRotations(),
  })
}

/**
 * Hook to create a new on-call rotation schedule.
 */
export function useCreateRotation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: OncallRotationCreate) => api.createRotation(data),
    onSuccess: () => {
      toast.success('On-call Rotation created successfully.')
      queryClient.invalidateQueries({ queryKey: rotationKeys.all })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to create On-call Rotation.')
    }
  })
}

/**
 * Hook to manually rotate the rotation schedule to the next active developer.
 */
export function useRotateRotation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.rotateRotation(id),
    onSuccess: (data) => {
      toast.success(`Schedule rotated. Current on-call: ${data.members[data.current_index]}.`)
      queryClient.invalidateQueries({ queryKey: rotationKeys.all })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to manually rotate schedule.')
    }
  })
}

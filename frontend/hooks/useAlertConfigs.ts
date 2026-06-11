import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '@/lib/api'
import { AlertConfigCreate, AlertConfigUpdate } from '@/types'
import { toast } from 'sonner'

export const alertConfigKeys = {
  all: ['alertConfigs'] as const,
  ntfyTopic: ['ntfyTopic'] as const,
  ntfyQRCode: ['ntfyQRCode'] as const,
}

/**
 * Hook to retrieve all alert channel configurations.
 */
export function useAlertConfigs() {
  return useQuery({
    queryKey: alertConfigKeys.all,
    queryFn: () => api.fetchAlertConfigs(),
  })
}

/**
 * Hook to create a new alert configuration channel.
 */
export function useCreateAlertConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: AlertConfigCreate) => api.createAlertConfig(data),
    onSuccess: () => {
      toast.success('Alert configuration created successfully.')
      queryClient.invalidateQueries({ queryKey: alertConfigKeys.all })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to create alert configuration.')
    }
  })
}

/**
 * Hook to update an existing alert configuration.
 */
export function useUpdateAlertConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AlertConfigUpdate }) => api.updateAlertConfig(id, data),
    onSuccess: () => {
      toast.success('Alert configuration updated successfully.')
      queryClient.invalidateQueries({ queryKey: alertConfigKeys.all })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to update alert configuration.')
    }
  })
}

/**
 * Hook to delete an alert configuration.
 */
export function useDeleteAlertConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.deleteAlertConfig(id),
    onSuccess: () => {
      toast.success('Alert configuration deleted successfully.')
      queryClient.invalidateQueries({ queryKey: alertConfigKeys.all })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to delete alert configuration.')
    }
  })
}

/**
 * Hook to send a manual test alert to verify an active channel integration.
 */
export function useTestAlertConfig() {
  return useMutation({
    mutationFn: ({ channelType, message }: { channelType: string; message: string }) =>
      api.testAlertConfig(channelType, message),
    onSuccess: (data, variables) => {
      if (data.sent) {
        toast.success(`Test alert dispatched successfully to ${variables.channelType}.`)
      } else {
        toast.error(`Test alert failed to dispatch: ${data.status}`)
      }
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to send test alert.')
    }
  })
}

/**
 * Hook to retrieve the default system Ntfy topic metadata.
 */
export function useNtfyTopic() {
  return useQuery({
    queryKey: alertConfigKeys.ntfyTopic,
    queryFn: () => api.fetchNtfyTopic(),
  })
}

/**
 * Hook to generate the default system Ntfy topic QR code image.
 */
export function useNtfyQRCode() {
  return useQuery({
    queryKey: alertConfigKeys.ntfyQRCode,
    queryFn: () => api.fetchNtfyQRCode(),
  })
}

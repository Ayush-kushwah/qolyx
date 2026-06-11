import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '@/lib/api'
import { AppSettingsUpdate, ApiKeyCreateRequest, IntegrationConnectionRequest } from '@/types'
import { toast } from 'sonner'

export const settingsKeys = {
  settings: ['settings'] as const,
  apiKeys: ['settings', 'apiKeys'] as const,
  integrations: ['settings', 'integrations'] as const,
}

export function useSettings() {
  return useQuery({
    queryKey: settingsKeys.settings,
    queryFn: () => api.fetchAppSettings(),
  })
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: AppSettingsUpdate) => api.updateAppSettings(data),
    onSuccess: () => {
      toast.success('System settings updated successfully.')
      queryClient.invalidateQueries({ queryKey: settingsKeys.settings })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to update system settings.')
    }
  })
}

export function useApiKeys() {
  return useQuery({
    queryKey: settingsKeys.apiKeys,
    queryFn: () => api.fetchApiKeys(),
  })
}

export function useCreateApiKey() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: ApiKeyCreateRequest) => api.createApiKey(data),
    onSuccess: () => {
      toast.success('API Key generated successfully.')
      queryClient.invalidateQueries({ queryKey: settingsKeys.apiKeys })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to generate API Key.')
    }
  })
}

export function useRevokeApiKey() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.revokeApiKey(id),
    onSuccess: () => {
      toast.success('API Key revoked successfully.')
      queryClient.invalidateQueries({ queryKey: settingsKeys.apiKeys })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to revoke API Key.')
    }
  })
}

export function useIntegrations() {
  return useQuery({
    queryKey: settingsKeys.integrations,
    queryFn: () => api.fetchIntegrations(),
  })
}

export function useCreateIntegration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: IntegrationConnectionRequest) => api.createOrUpdateIntegration(data),
    onSuccess: () => {
      toast.success('Integration connection saved successfully.')
      queryClient.invalidateQueries({ queryKey: settingsKeys.integrations })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to save integration connection.')
    }
  })
}

export function useDeleteIntegration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteIntegration(id),
    onSuccess: () => {
      toast.success('Integration connection removed successfully.')
      queryClient.invalidateQueries({ queryKey: settingsKeys.integrations })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to remove integration connection.')
    }
  })
}

export function useTestIntegration() {
  return useMutation({
    mutationFn: (data: IntegrationConnectionRequest) => api.testIntegration(data),
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message || 'Connectivity check succeeded!')
      } else {
        toast.error(data.message || 'Connectivity check failed.')
      }
    },
    onError: (err: any) => {
      toast.error(err.message || 'Error occurred during connectivity check.')
    }
  })
}

export function useSyncIntegration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.syncIntegration(id),
    onSuccess: (data) => {
      toast.success(data.message || 'Integration assets synchronized successfully.')
      queryClient.invalidateQueries({ queryKey: settingsKeys.integrations })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to sync integration assets.')
    }
  })
}

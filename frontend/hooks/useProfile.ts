import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '@/lib/api'
import { UserProfileUpdate, ChangePasswordRequest } from '@/types'
import { toast } from 'sonner'

export const profileKeys = {
  profile: ['profile'] as const,
  sessions: ['profile', 'sessions'] as const,
  loginHistory: ['profile', 'loginHistory'] as const,
}

export function useProfile() {
  return useQuery({
    queryKey: profileKeys.profile,
    queryFn: () => api.fetchProfile(),
  })
}

export function useUpdateProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: UserProfileUpdate) => api.updateProfile(data),
    onSuccess: () => {
      toast.success('Profile settings updated successfully.')
      queryClient.invalidateQueries({ queryKey: profileKeys.profile })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to update profile settings.')
    }
  })
}

export function useUploadAvatar() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => api.uploadAvatar(file),
    onSuccess: (data) => {
      toast.success('Avatar image uploaded successfully.')
      queryClient.invalidateQueries({ queryKey: profileKeys.profile })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to upload avatar image.')
    }
  })
}

export function useDeleteAvatar() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.deleteAvatar(),
    onSuccess: () => {
      toast.success('Avatar image removed.')
      queryClient.invalidateQueries({ queryKey: profileKeys.profile })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to remove avatar image.')
    }
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (data: ChangePasswordRequest) => api.changePassword(data),
    onSuccess: () => {
      toast.success('Account password updated successfully.')
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to update account password.')
    }
  })
}

export function useSessions() {
  return useQuery({
    queryKey: profileKeys.sessions,
    queryFn: () => api.fetchSessions(),
  })
}

export function useRevokeSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.revokeSession(id),
    onSuccess: () => {
      toast.success('Login session revoked successfully.')
      queryClient.invalidateQueries({ queryKey: profileKeys.sessions })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to revoke login session.')
    }
  })
}

export function useRevokeAllSessions() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.revokeAllSessions(),
    onSuccess: () => {
      toast.success('All other login sessions revoked successfully.')
      queryClient.invalidateQueries({ queryKey: profileKeys.sessions })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to revoke login sessions.')
    }
  })
}

export function useLoginHistory() {
  return useQuery({
    queryKey: profileKeys.loginHistory,
    queryFn: () => api.fetchLoginHistory(),
  })
}

export function useRequestDataExport() {
  return useMutation({
    mutationFn: () => api.exportUserData(),
    onSuccess: (data) => {
      // Trigger a browser download of the exported JSON payload
      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(data, null, 2))
      const downloadAnchor = document.createElement('a')
      downloadAnchor.setAttribute('href', dataStr)
      downloadAnchor.setAttribute('download', `qolyx_profile_export_${new Date().toISOString().slice(0, 10)}.json`)
      document.body.appendChild(downloadAnchor)
      downloadAnchor.click()
      downloadAnchor.remove()
      toast.success('User account data compiled and download initiated.')
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to export account data.')
    }
  })
}

export function useDeleteAccount() {
  return useMutation({
    mutationFn: () => api.deleteAccount(),
    onSuccess: () => {
      toast.success('Account termination successfully processed.')
      // In a real app, redirect to register/login
      window.location.href = '/'
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to terminate account.')
    }
  })
}

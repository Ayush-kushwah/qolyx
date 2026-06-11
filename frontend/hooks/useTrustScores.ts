import { useQuery } from '@tanstack/react-query'
import * as api from '@/lib/api'

export const trustScoreKeys = {
  all: ['trustScores'] as const,
  histories: () => [...trustScoreKeys.all, 'history'] as const,
  history: (tableName: string, page: number, pageSize: number) =>
    [...trustScoreKeys.histories(), tableName, page, pageSize] as const,
  trends: () => [...trustScoreKeys.all, 'trend'] as const,
  trend: (tableName: string, days: number) => [...trustScoreKeys.trends(), tableName, days] as const,
  health: () => [...trustScoreKeys.all, 'health'] as const,
}

/**
 * Hook to retrieve trust score history records for a table with pagination.
 */
export function useTrustScoreHistory(tableName: string, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: trustScoreKeys.history(tableName, page, pageSize),
    queryFn: () => api.fetchTrustScoreHistory(tableName, page, pageSize),
    enabled: !!tableName,
  })
}

/**
 * Hook to retrieve trust score trend items for charting.
 * Sorts them chronologically (oldest to newest).
 */
export function useTrustScoreTrend(tableName: string, days = 30) {
  return useQuery({
    queryKey: trustScoreKeys.trend(tableName, days),
    queryFn: async () => {
      const data = await api.fetchTrustScoreHistory(tableName, 1, days)
      return [...data.items].reverse()
    },
    enabled: !!tableName,
  })
}

/**
 * Hook to check the general health of the trust scoring API.
 */
export function useTrustScoreHealth() {
  return useQuery({
    queryKey: trustScoreKeys.health(),
    queryFn: () => api.fetchTrustScoreHealth(),
  })
}

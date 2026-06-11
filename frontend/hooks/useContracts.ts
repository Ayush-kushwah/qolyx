import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '@/lib/api'
import { ContractCreate, ContractUpdate } from '@/types'
import { toast } from 'sonner'

export const contractKeys = {
  all: ['contracts'] as const,
}

/**
 * Hook to retrieve all data contracts.
 */
export function useContracts() {
  return useQuery({
    queryKey: contractKeys.all,
    queryFn: () => api.fetchContracts(),
  })
}

/**
 * Hook to create a new data contract manually.
 */
export function useCreateContract() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ContractCreate) => api.createContract(data),
    onSuccess: () => {
      toast.success('Data Contract created successfully.')
      queryClient.invalidateQueries({ queryKey: contractKeys.all })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to create Data Contract.')
    }
  })
}

/**
 * Hook to generate a draft contract schema definition from an existing table structure.
 */
export function useGenerateContract() {
  return useMutation({
    mutationFn: ({ tableName, name }: { tableName: string; name: string }) =>
      api.generateContractFromTable(tableName, name),
    onSuccess: () => {
      toast.success('Data Contract proposal generated successfully.')
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to generate Data Contract proposal.')
    }
  })
}

/**
 * Hook to update a data contract name, schema, or status.
 */
export function useUpdateContract() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ContractUpdate }) => api.updateContract(id, data),
    onSuccess: () => {
      toast.success('Data Contract updated successfully.')
      queryClient.invalidateQueries({ queryKey: contractKeys.all })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to update Data Contract.')
    }
  })
}

/**
 * Hook to delete a data contract from database.
 */
export function useDeleteContract() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.deleteContract(id),
    onSuccess: () => {
      toast.success('Data Contract deleted successfully.')
      queryClient.invalidateQueries({ queryKey: contractKeys.all })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to delete Data Contract.')
    }
  })
}

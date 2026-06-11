import { create } from 'zustand'

interface IncidentFilterState {
  severityFilter: string[] | null
  stateFilter: string[] | null
  tableNameFilter: string | null
  page: number
  pageSize: number
  setSeverityFilter: (severity: string[] | null) => void
  setStateFilter: (state: string[] | null) => void
  setTableNameFilter: (tableName: string | null) => void
  setPage: (page: number) => void
  setPageSize: (pageSize: number) => void
  resetFilters: () => void
}

export const useIncidentFilterStore = create<IncidentFilterState>((set) => ({
  severityFilter: null,
  stateFilter: null,
  tableNameFilter: null,
  page: 1,
  pageSize: 20,
  setSeverityFilter: (severityFilter) => set({ severityFilter, page: 1 }),
  setStateFilter: (stateFilter) => set({ stateFilter, page: 1 }),
  setTableNameFilter: (tableNameFilter) => set({ tableNameFilter, page: 1 }),
  setPage: (page) => set({ page }),
  setPageSize: (pageSize) => set({ pageSize, page: 1 }),
  resetFilters: () => set({
    severityFilter: null,
    stateFilter: null,
    tableNameFilter: null,
    page: 1,
    pageSize: 20
  })
}))

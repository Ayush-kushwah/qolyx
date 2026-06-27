'use client'

import React from 'react'
import Link from 'next/link'
import { format } from 'date-fns'
import { 
  useIncidents, 
  useIncidentStats, 
  useAcknowledgeIncident 
} from '@/hooks/useIncidents'
import { useIncidentFilterStore } from '@/store/incidentFilterStore'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorBoundary from '@/components/common/ErrorBoundary'
import EmptyState from '@/components/common/EmptyState'
import { 
  ShieldAlert, 
  RotateCcw, 
  Check, 
  Eye, 
  ChevronLeft, 
  ChevronRight, 
  AlertCircle,
  Clock,
  User,
  Filter,
  CheckCircle2,
  AlertTriangle,
  FileSpreadsheet
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const TABLES = [
  { id: 'all', label: 'All Tables' },
  { id: 'bronze_financial_candles', label: 'Financial Candles' },
  { id: 'bronze_fda_events', label: 'FDA Events' },
  { id: 'bronze_github_events', label: 'GitHub Events' }
]

export default function IncidentsPage() {
  const {
    severityFilter,
    stateFilter,
    tableNameFilter,
    page,
    pageSize,
    setSeverityFilter,
    setStateFilter,
    setTableNameFilter,
    setPage,
    setPageSize,
    resetFilters
  } = useIncidentFilterStore()

  // Map Zustand filters to API format
  const queryFilters = {
    severity: severityFilter && severityFilter.length > 0 ? severityFilter[0] : null,
    state: stateFilter && stateFilter.length > 0 ? stateFilter[0] : null,
    table_name: tableNameFilter === 'all' ? null : tableNameFilter,
    page,
    page_size: pageSize
  }

  // API queries & mutations
  const statsQuery = useIncidentStats(tableNameFilter === 'all' ? undefined : tableNameFilter || undefined)
  const incidentsQuery = useIncidents(queryFilters)
  const acknowledgeMutation = useAcknowledgeIncident()

  const getSeverityBadge = (sev: string) => {
    switch (sev.toUpperCase()) {
      case 'CRITICAL':
        return <Badge variant="outline" className="bg-critical/10 text-critical border-critical/20 uppercase text-[10px] font-bold tracking-wider">Critical</Badge>
      case 'HIGH':
        return <Badge variant="outline" className="bg-degraded/10 text-degraded border-degraded/20 uppercase text-[10px] font-bold tracking-wider">High</Badge>
      case 'MEDIUM':
        return <Badge variant="outline" className="bg-warning/10 text-warning border-warning/20 uppercase text-[10px] font-bold tracking-wider">Medium</Badge>
      default:
        return <Badge variant="outline" className="bg-muted text-muted-foreground border-border uppercase text-[10px] font-bold tracking-wider">Low</Badge>
    }
  }

  const getStateBadge = (state: string) => {
    switch (state.toUpperCase()) {
      case 'OPEN':
        return (
          <span className="flex items-center gap-1.5 text-xs text-critical font-bold">
            <span className="h-1.5 w-1.5 rounded-full bg-critical animate-ping" />
            Open
          </span>
        )
      case 'ACKNOWLEDGED':
        return (
          <span className="flex items-center gap-1.5 text-xs text-warning font-bold">
            <span className="h-1.5 w-1.5 rounded-full bg-warning" />
            Acknowledged
          </span>
        )
      case 'RESOLVED':
        return (
          <span className="flex items-center gap-1.5 text-xs text-healthy font-bold">
            <span className="h-1.5 w-1.5 rounded-full bg-healthy" />
            Resolved
          </span>
        )
      case 'CLOSED':
        return (
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground font-bold">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
            Closed
          </span>
        )
      default:
        return <span className="text-xs text-muted-foreground font-bold">{state}</span>
    }
  }

  const handleAcknowledge = (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    acknowledgeMutation.mutate({ id })
  }

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= (incidentsQuery.data?.pages ?? 1)) {
      setPage(newPage)
    }
  }

  const handleSeverityChange = (value: string) => {
    setSeverityFilter(value === 'all' ? null : [value])
  }

  const handleStateChange = (value: string) => {
    setStateFilter(value === 'all' ? null : [value])
  }

  const handleTableChange = (value: string) => {
    setTableNameFilter(value === 'all' ? null : value)
  }

  const totalPages = incidentsQuery.data?.pages ?? 1
  const totalItems = incidentsQuery.data?.total ?? 0
  const currentStart = (page - 1) * pageSize + 1
  const currentEnd = Math.min(page * pageSize, totalItems)

  const isLoading = incidentsQuery.isLoading || statsQuery.isLoading

  return (
    <ErrorBoundary>
      <div className="space-y-4 select-none font-sans text-foreground">
        
        {/* Title / Action Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
          <div className="space-y-0.5">
            <h1 className="text-xl md:text-2xl font-bold tracking-tight bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-400 bg-clip-text text-transparent flex items-center gap-2">
              <ShieldAlert className="h-6 w-6 text-critical" />
              Incident Command Center
            </h1>
            <p className="text-xs text-muted-foreground">
              Acknowledge, resolve, and audit pipeline data reliability breaches and SLA alerts.
            </p>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
          {/* Card 1: Open */}
          <div className="glass-panel p-4 rounded-xl flex items-center justify-between bg-card border border-border relative overflow-hidden group">
            <div className="space-y-1">
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Open Incidents</div>
              <div className="text-xl font-bold text-foreground">{statsQuery.data?.total_open ?? 0}</div>
            </div>
            <div className="p-2 rounded-lg bg-critical/10 border border-critical/20">
              <AlertCircle className="h-4 w-4 text-critical" />
            </div>
          </div>

          {/* Card 2: Acknowledged */}
          <div className="glass-panel p-4 rounded-xl flex items-center justify-between bg-card border border-border relative overflow-hidden group">
            <div className="space-y-1">
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Acknowledged</div>
              <div className="text-xl font-bold text-foreground">{statsQuery.data?.total_acknowledged ?? 0}</div>
            </div>
            <div className="p-2 rounded-lg bg-warning/10 border border-warning/20">
              <Clock className="h-4 w-4 text-warning" />
            </div>
          </div>

          {/* Card 3: Resolved */}
          <div className="glass-panel p-4 rounded-xl flex items-center justify-between bg-card border border-border relative overflow-hidden group">
            <div className="space-y-1">
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Resolved (Live)</div>
              <div className="text-xl font-bold text-foreground">{statsQuery.data?.total_resolved ?? 0}</div>
            </div>
            <div className="p-2 rounded-lg bg-healthy/10 border border-healthy/20">
              <CheckCircle2 className="h-4 w-4 text-healthy" />
            </div>
          </div>

          {/* Card 4: Closed */}
          <div className="glass-panel p-4 rounded-xl flex items-center justify-between bg-card border border-border relative overflow-hidden group">
            <div className="space-y-1">
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Closed Archive</div>
              <div className="text-xl font-bold text-foreground">{statsQuery.data?.total_closed ?? 0}</div>
            </div>
            <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 border border-border">
              <Check className="h-4 w-4 text-muted-foreground" />
            </div>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="glass-panel p-4 rounded-xl bg-card border border-border space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground uppercase tracking-wider">
              <Filter className="h-3.5 w-3.5 text-primary" />
              Filter Feed
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={resetFilters}
              className="text-muted-foreground border-border hover:bg-muted hover:text-foreground text-xs font-semibold gap-1 self-end sm:self-center h-8 bg-card"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset Filters
            </Button>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            {/* Table Selector */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Data Table</label>
              <Select value={tableNameFilter || 'all'} onValueChange={handleTableChange}>
                <SelectTrigger className="bg-background border-border text-foreground h-9 font-medium text-xs">
                  <SelectValue placeholder="Select Data Table" />
                </SelectTrigger>
                <SelectContent className="bg-card border-border text-foreground">
                  {TABLES.map((t) => (
                    <SelectItem key={t.id} value={t.id} className="text-xs">
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Severity Selector */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Severity Level</label>
              <Select value={severityFilter?.[0] || 'all'} onValueChange={handleSeverityChange}>
                <SelectTrigger className="bg-background border-border text-foreground h-9 font-medium text-xs">
                  <SelectValue placeholder="Select Severity" />
                </SelectTrigger>
                <SelectContent className="bg-card border-border text-foreground">
                  <SelectItem value="all" className="text-xs">All Severities</SelectItem>
                  <SelectItem value="CRITICAL" className="text-xs">Critical</SelectItem>
                  <SelectItem value="HIGH" className="text-xs">High</SelectItem>
                  <SelectItem value="MEDIUM" className="text-xs">Medium</SelectItem>
                  <SelectItem value="LOW" className="text-xs">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* State Selector */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Incident State</label>
              <Select value={stateFilter?.[0] || 'all'} onValueChange={handleStateChange}>
                <SelectTrigger className="bg-background border-border text-foreground h-9 font-medium text-xs">
                  <SelectValue placeholder="Select State" />
                </SelectTrigger>
                <SelectContent className="bg-card border-border text-foreground">
                  <SelectItem value="all" className="text-xs">All States</SelectItem>
                  <SelectItem value="OPEN" className="text-xs">Open</SelectItem>
                  <SelectItem value="ACKNOWLEDGED" className="text-xs">Acknowledged</SelectItem>
                  <SelectItem value="RESOLVED" className="text-xs">Resolved</SelectItem>
                  <SelectItem value="CLOSED" className="text-xs">Closed</SelectItem>
                  <SelectItem value="REOPENED" className="text-xs">Reopened</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {/* Content Area */}
        <div className="glass-panel rounded-xl border border-border bg-card overflow-hidden">
          {isLoading ? (
            <div className="py-16">
              <LoadingSpinner text="Retrieving Active Incident Feed..." />
            </div>
          ) : incidentsQuery.isError ? (
            <div className="py-12 px-6">
              <EmptyState
                 title="Error Loading Incidents"
                 description={incidentsQuery.error instanceof Error ? incidentsQuery.error.message : 'Failed to retrieve incident logs.'}
                 icon={AlertTriangle}
                 action={{
                   label: "Retry",
                   onClick: () => incidentsQuery.refetch()
                 }}
              />
            </div>
          ) : !incidentsQuery.data?.items || incidentsQuery.data.items.length === 0 ? (
            <div className="py-16 px-6">
              <EmptyState
                title="No Incidents Found"
                description="No pipeline breaches match the currently selected filter options."
                icon={CheckCircle2}
                action={{
                  label: "Reset Filters",
                  onClick: resetFilters
                }}
              />
            </div>
          ) : (
            <div>
              {/* Desktop view */}
              <div className="hidden md:block">
                <Table>
                  <TableHeader className="bg-muted/50 border-b border-border">
                    <TableRow className="border-b border-border hover:bg-transparent">
                      <TableHead className="text-muted-foreground font-semibold text-[10px] uppercase py-3 pl-6">Title</TableHead>
                      <TableHead className="text-muted-foreground font-semibold text-[10px] uppercase py-3">Severity</TableHead>
                      <TableHead className="text-muted-foreground font-semibold text-[10px] uppercase py-3">Target Table</TableHead>
                      <TableHead className="text-muted-foreground font-semibold text-[10px] uppercase py-3">State</TableHead>
                      <TableHead className="text-muted-foreground font-semibold text-[10px] uppercase py-3">Owner</TableHead>
                      <TableHead className="text-muted-foreground font-semibold text-[10px] uppercase py-3">Logged Time</TableHead>
                      <TableHead className="text-muted-foreground font-semibold text-[10px] uppercase py-3 text-right pr-6">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody className="divide-y divide-border text-xs text-foreground">
                    {incidentsQuery.data.items.map((incident) => (
                      <TableRow 
                        key={incident.id}
                        className="border-b border-border hover:bg-muted/50 transition-colors cursor-pointer group"
                      >
                        <TableCell className="py-3 pl-6 font-semibold text-foreground group-hover:text-primary transition-colors max-w-[280px] truncate">
                          <Link href={`/incidents/${incident.id}`} className="block">
                            {incident.title}
                          </Link>
                        </TableCell>
                        <TableCell className="py-3">
                          <Link href={`/incidents/${incident.id}`} className="block">
                            {getSeverityBadge(incident.severity)}
                          </Link>
                        </TableCell>
                        <TableCell className="py-3 font-mono text-[10px] text-muted-foreground">
                          <Link href={`/incidents/${incident.id}`} className="block">
                            {incident.table_name}
                          </Link>
                        </TableCell>
                        <TableCell className="py-3">
                          <Link href={`/incidents/${incident.id}`} className="block">
                            {getStateBadge(incident.state)}
                          </Link>
                        </TableCell>
                        <TableCell className="py-3 font-medium text-muted-foreground">
                          <Link href={`/incidents/${incident.id}`} className="block">
                            <span className="flex items-center gap-1.5">
                              <User className="h-3.5 w-3.5 text-muted-foreground/80" />
                              {incident.assigned_to || 'Unassigned'}
                            </span>
                          </Link>
                        </TableCell>
                        <TableCell className="py-3 font-mono text-[10px] text-muted-foreground">
                          <Link href={`/incidents/${incident.id}`} className="block">
                            {format(new Date(incident.created_at), 'yyyy-MM-dd HH:mm')}
                          </Link>
                        </TableCell>
                        <TableCell className="py-3 pr-6 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end gap-2">
                            {incident.state.toUpperCase() === 'OPEN' && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={(e) => handleAcknowledge(incident.id, e)}
                                disabled={acknowledgeMutation.isPending}
                                className="h-7 px-2.5 bg-warning/10 text-warning border-warning/20 hover:bg-warning hover:text-black font-bold text-[10px] uppercase gap-1"
                              >
                                {acknowledgeMutation.isPending ? 'Acking...' : 'Acknowledge'}
                              </Button>
                            )}
                            <Link href={`/incidents/${incident.id}`}>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 w-7 p-0 border-border text-muted-foreground hover:text-foreground hover:bg-muted bg-card"
                              >
                                <Eye className="h-3.5 w-3.5" />
                              </Button>
                            </Link>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Mobile View */}
              <div className="md:hidden divide-y divide-border">
                {incidentsQuery.data.items.map((incident) => (
                  <div 
                    key={incident.id} 
                    className="p-4 space-y-3 hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <Link href={`/incidents/${incident.id}`} className="block space-y-1 flex-1">
                        <div className="font-semibold text-foreground hover:text-primary transition-colors text-sm">
                          {incident.title}
                        </div>
                        <div className="text-[10px] font-mono text-muted-foreground">
                          {incident.table_name}
                        </div>
                      </Link>
                      <div>
                        {getSeverityBadge(incident.severity)}
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                      <div className="flex items-center gap-1.5">
                        {getStateBadge(incident.state)}
                        <span className="text-muted-foreground/60">•</span>
                        <span className="flex items-center gap-1">
                          <User className="h-3 w-3 text-muted-foreground/75" />
                          {incident.assigned_to || 'Unassigned'}
                        </span>
                      </div>
                      <div className="font-mono text-[10px]">
                        {format(new Date(incident.created_at), 'MM-dd HH:mm')}
                      </div>
                    </div>

                    <div className="flex items-center justify-end gap-2 pt-1">
                      {incident.state.toUpperCase() === 'OPEN' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={(e) => handleAcknowledge(incident.id, e)}
                          disabled={acknowledgeMutation.isPending}
                          className="h-7 px-3 bg-warning/10 text-warning border-warning/20 hover:bg-warning hover:text-black font-bold text-[10px] uppercase"
                        >
                          Acknowledge
                        </Button>
                      )}
                      <Link href={`/incidents/${incident.id}`} className="flex-1 max-w-[80px]">
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 w-full border-border text-muted-foreground hover:text-foreground text-[10px] uppercase font-bold bg-card"
                        >
                          View Details
                        </Button>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination bar */}
              <div className="flex flex-col sm:flex-row items-center justify-between border-t border-border p-4 md:p-6 gap-4">
                <div className="text-xs text-muted-foreground font-medium">
                  Showing <span className="text-foreground font-bold">{currentStart}</span> to{' '}
                  <span className="text-foreground font-bold">{currentEnd}</span> of{' '}
                  <span className="text-foreground font-bold">{totalItems}</span> incidents
                </div>

                <div className="flex items-center gap-4">
                  {/* Page size selector */}
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider font-sans">Page size</span>
                    <Select
                      value={String(pageSize)}
                      onValueChange={(val) => setPageSize(Number(val))}
                    >
                      <SelectTrigger className="w-16 bg-background border-border text-foreground h-8 font-bold text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-card border-border text-foreground min-w-[64px]">
                        <SelectItem value="10" className="text-xs font-semibold">10</SelectItem>
                        <SelectItem value="20" className="text-xs font-semibold">20</SelectItem>
                        <SelectItem value="50" className="text-xs font-semibold">50</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Nav buttons */}
                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => handlePageChange(page - 1)}
                      disabled={page === 1}
                      className="h-8 w-8 border-border text-muted-foreground hover:text-foreground hover:bg-muted bg-card disabled:opacity-30"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <div className="text-xs font-bold text-foreground px-2 select-none">
                      Page {page} of {totalPages}
                    </div>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => handlePageChange(page + 1)}
                      disabled={page === totalPages}
                      className="h-8 w-8 border-border text-muted-foreground hover:text-foreground hover:bg-muted bg-card disabled:opacity-30"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

      </div>
    </ErrorBoundary>
  )
}

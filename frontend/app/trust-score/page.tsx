'use client'

import React, { useState } from 'react'
import { format } from 'date-fns'
import { 
  useTrustScoreHistory, 
  useTrustScoreTrend 
} from '@/hooks/useTrustScores'
import TrustScoreTrend from '@/components/trust-score/TrustScoreTrend'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorBoundary from '@/components/common/ErrorBoundary'
import EmptyState from '@/components/common/EmptyState'
import { 
  TrendingUp,
  RotateCcw,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Download,
  Info,
  Calendar,
  CheckCircle2,
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
import { toast } from 'sonner'

const TABLES = [
  { id: 'bronze_financial_candles', label: 'Financial Candles (Finnhub)' },
  { id: 'bronze_fda_events', label: 'FDA events (Scraper)' },
  { id: 'bronze_github_events', label: 'GitHub Events (Webhooks)' }
]

export default function TrustScoreHistoryPage() {
  const [selectedTable, setSelectedTable] = useState(TABLES[0].id)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  // API Queries
  const historyQuery = useTrustScoreHistory(selectedTable, page, pageSize)
  const trendQuery = useTrustScoreTrend(selectedTable, 30)

  // CSV Exporter
  const handleExportCsv = () => {
    const items = historyQuery.data?.items || []
    if (items.length === 0) {
      toast.error('No history records available to export.')
      return
    }

    try {
      const headers = [
        'Pipeline Run ID',
        'Table Name',
        'Trust Score',
        'Status',
        'Contract Penalty',
        'Freshness Penalty',
        'Volume Penalty',
        'Anomaly Penalty',
        'DBT Penalty',
        'Total Penalty',
        'Created At'
      ]

      const rows = items.map((item) => [
        `"${item.pipeline_run_id}"`,
        `"${item.table_name}"`,
        item.trust_score,
        `"${item.trust_score_status}"`,
        item.contract_penalty,
        item.freshness_penalty,
        item.volume_penalty,
        item.anomaly_penalty,
        item.dbt_penalty,
        item.total_penalty,
        `"${format(new Date(item.created_at), 'yyyy-MM-dd HH:mm:ss')}"`
      ])

      const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.setAttribute('href', url)
      link.setAttribute('download', `qolyx_${selectedTable}_history_${format(new Date(), 'yyyyMMdd_HHmmss')}.csv`)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      toast.success('History logs exported successfully as CSV.')
    } catch {
      toast.error('Failed to export CSV. Please try again.')
    }
  }

  const handleTableChange = (value: string) => {
    setSelectedTable(value)
    setPage(1)
  }

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= (historyQuery.data?.pages ?? 1)) {
      setPage(newPage)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'HEALTHY':
        return <Badge variant="outline" className="bg-healthy/10 text-healthy border-healthy/20 uppercase text-[9px] font-bold">Healthy</Badge>
      case 'WARNING':
        return <Badge variant="outline" className="bg-warning/10 text-warning border-warning/20 uppercase text-[9px] font-bold">Warning</Badge>
      case 'DEGRADED':
        return <Badge variant="outline" className="bg-degraded/10 text-degraded border-degraded/20 uppercase text-[9px] font-bold">Degraded</Badge>
      default:
        return <Badge variant="outline" className="bg-critical/10 text-critical border-critical/20 uppercase text-[9px] font-bold">Critical</Badge>
    }
  }

  const totalPages = historyQuery.data?.pages ?? 1
  const totalItems = historyQuery.data?.total ?? 0
  const currentStart = (page - 1) * pageSize + 1
  const currentEnd = Math.min(page * pageSize, totalItems)

  const isLoading = historyQuery.isLoading || trendQuery.isLoading

  return (
    <ErrorBoundary>
      <div className="space-y-8 select-none">
        
        {/* Header section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-400 bg-clip-text text-transparent flex items-center gap-2">
              <TrendingUp className="h-7 w-7 text-primary" />
              Dataset Trust Scores
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Verify multi-dimensional scoring trends and audit individual pipeline execution runs.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            {/* Table Selector */}
            <Select value={selectedTable} onValueChange={handleTableChange}>
              <SelectTrigger className="w-full sm:w-64 bg-background border-border text-foreground h-9 font-medium text-xs rounded-lg">
                <SelectValue placeholder="Select Data Table" />
              </SelectTrigger>
              <SelectContent className="bg-popover border-border text-popover-foreground">
                {TABLES.map((t) => (
                  <SelectItem key={t.id} value={t.id} className="text-xs cursor-pointer focus:bg-accent focus:text-accent-foreground">
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* CSV Export Button */}
            <Button
              onClick={handleExportCsv}
              disabled={isLoading || totalItems === 0}
              className="bg-primary hover:bg-emerald-600 text-white font-bold text-xs h-9 rounded-lg gap-1.5 uppercase self-start sm:self-center"
            >
              <Download className="h-4 w-4" />
              Export CSV
            </Button>
          </div>
        </div>

        {/* Trend Chart Panel */}
        <div className="glass-panel p-6 rounded-xl flex flex-col justify-between min-h-[360px] bg-card border border-border">
          <div className="border-b border-border pb-4 space-y-1">
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              Quality Score History Trend
            </h3>
            <p className="text-[11px] text-muted-foreground">
              Score changes across the last 30 execution pipelines (threshold set to 70)
            </p>
          </div>
          
          <div className="flex-1 py-4">
            {trendQuery.isLoading ? (
              <div className="h-full flex items-center justify-center py-20">
                <LoadingSpinner text="Computing Scoring Trends..." />
              </div>
            ) : (
              <TrustScoreTrend data={trendQuery.data || []} />
            )}
          </div>
        </div>

        {/* Table / Audit Log Panel */}
        <div className="glass-panel rounded-xl overflow-hidden bg-card border border-border">
          <div className="p-4 md:p-6 border-b border-border space-y-1 bg-muted/20">
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              Forensic Audit Logs
            </h3>
            <p className="text-[11px] text-muted-foreground">
              Details of individual pipeline runs and metric category deductions
            </p>
          </div>

          {historyQuery.isLoading ? (
            <div className="py-24">
              <LoadingSpinner text="Loading Historical Scoring Records..." />
            </div>
          ) : historyQuery.isError ? (
            <div className="py-12 px-6">
              <EmptyState
                title="Error Loading Histories"
                description={historyQuery.error instanceof Error ? historyQuery.error.message : 'Failed to retrieve scoring histories.'}
                icon={AlertTriangle}
                action={{
                  label: "Retry",
                  onClick: () => historyQuery.refetch()
                }}
              />
            </div>
          ) : !historyQuery.data?.items || historyQuery.data.items.length === 0 ? (
            <div className="py-16 px-6">
              <EmptyState
                title="No Scoring Histories"
                description="No execution runs have been logged for this database table yet."
                icon={CheckCircle2}
              />
            </div>
          ) : (
            <div>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader className="bg-muted/40 border-b border-border">
                    <TableRow className="border-b border-border hover:bg-transparent">
                      <TableHead className="text-muted-foreground font-bold text-[10px] uppercase py-3.5 pl-6">Pipeline Run ID</TableHead>
                      <TableHead className="text-muted-foreground font-bold text-[10px] uppercase py-3.5">Score</TableHead>
                      <TableHead className="text-muted-foreground font-bold text-[10px] uppercase py-3.5">Status</TableHead>
                      <TableHead className="text-muted-foreground font-bold text-[10px] uppercase py-3.5">Schema Penalty</TableHead>
                      <TableHead className="text-muted-foreground font-bold text-[10px] uppercase py-3.5">Freshness Penalty</TableHead>
                      <TableHead className="text-muted-foreground font-bold text-[10px] uppercase py-3.5">Volume Penalty</TableHead>
                      <TableHead className="text-muted-foreground font-bold text-[10px] uppercase py-3.5">ML Penalty</TableHead>
                      <TableHead className="text-muted-foreground font-bold text-[10px] uppercase py-3.5">dbt Penalty</TableHead>
                      <TableHead className="text-muted-foreground font-bold text-[10px] uppercase py-3.5">Total Deductions</TableHead>
                      <TableHead className="text-muted-foreground font-bold text-[10px] uppercase py-3.5 pr-6 text-right">Executed At</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody className="divide-y divide-border text-xs text-foreground">
                    {historyQuery.data.items.map((item) => (
                      <TableRow 
                        key={item.id}
                        className="border-b border-border hover:bg-muted/50 transition-colors"
                      >
                        <TableCell className="py-3.5 pl-6 font-mono text-[10px] text-muted-foreground max-w-[150px] truncate">
                          {item.pipeline_run_id}
                        </TableCell>
                        <TableCell className="py-3.5 font-bold text-foreground text-sm">
                          {item.trust_score}%
                        </TableCell>
                        <TableCell className="py-3.5">
                          {getStatusBadge(item.trust_score_status)}
                        </TableCell>
                        <TableCell className={`py-3.5 font-semibold ${item.contract_penalty > 0 ? 'text-rose-500 dark:text-rose-400' : 'text-muted-foreground'}`}>
                          -{item.contract_penalty}
                        </TableCell>
                        <TableCell className={`py-3.5 font-semibold ${item.freshness_penalty > 0 ? 'text-rose-500 dark:text-rose-400' : 'text-muted-foreground'}`}>
                          -{item.freshness_penalty}
                        </TableCell>
                        <TableCell className={`py-3.5 font-semibold ${item.volume_penalty > 0 ? 'text-rose-500 dark:text-rose-400' : 'text-muted-foreground'}`}>
                          -{item.volume_penalty}
                        </TableCell>
                        <TableCell className={`py-3.5 font-semibold ${item.anomaly_penalty > 0 ? 'text-rose-500 dark:text-rose-400' : 'text-muted-foreground'}`}>
                          -{item.anomaly_penalty}
                        </TableCell>
                        <TableCell className={`py-3.5 font-semibold ${item.dbt_penalty > 0 ? 'text-rose-500 dark:text-rose-400' : 'text-muted-foreground'}`}>
                          -{item.dbt_penalty}
                        </TableCell>
                        <TableCell className={`py-3.5 font-bold ${item.total_penalty > 0 ? 'text-rose-600 dark:text-rose-500' : 'text-muted-foreground'}`}>
                          -{item.total_penalty}
                        </TableCell>
                        <TableCell className="py-3.5 pr-6 text-right font-mono text-[10px] text-muted-foreground">
                          {format(new Date(item.created_at), 'yyyy-MM-dd HH:mm')}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination controls */}
              <div className="flex flex-col sm:flex-row items-center justify-between border-t border-border p-4 md:p-6 gap-4 bg-muted/20">
                <div className="text-xs text-muted-foreground font-medium">
                  Showing <span className="text-foreground font-bold">{currentStart}</span> to{' '}
                  <span className="text-foreground font-bold">{currentEnd}</span> of{' '}
                  <span className="text-foreground font-bold">{totalItems}</span> runs
                </div>

                <div className="flex items-center gap-4">
                  {/* Page size select */}
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Page size</span>
                    <Select
                      value={String(pageSize)}
                      onValueChange={(val) => {
                        setPageSize(Number(val))
                        setPage(1)
                      }}
                    >
                      <SelectTrigger className="w-16 bg-background border-border text-foreground h-8 font-bold text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-popover border-border text-popover-foreground min-w-[64px]">
                        <SelectItem value="10" className="text-xs font-semibold cursor-pointer">10</SelectItem>
                        <SelectItem value="20" className="text-xs font-semibold cursor-pointer">20</SelectItem>
                        <SelectItem value="50" className="text-xs font-semibold cursor-pointer">50</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Nav links */}
                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => handlePageChange(page - 1)}
                      disabled={page === 1}
                      className="h-8 w-8 border-border text-muted-foreground hover:bg-accent hover:text-accent-foreground disabled:opacity-30"
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
                      className="h-8 w-8 border-border text-muted-foreground hover:bg-accent hover:text-accent-foreground disabled:opacity-30"
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

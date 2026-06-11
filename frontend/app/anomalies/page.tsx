'use client'

import React, { useState } from 'react'
import { format } from 'date-fns'
import { 
  useAnomalies, 
  useSubmitAnomalyFeedback,
  useBaselineProgress
} from '@/hooks/useAnomalies'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ProgressBar from '@/components/common/ProgressBar'

import ErrorBoundary from '@/components/common/ErrorBoundary'
import EmptyState from '@/components/common/EmptyState'
import { 
  Activity,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Filter,
  RotateCcw,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Sparkles,
  ThumbsUp,
  ThumbsDown,
  BarChart4,
  Info
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
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ReferenceLine
} from 'recharts'

const TABLES = [
  { id: 'all', label: 'All Tables' },
  { id: 'bronze_financial_candles', label: 'Financial Candles' },
  { id: 'bronze_fda_events', label: 'FDA Events' },
  { id: 'bronze_github_events', label: 'GitHub Events' }
]

const ANOMALY_TYPES = [
  { id: 'all', label: 'All Types' },
  { id: 'freshness', label: 'Freshness Lag' },
  { id: 'volume', label: 'Volume Drift' },
  { id: 'schema', label: 'Schema Drift' },
  { id: 'null_rate', label: 'Null Rate Spike' }
]

export default function AnomaliesPage() {
  const [selectedTable, setSelectedTable] = useState('all')
  const [selectedType, setSelectedType] = useState('all')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({})

  // API Hooks
  const queryFilters = {
    table_name: selectedTable === 'all' ? null : selectedTable,
    page,
    page_size: pageSize
  }

  const { data, isLoading, isError, error, refetch } = useAnomalies(queryFilters)
  const progressQuery = useBaselineProgress()
  const feedbackMutation = useSubmitAnomalyFeedback()


  const handleTableChange = (value: string) => {
    setSelectedTable(value)
    setPage(1)
  }

  const handleTypeChange = (value: string) => {
    setSelectedType(value)
    setPage(1)
  }

  const resetFilters = () => {
    setSelectedTable('all')
    setSelectedType('all')
    setPage(1)
  }

  const toggleRow = (id: string) => {
    setExpandedRows(prev => ({
      ...prev,
      [id]: !prev[id]
    }))
  }

  const handleFeedback = (detectionId: string, feedbackType: 'acknowledged' | 'false_positive', e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    feedbackMutation.mutate({
      detectionId,
      feedbackType,
      userNotes: feedbackType === 'false_positive' ? 'Operator marked as false positive.' : 'Acknowledged by operator.'
    })
  }

  const getAnomalyTypeBadge = (type: string) => {
    const displayType = type.replace(/_/g, ' ').toUpperCase()
    if (type.toLowerCase().includes('freshness')) {
      return <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/20 text-[9px] font-bold uppercase">Freshness</Badge>
    }
    if (type.toLowerCase().includes('volume')) {
      return <Badge variant="outline" className="bg-indigo-500/10 text-indigo-400 border-indigo-500/20 text-[9px] font-bold uppercase">Volume</Badge>
    }
    if (type.toLowerCase().includes('schema')) {
      return <Badge variant="outline" className="bg-pink-500/10 text-pink-400 border-pink-500/20 text-[9px] font-bold uppercase">Schema</Badge>
    }
    return <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/20 text-[9px] font-bold uppercase">Null Rate</Badge>
  }

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= Math.ceil((data?.total || 0) / pageSize)) {
      setPage(newPage)
    }
  }

  // Client-side filtering for anomaly type since backend doesn't support it directly
  const rawDetections = data?.detections || []
  const filteredDetections = rawDetections.filter(d => {
    if (selectedType === 'all') return true
    return d.anomaly_type.toLowerCase().includes(selectedType.toLowerCase())
  })

  const totalItems = selectedType === 'all' ? (data?.total || 0) : filteredDetections.length
  const totalPages = selectedType === 'all' ? Math.ceil(totalItems / pageSize) : 1
  const currentStart = totalItems === 0 ? 0 : (page - 1) * pageSize + 1
  const currentEnd = Math.min(page * pageSize, totalItems)

  return (
    <ErrorBoundary>
      <div className="space-y-8 select-none">
        
        {/* Title */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-400 bg-clip-text text-transparent flex items-center gap-2">
              <Activity className="h-7 w-7 text-primary" />
              Statistical Anomalies
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Isolation Forest model predictions qualified with SHAP local feature importance explanations.
            </p>
          </div>
        </div>

        {/* Baseline Training Progress Section */}
        <div className="glass-panel p-6 rounded-xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-slate-900/20 space-y-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-slate-200">Baseline Training Progress</h3>
              <p className="text-[11px] text-slate-400 max-w-3xl leading-relaxed">
                Isolation Forest models require 7 historical pipeline execution runs to establish baseline parameters.
                Once 100% complete, active anomaly detection and enforcement is automatically enabled.
              </p>
            </div>
          </div>

          {progressQuery.isLoading ? (
            <div className="py-6 flex justify-center">
              <LoadingSpinner text="Retrieving baseline training progress..." />
            </div>
          ) : progressQuery.isError ? (
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400 flex items-center justify-between">
              <span>Failed to load baseline progress telemetry.</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => progressQuery.refetch()}
                className="h-7 text-xs font-bold hover:bg-red-500/20 hover:text-red-300"
              >
                Retry
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              {TABLES.filter(t => t.id !== 'all').map(table => {
                const progress = progressQuery.data?.[table.id as keyof typeof progressQuery.data] || {
                  runs_completed: 0,
                  runs_needed: 7,
                  is_ready: false,
                  estimated_minutes_remaining: 35
                }

                const percent = (progress.runs_completed / progress.runs_needed) * 100

                return (
                  <div
                    key={table.id}
                    className="bg-white dark:bg-slate-950/40 p-4 rounded-lg border border-slate-200 dark:border-white/5 space-y-3 flex flex-col justify-between hover:border-slate-300 dark:hover:border-slate-800/80 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs text-slate-350">{table.label}</span>
                      {progress.is_ready ? (
                        <Badge
                          variant="outline"
                          className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[9px] font-extrabold uppercase"
                        >
                          ACTIVE
                        </Badge>
                      ) : (
                        <Badge
                          variant="outline"
                          className="bg-amber-500/10 text-amber-400 border-amber-500/20 text-[9px] font-extrabold uppercase animate-pulse"
                        >
                          TUNING
                        </Badge>
                      )}
                    </div>

                    <ProgressBar
                      value={percent}
                      label={`${progress.runs_completed} / ${progress.runs_needed} runs completed`}
                      subtext={
                        progress.is_ready
                          ? 'Baseline established. Active anomaly detection enabled.'
                          : `${progress.runs_needed - progress.runs_completed} more runs needed • Est. ${progress.estimated_minutes_remaining}m remaining`
                      }
                      showPercentage={true}
                    />
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Filter bar */}
        <div className="glass-panel p-4 rounded-xl space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
              <Filter className="h-4 w-4 text-primary" />
              Filter Telemetry
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={resetFilters}
              className="text-slate-400 border-white/5 hover:bg-white/5 hover:text-white text-xs font-bold gap-1 self-end sm:self-center h-8"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset Filters
            </Button>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {/* Table Name */}
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Target Table</label>
              <Select value={selectedTable} onValueChange={handleTableChange}>
                <SelectTrigger className="bg-slate-950/40 border-white/5 text-slate-200 h-9 font-medium text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-white/10 text-slate-200">
                  {TABLES.map(t => (
                    <SelectItem key={t.id} value={t.id} className="text-xs">
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Anomaly Type */}
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Anomaly Type</label>
              <Select value={selectedType} onValueChange={handleTypeChange}>
                <SelectTrigger className="bg-slate-950/40 border-white/5 text-slate-200 h-9 font-medium text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-white/10 text-slate-200">
                  {ANOMALY_TYPES.map(t => (
                    <SelectItem key={t.id} value={t.id} className="text-xs">
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {/* Content list */}
        <div className="glass-panel rounded-xl overflow-hidden">
          {isLoading ? (
            <div className="py-24">
              <LoadingSpinner text="Retrieving Anomaly Logs..." />
            </div>
          ) : isError ? (
            <div className="py-12 px-6">
              <EmptyState
                title="Error Loading Anomalies"
                description={error instanceof Error ? error.message : 'Failed to retrieve baseline anomalies.'}
                icon={AlertTriangle}
                action={{
                  label: 'Retry',
                  onClick: () => refetch()
                }}
              />
            </div>
          ) : filteredDetections.length === 0 ? (
            <div className="py-16 px-6">
              <EmptyState
                title="No Anomalies Logged"
                description="All pipelines are running smoothly inside Isolation Forest baseline bounds."
                icon={CheckCircle2}
                action={{
                  label: 'Reset Filters',
                  onClick: resetFilters
                }}
              />
            </div>
          ) : (
            <div>
              <Table>
                <TableHeader className="bg-slate-50 dark:bg-slate-900/40 border-b border-slate-200 dark:border-white/5">
                  <TableRow className="border-b border-slate-200 dark:border-white/5 hover:bg-transparent">
                    <TableHead className="w-10 py-3.5 pl-6"></TableHead>
                    <TableHead className="text-slate-600 dark:text-slate-400 font-bold text-[10px] uppercase py-3.5">Detected At</TableHead>
                    <TableHead className="text-slate-600 dark:text-slate-400 font-bold text-[10px] uppercase py-3.5">Data Table</TableHead>
                    <TableHead className="text-slate-600 dark:text-slate-400 font-bold text-[10px] uppercase py-3.5">Type</TableHead>
                    <TableHead className="text-slate-600 dark:text-slate-400 font-bold text-[10px] uppercase py-3.5">Score</TableHead>
                    <TableHead className="text-slate-600 dark:text-slate-400 font-bold text-[10px] uppercase py-3.5">Penalty</TableHead>
                    <TableHead className="text-slate-600 dark:text-slate-400 font-bold text-[10px] uppercase py-3.5">State</TableHead>
                    <TableHead className="text-slate-600 dark:text-slate-400 font-bold text-[10px] uppercase py-3.5 text-right pr-6">Quick Feedback</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody className="divide-y divide-slate-200 dark:divide-white/5 text-xs text-slate-700 dark:text-slate-300">
                  {filteredDetections.map((anomaly) => {
                    const isExpanded = !!expandedRows[anomaly.id]
                    
                    // Parse SHAP chart data
                    const featureValues = anomaly.feature_values as any
                    const shapData = Object.entries(featureValues?.feature_importance || {})
                      .map(([key, val]) => ({
                        name: key.replace(/_/g, ' '),
                        value: Number(val),
                        abs: Math.abs(Number(val))
                      }))
                      .sort((a, b) => b.abs - a.abs)

                    return (
                      <React.Fragment key={anomaly.id}>
                        {/* Summary Row */}
                        <TableRow 
                          onClick={() => toggleRow(anomaly.id)}
                          className="border-b border-slate-200 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors cursor-pointer group"
                        >
                          <TableCell className="py-3.5 pl-6 text-slate-500 group-hover:text-primary transition-colors">
                            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </TableCell>
                          <TableCell className="py-3.5 font-mono text-[10px] text-slate-550 dark:text-slate-400">
                            {format(new Date(anomaly.created_at), 'yyyy-MM-dd HH:mm')}
                          </TableCell>
                          <TableCell className="py-3.5 font-mono text-[10px] font-semibold text-slate-800 dark:text-slate-200">
                            {anomaly.table_name}
                          </TableCell>
                          <TableCell className="py-3.5">
                            {getAnomalyTypeBadge(anomaly.anomaly_type)}
                          </TableCell>
                          <TableCell className="py-3.5">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-800 dark:text-slate-200">{(anomaly.anomaly_score * 100).toFixed(0)}%</span>
                              <div className="w-16 h-1.5 rounded-full bg-slate-900 overflow-hidden border border-white/5">
                                <div 
                                  className="h-full bg-gradient-to-r from-emerald-500 to-rose-500" 
                                  style={{ width: `${(anomaly.anomaly_score * 100).toFixed(0)}%` }}
                                />
                              </div>
                            </div>
                          </TableCell>
                          <TableCell className="py-3.5 font-bold text-rose-400">
                            -{anomaly.anomaly_penalty} pts
                          </TableCell>
                          <TableCell className="py-3.5">
                            {anomaly.is_false_positive ? (
                              <Badge variant="outline" className="bg-slate-800 text-slate-500 border-white/5 uppercase text-[9px] font-bold">False Positive</Badge>
                            ) : anomaly.is_acknowledged ? (
                              <Badge variant="outline" className="bg-warning/10 text-warning border-warning/20 uppercase text-[9px] font-bold">Acknowledged</Badge>
                            ) : (
                              <Badge variant="outline" className="bg-critical/10 text-critical border-critical/20 uppercase text-[9px] font-bold animate-pulse">Unresolved</Badge>
                            )}
                          </TableCell>
                          
                          <TableCell className="py-3.5 pr-6 text-right" onClick={e => e.stopPropagation()}>
                            <div className="flex items-center justify-end gap-2">
                              {!anomaly.is_acknowledged && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={(e) => handleFeedback(anomaly.id, 'acknowledged', e)}
                                  disabled={feedbackMutation.isPending}
                                  className="h-7 px-2.5 bg-warning/10 text-warning border-warning/20 hover:bg-warning hover:text-black text-[10px] font-bold uppercase gap-1"
                                >
                                  Ack
                                </Button>
                              )}
                              {!anomaly.is_false_positive && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={(e) => handleFeedback(anomaly.id, 'false_positive', e)}
                                  disabled={feedbackMutation.isPending}
                                  className="h-7 px-2.5 border-white/5 text-slate-400 hover:text-white hover:bg-white/5 text-[10px] font-bold uppercase gap-1"
                                >
                                  False Positive
                                </Button>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>

                        {isExpanded && (
                          <TableRow className="bg-slate-50 dark:bg-slate-950/30 hover:bg-slate-50 dark:hover:bg-slate-950/30">
                            <TableCell colSpan={8} className="p-6">
                              <div className="grid gap-6 md:grid-cols-2">
                                
                                {/* Text Explanation */}
                                <div className="space-y-4">
                                  <div className="space-y-1">
                                    <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                                      <Sparkles className="h-4 w-4 text-primary" />
                                      AI Drift Explanation
                                    </h4>
                                    <p className="bg-slate-100/35 dark:bg-slate-950/50 p-4 rounded-lg border border-slate-200 dark:border-white/5 leading-relaxed text-xs text-slate-700 dark:text-slate-400">
                                      {anomaly.explanation || 'Anomaly score indicates deviation from baseline variance.'}
                                    </p>
                                  </div>

                                  <div className="space-y-1.5">
                                    <h4 className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest">Metadata Context</h4>
                                    <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-600 dark:text-slate-400 bg-slate-100/35 dark:bg-slate-950/40 p-3 rounded-lg border border-slate-200 dark:border-white/5">
                                      <div>ID: {anomaly.id.slice(0, 18)}...</div>
                                      <div>Run ID: {anomaly.pipeline_run_id.slice(0, 18)}...</div>
                                      <div>Row count: {featureValues?.row_count !== undefined ? String(featureValues.row_count) : 'N/A'}</div>
                                      <div>Latency: {featureValues?.freshness_latency_seconds !== undefined ? `${featureValues.freshness_latency_seconds}s` : 'N/A'}</div>
                                    </div>
                                  </div>
                                </div>

                                {/* SHAP Recharts Chart */}
                                <div className="space-y-2">
                                  <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                                    <BarChart4 className="h-4 w-4 text-primary" />
                                    SHAP Feature Importance
                                  </h4>
                                  
                                  <div className="bg-slate-950/40 p-4 rounded-lg border border-white/5 h-[200px]">
                                    <ResponsiveContainer width="100%" height="100%">
                                      <BarChart
                                        data={shapData}
                                        layout="vertical"
                                        margin={{ top: 5, right: 5, left: -15, bottom: 5 }}
                                      >
                                        <XAxis 
                                          type="number" 
                                          stroke="#475569" 
                                          fontSize={8} 
                                          tickLine={false} 
                                          axisLine={false}
                                        />
                                        <YAxis 
                                          dataKey="name" 
                                          type="category" 
                                          stroke="#94a3b8" 
                                          fontSize={9} 
                                          tickLine={false} 
                                          axisLine={false}
                                          width={100}
                                        />
                                        <Tooltip 
                                          content={({ active, payload }: any) => {
                                            if (active && payload && payload.length) {
                                              const data = payload[0].payload
                                              return (
                                                <div className="bg-slate-900 border border-white/10 p-2 rounded text-[10px] space-y-0.5 shadow-xl">
                                                  <p className="font-bold text-slate-200 capitalize">{data.name}</p>
                                                  <p className="text-slate-400">
                                                    SHAP Contribution: <span className={data.value < 0 ? 'text-rose-400 font-bold' : 'text-emerald-400 font-bold'}>{data.value.toFixed(4)}</span>
                                                  </p>
                                                  <p className="text-[8px] text-slate-500 leading-normal">
                                                    {data.value < 0 ? 'Negative SHAP drives run toward anomaly' : 'Positive SHAP supports baseline stability'}
                                                  </p>
                                                </div>
                                              )
                                            }
                                            return null
                                          }}
                                        />
                                        <ReferenceLine x={0} stroke="rgba(255,255,255,0.1)" />
                                        <Bar dataKey="value" barSize={8} radius={4}>
                                          {shapData.map((entry, index) => (
                                            <Cell 
                                              key={`cell-${index}`} 
                                              fill={entry.value < 0 ? 'url(#shapNegative)' : 'url(#shapPositive)'} 
                                            />
                                          ))}
                                        </Bar>
                                        <defs>
                                          <linearGradient id="shapNegative" x1="0" y1="0" x2="1" y2="0">
                                            <stop offset="0%" stopColor="#ef4444" />
                                            <stop offset="100%" stopColor="#f43f5e" />
                                          </linearGradient>
                                          <linearGradient id="shapPositive" x1="0" y1="0" x2="1" y2="0">
                                            <stop offset="0%" stopColor="#10b981" />
                                            <stop offset="100%" stopColor="#34d399" />
                                          </linearGradient>
                                        </defs>
                                      </BarChart>
                                    </ResponsiveContainer>
                                  </div>
                                  <div className="text-[9px] text-slate-500 text-center leading-normal">
                                    Negative SHAP values (red bars) indicate metrics driving the run out of normal baseline bounds.
                                  </div>
                                </div>

                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </React.Fragment>
                    )
                  })}
                </TableBody>
              </Table>

              {/* Pagination controls */}
              <div className="flex flex-col sm:flex-row items-center justify-between border-t border-slate-200 dark:border-white/5 p-4 md:p-6 gap-4 bg-slate-50 dark:bg-slate-900/10">
                <div className="text-xs text-slate-500 font-medium">
                  Showing <span className="text-slate-800 dark:text-slate-300 font-bold">{currentStart}</span> to{' '}
                  <span className="text-slate-800 dark:text-slate-300 font-bold">{currentEnd}</span> of{' '}
                  <span className="text-slate-800 dark:text-slate-300 font-bold">{totalItems}</span> anomalies
                </div>

                <div className="flex items-center gap-4">
                  {/* Page size select */}
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Page size</span>
                    <Select
                      value={String(pageSize)}
                      onValueChange={(val) => {
                        setPageSize(Number(val))
                        setPage(1)
                      }}
                    >
                      <SelectTrigger className="w-16 bg-slate-950/40 border-white/5 text-slate-200 h-8 font-bold text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-900 border-white/10 text-slate-200 min-w-[64px]">
                        <SelectItem value="10" className="text-xs font-semibold">10</SelectItem>
                        <SelectItem value="20" className="text-xs font-semibold">20</SelectItem>
                        <SelectItem value="50" className="text-xs font-semibold">50</SelectItem>
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
                      className="h-8 w-8 border-white/5 text-slate-400 hover:text-white hover:bg-white/5 disabled:opacity-30"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <div className="text-xs font-bold text-slate-300 px-2 select-none">
                      Page {page} of {totalPages}
                    </div>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => handlePageChange(page + 1)}
                      disabled={page === totalPages}
                      className="h-8 w-8 border-white/5 text-slate-400 hover:text-white hover:bg-white/5 disabled:opacity-30"
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

'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { format } from 'date-fns'
import { 
  useTrustScoreHistory, 
  useTrustScoreTrend 
} from '@/hooks/useTrustScores'
import { useIncidents, useIncidentStats } from '@/hooks/useIncidents'
import { useAnomalyHealth } from '@/hooks/useAnomalies'
import TrustScoreGauge from '@/components/trust-score/TrustScoreGauge'
import TrustScoreTrend from '@/components/trust-score/TrustScoreTrend'
import PenaltyBreakdown from '@/components/trust-score/PenaltyBreakdown'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorBoundary from '@/components/common/ErrorBoundary'
import { 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Calendar,
  Layers,
  Sparkles,
  ArrowRight,
  TrendingDown,
  Info
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'

const TABLES = [
  { id: 'bronze_financial_candles', label: 'Financial Candles' },
  { id: 'bronze_fda_events', label: 'FDA Events' },
  { id: 'bronze_github_events', label: 'GitHub Events' }
]

export default function DashboardPage() {
  const [selectedTable, setSelectedTable] = useState(TABLES[0].id)
  
  // API Fetch calls
  const candlesHistory = useTrustScoreHistory('bronze_financial_candles', 1, 1)
  const fdaHistory = useTrustScoreHistory('bronze_fda_events', 1, 1)
  const githubHistory = useTrustScoreHistory('bronze_github_events', 1, 1)
  
  const trendQuery = useTrustScoreTrend(selectedTable, 30)
  const statsQuery = useIncidentStats()
  const incidentsQuery = useIncidents({ page: 1, page_size: 5 })
  const anomalyHealthQuery = useAnomalyHealth()

  // Loading validations
  const isLoading = 
    candlesHistory.isLoading || 
    fdaHistory.isLoading || 
    githubHistory.isLoading || 
    trendQuery.isLoading || 
    statsQuery.isLoading || 
    incidentsQuery.isLoading || 
    anomalyHealthQuery.isLoading

  if (isLoading) {
    return <LoadingSpinner text="Compiling Qolyx Dashboard Analytics..." fullPage />
  }

  // Calculate Latest overall scores
  const getLatestScore = (query: any) => {
    return query.data?.items?.[0]?.trust_score ?? 100
  }
  const scoreCandles = getLatestScore(candlesHistory)
  const scoreFda = getLatestScore(fdaHistory)
  const scoreGithub = getLatestScore(githubHistory)

  const overallAverageScore = Math.round((scoreCandles + scoreFda + scoreGithub) / 3)

  // Current selected table score records
  const currentHistoryItem = 
    selectedTable === 'bronze_financial_candles' ? candlesHistory.data?.items?.[0] :
    selectedTable === 'bronze_fda_events' ? fdaHistory.data?.items?.[0] :
    githubHistory.data?.items?.[0]

  const currentScore = currentHistoryItem?.trust_score ?? 100
  
  // Get active status colors for headers
  const getStatusClass = (score: number) => {
    if (score >= 80) return 'text-healthy bg-healthy/10 border-healthy/20'
    if (score >= 60) return 'text-warning bg-warning/10 border-warning/20'
    if (score >= 40) return 'text-degraded bg-degraded/10 border-degraded/20'
    return 'text-critical bg-critical/10 border-critical/20'
  }

  const getSeverityBadge = (sev: string) => {
    switch (sev.toUpperCase()) {
      case 'CRITICAL':
        return <Badge variant="outline" className="bg-critical/10 text-critical border-critical/20 uppercase text-[10px]">Critical</Badge>
      case 'HIGH':
        return <Badge variant="outline" className="bg-degraded/10 text-degraded border-degraded/20 uppercase text-[10px]">High</Badge>
      case 'MEDIUM':
        return <Badge variant="outline" className="bg-warning/10 text-warning border-warning/20 uppercase text-[10px]">Medium</Badge>
      default:
        return <Badge variant="outline" className="bg-muted text-muted-foreground border-border uppercase text-[10px]">Low</Badge>
    }
  }

  const getStateBadge = (state: string) => {
    switch (state.toUpperCase()) {
      case 'OPEN':
        return <span className="text-xs text-critical font-bold">● Open</span>
      case 'ACKNOWLEDGED':
        return <span className="text-xs text-warning font-bold">● Acknowledged</span>
      case 'RESOLVED':
        return <span className="text-xs text-healthy font-bold">● Resolved</span>
      default:
        return <span className="text-xs text-muted-foreground font-bold">● {state}</span>
    }
  }

  return (
    <ErrorBoundary>
      <div className="space-y-4 select-none">
        
        {/* Welcome Section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-400 bg-clip-text text-transparent flex items-center gap-2">
              Welcome back, Operator <Sparkles className="h-5 w-5 text-primary animate-pulse" />
            </h1>
            <p className="text-sm text-muted-foreground">Monitoring real-time database ingest reliability metrics and anomaly bounds.</p>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-muted border border-border text-xs text-muted-foreground font-medium self-start">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            {format(new Date(), 'PPPP')}
          </div>
        </div>

        {/* Top Summary Row */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {/* Card 1: Average Trust Score */}
          <div className="glass-panel p-6 rounded-xl flex flex-col gap-2 relative overflow-hidden group bg-card border border-border">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Average System health</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-4xl font-black text-foreground">{overallAverageScore}%</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-bold border ${getStatusClass(overallAverageScore)}`}>
                {overallAverageScore >= 80 ? 'HEALTHY' : 'WARNING'}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-2">Calculated across all active source tables</p>
          </div>

          {/* Card 2: Active Incidents */}
          <div className="glass-panel p-6 rounded-xl flex flex-col gap-2 relative overflow-hidden group bg-card border border-border">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Active incident logs</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-4xl font-black text-foreground">
                {statsQuery.data?.total_open ?? 0}
              </span>
              {(statsQuery.data?.total_open ?? 0) > 0 ? (
                <span className="text-xs px-2 py-0.5 rounded-full bg-critical/10 text-critical border border-critical/20 font-bold animate-pulse">
                  UNRESOLVED
                </span>
              ) : (
                <span className="text-xs px-2 py-0.5 rounded-full bg-healthy/10 text-healthy border border-healthy/20 font-bold">
                  STABLE
                </span>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground mt-2">Requires developer review and RCA inputs</p>
          </div>

          {/* Card 3: Trained ML Baselines */}
          <div className="glass-panel p-6 rounded-xl flex flex-col gap-2 relative overflow-hidden group bg-card border border-border">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Trained ML Baselines</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-4xl font-black text-foreground">
                {Object.values(anomalyHealthQuery.data || {}).filter(Boolean).length} / 3
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 font-bold">
                ISOLATION FOREST
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-2">Tables qualified with active ML detection bounds</p>
          </div>
        </div>

        {/* Second Row: Gauge & Trend Chart */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Gauge Widget */}
          <div className="glass-panel p-6 rounded-xl flex flex-col items-center justify-between min-h-[350px] bg-card border border-border">
            <div className="w-full flex items-center justify-between border-b border-border pb-4">
              <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Table scoring profile</span>
              <span className="text-[10px] text-muted-foreground">Run Ingress</span>
            </div>
            <div className="flex-1 flex items-center justify-center py-6">
              <TrustScoreGauge score={currentScore} size="lg" />
            </div>
            <div className="text-center space-y-1">
              <h4 className="font-bold text-foreground text-sm">
                {TABLES.find(t => t.id === selectedTable)?.label}
              </h4>
              <p className="text-[11px] text-muted-foreground max-w-xs">
                {(currentHistoryItem as any)?.explanation || 'No active penalties applied to the latest execution run.'}
              </p>
            </div>
          </div>

          {/* Trend Chart */}
          <div className="glass-panel p-6 rounded-xl lg:col-span-2 flex flex-col justify-between min-h-[350px] bg-card border border-border">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-border pb-4 gap-4">
              <div className="space-y-1">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Trust Score History</span>
                <p className="text-[11px] text-muted-foreground">Tracking score changes across the last 30 execution pipelines</p>
              </div>
              
              {/* Tab Selector */}
              <div className="flex p-1 rounded-lg bg-muted border border-border self-start sm:self-center">
                {TABLES.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setSelectedTable(t.id)}
                    className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${
                      selectedTable === t.id 
                        ? 'bg-primary text-white shadow-md' 
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {t.label.split(' ')[0]}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="flex-1 py-4">
              <TrustScoreTrend data={trendQuery.data || []} />
            </div>
          </div>
        </div>

        {/* Third Row: Penalty Breakdown & Pipelines */}
        <div className="grid gap-6 md:grid-cols-2">
          {/* Penalty Chart */}
          <div className="glass-panel p-6 rounded-xl flex flex-col justify-between bg-card border border-border">
            <div className="border-b border-border pb-4">
              <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Score penalty allocation</span>
              <p className="text-[11px] text-muted-foreground mt-0.5">Deduction breakdown details for the current table run</p>
            </div>
            <div className="flex-1 py-4 flex items-center justify-center">
              <PenaltyBreakdown 
                contract={currentHistoryItem?.contract_penalty || 0}
                freshness={currentHistoryItem?.freshness_penalty || 0}
                volume={currentHistoryItem?.volume_penalty || 0}
                anomaly={currentHistoryItem?.anomaly_penalty || 0}
                dbt={currentHistoryItem?.dbt_penalty || 0}
              />
            </div>
          </div>

          {/* Pipelines Health */}
          <div className="glass-panel p-6 rounded-xl flex flex-col justify-between bg-card border border-border">
            <div className="border-b border-border pb-4">
              <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Pipeline integrations</span>
              <p className="text-[11px] text-muted-foreground mt-0.5">Status of raw data collection schedulers</p>
            </div>
            
            <div className="flex-1 py-6 space-y-4">
              {/* Finnhub */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50 border border-border">
                <div className="space-y-1">
                  <span className="text-sm font-bold text-foreground">Finnhub Ingest (candles)</span>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                    <span>ML Baseline:</span>
                    <span className={anomalyHealthQuery.data?.['bronze_financial_candles'] ? 'text-healthy font-semibold' : 'text-muted-foreground'}>
                      {anomalyHealthQuery.data?.['bronze_financial_candles'] ? 'Ready' : 'Tuning (7 runs req.)'}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-foreground font-bold">{scoreCandles}%</span>
                  {scoreCandles >= 85 ? (
                    <CheckCircle2 className="h-5 w-5 text-healthy" />
                  ) : scoreCandles >= 70 ? (
                    <AlertTriangle className="h-5 w-5 text-warning" />
                  ) : (
                    <XCircle className="h-5 w-5 text-critical animate-pulse" />
                  )}
                </div>
              </div>

              {/* FDA */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50 border border-border">
                <div className="space-y-1">
                  <span className="text-sm font-bold text-foreground">FDA Scraping (events)</span>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                    <span>ML Baseline:</span>
                    <span className={anomalyHealthQuery.data?.['bronze_fda_events'] ? 'text-healthy font-semibold' : 'text-muted-foreground'}>
                      {anomalyHealthQuery.data?.['bronze_fda_events'] ? 'Ready' : 'Tuning (7 runs req.)'}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-foreground font-bold">{scoreFda}%</span>
                  {scoreFda >= 85 ? (
                    <CheckCircle2 className="h-5 w-5 text-healthy" />
                  ) : scoreFda >= 70 ? (
                    <AlertTriangle className="h-5 w-5 text-warning" />
                  ) : (
                    <XCircle className="h-5 w-5 text-critical animate-pulse" />
                  )}
                </div>
              </div>

              {/* Github */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50 border border-border">
                <div className="space-y-1">
                  <span className="text-sm font-bold text-foreground">GitHub Webhook (events)</span>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                    <span>ML Baseline:</span>
                    <span className={anomalyHealthQuery.data?.['bronze_github_events'] ? 'text-healthy font-semibold' : 'text-muted-foreground'}>
                      {anomalyHealthQuery.data?.['bronze_github_events'] ? 'Ready' : 'Tuning (7 runs req.)'}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-foreground font-bold">{scoreGithub}%</span>
                  {scoreGithub >= 85 ? (
                    <CheckCircle2 className="h-5 w-5 text-healthy" />
                  ) : scoreGithub >= 70 ? (
                    <AlertTriangle className="h-5 w-5 text-warning" />
                  ) : (
                    <XCircle className="h-5 w-5 text-critical animate-pulse" />
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Fourth Row: Recent Incidents */}
        <div className="glass-panel p-6 rounded-xl flex flex-col justify-between bg-card border border-border">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div className="space-y-0.5">
              <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-critical" />
                Active incident command feed
              </span>
              <p className="text-[11px] text-muted-foreground">Timeline events mapping trust score breaches below 70</p>
            </div>
            <Link href="/incidents" className="text-xs text-primary hover:text-emerald-500 font-bold flex items-center gap-1 group">
              View all
              <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>

          <div className="overflow-x-auto py-4">
            {incidentsQuery.data?.items && incidentsQuery.data.items.length > 0 ? (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border text-muted-foreground text-[10px] uppercase font-bold tracking-wider">
                    <th className="py-2.5">Title</th>
                    <th className="py-2.5">Severity</th>
                    <th className="py-2.5">Target Table</th>
                    <th className="py-2.5">State</th>
                    <th className="py-2.5 text-right">Logged At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border text-xs text-foreground">
                  {incidentsQuery.data.items.map((incident) => (
                    <tr 
                      key={incident.id} 
                      className="hover:bg-muted/50 transition-colors cursor-pointer group"
                    >
                      <td className="py-3 font-semibold text-foreground group-hover:text-primary transition-colors">
                        <Link href={`/incidents/${incident.id}`} className="block">
                          {incident.title}
                        </Link>
                      </td>
                      <td className="py-3">
                        <Link href={`/incidents/${incident.id}`} className="block">
                          {getSeverityBadge(incident.severity)}
                        </Link>
                      </td>
                      <td className="py-3 font-mono text-[10px]">
                        <Link href={`/incidents/${incident.id}`} className="block">
                          {incident.table_name}
                        </Link>
                      </td>
                      <td className="py-3">
                        <Link href={`/incidents/${incident.id}`} className="block">
                          {getStateBadge(incident.state)}
                        </Link>
                      </td>
                      <td className="py-3 text-right text-muted-foreground font-mono text-[10px]">
                        <Link href={`/incidents/${incident.id}`} className="block">
                          {format(new Date(incident.created_at), 'MMM dd, HH:mm')}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground text-xs">
                <CheckCircle2 className="h-8 w-8 text-healthy mb-2 opacity-80" />
                <span>No incidents logged. All datasets operating cleanly.</span>
              </div>
            )}
          </div>
        </div>

      </div>
    </ErrorBoundary>
  )
}

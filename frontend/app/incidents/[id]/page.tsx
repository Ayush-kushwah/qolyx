'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { format } from 'date-fns'
import { 
  useIncidentDetail,
  useAcknowledgeIncident,
  useResolveIncident,
  useCloseIncident,
  useReopenIncident,
  useAddIncidentComment,
  useRegenerateRCA,
  useUpdateIncident
} from '@/hooks/useIncidents'
import TrustScoreGauge from '@/components/trust-score/TrustScoreGauge'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorBoundary from '@/components/common/ErrorBoundary'
import EmptyState from '@/components/common/EmptyState'
import { 
  ArrowLeft,
  ShieldAlert,
  Clock,
  User,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Send,
  Wrench,
  RotateCcw,
  Sparkles,
  Layers,
  ChevronRight,
  UserCheck
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Card, CardContent } from '@/components/ui/card'

const MOCK_OPERATORS = [
  { value: 'unassigned', label: 'Unassigned' },
  { value: 'operator', label: 'Operator (Self)' },
  { value: 'Ayush Kushwah', label: 'Ayush Kushwah' },
  { value: 'operator_alpha', label: 'Operator Alpha' },
  { value: 'operator_beta', label: 'Operator Beta' },
]

export default function IncidentDetailPage({ params }: { params: { id: string } }) {
  const { id } = params
  const router = useRouter()

  // State hooks
  const [commentText, setCommentText] = useState('')
  const [resolutionNotes, setResolutionNotes] = useState('')
  const [isResolveOpen, setIsResolveOpen] = useState(false)

  // API Hooks
  const { 
    incident, 
    timeline, 
    comments, 
    rca, 
    isLoading, 
    isError, 
    error,
    refetchAll 
  } = useIncidentDetail(id)

  const ackMutation = useAcknowledgeIncident()
  const resolveMutation = useResolveIncident()
  const closeMutation = useCloseIncident()
  const reopenMutation = useReopenIncident()
  const commentMutation = useAddIncidentComment()
  const rcaMutation = useRegenerateRCA()
  const updateMutation = useUpdateIncident()

  if (isLoading) {
    return <LoadingSpinner text="Retrieving Incident Forensic Details..." fullPage />
  }

  if (isError || !incident) {
    return (
      <div className="py-24 px-6">
        <EmptyState
          title="Incident Not Found"
          description={error instanceof Error ? error.message : 'Could not find details for the requested incident ID.'}
          icon={AlertTriangle}
          action={{
            label: "Back to Feed",
            onClick: () => router.push('/incidents')
          }}
        />
      </div>
    )
  }

  // Calculate score and score details
  const score = incident.rca ? 100 - (rca?.confidence ? rca.confidence * 40 : 30) : 60 // fallback mock calculations
  
  const getSeverityBadge = (sev: string) => {
    switch (sev.toUpperCase()) {
      case 'CRITICAL':
        return <Badge variant="outline" className="bg-critical/10 text-critical border-critical/20 uppercase text-[10px] font-bold">Critical</Badge>
      case 'HIGH':
        return <Badge variant="outline" className="bg-degraded/10 text-degraded border-degraded/20 uppercase text-[10px] font-bold">High</Badge>
      case 'MEDIUM':
        return <Badge variant="outline" className="bg-warning/10 text-warning border-warning/20 uppercase text-[10px] font-bold">Medium</Badge>
      default:
        return <Badge variant="outline" className="bg-muted text-muted-foreground border-border uppercase text-[10px] font-bold">Low</Badge>
    }
  }

  const getStateBadge = (state: string) => {
    switch (state.toUpperCase()) {
      case 'OPEN':
        return (
          <span className="flex items-center gap-1.5 text-xs text-critical font-bold bg-critical/10 px-2.5 py-1 rounded-full border border-critical/20">
            <span className="h-1.5 w-1.5 rounded-full bg-critical animate-ping" />
            Open
          </span>
        )
      case 'ACKNOWLEDGED':
        return (
          <span className="flex items-center gap-1.5 text-xs text-warning font-bold bg-warning/10 px-2.5 py-1 rounded-full border border-warning/20">
            <span className="h-1.5 w-1.5 rounded-full bg-warning" />
            Acknowledged
          </span>
        )
      case 'RESOLVED':
        return (
          <span className="flex items-center gap-1.5 text-xs text-healthy font-bold bg-healthy/10 px-2.5 py-1 rounded-full border border-healthy/20">
            <span className="h-1.5 w-1.5 rounded-full bg-healthy" />
            Resolved
          </span>
        )
      case 'CLOSED':
        return (
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground font-bold bg-muted px-2.5 py-1 rounded-full border border-border">
            <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground" />
            Closed
          </span>
        )
      default:
        return (
          <span className="text-xs text-muted-foreground font-bold bg-muted px-2.5 py-1 rounded-full border border-border">
            {state}
          </span>
        )
    }
  }

  const handleAcknowledge = () => {
    ackMutation.mutate({ id })
  }

  const handleResolve = (e: React.FormEvent) => {
    e.preventDefault()
    if (!resolutionNotes.trim()) return
    resolveMutation.mutate(
      { id, resolutionNotes },
      {
        onSuccess: () => {
          setIsResolveOpen(false)
          setResolutionNotes('')
        }
      }
    )
  }

  const handleClose = () => {
    closeMutation.mutate({ id })
  }

  const handleReopen = () => {
    reopenMutation.mutate({ id })
  }

  const handlePostComment = (e: React.FormEvent) => {
    e.preventDefault()
    if (!commentText.trim()) return
    commentMutation.mutate(
      { id, comment: commentText, createdBy: 'operator' },
      {
        onSuccess: () => {
          setCommentText('')
        }
      }
    )
  }

  const handleRegenerateRCA = () => {
    rcaMutation.mutate({ id })
  }

  const handleAssignOperator = (val: string) => {
    const assigned_to = val === 'unassigned' ? null : val
    updateMutation.mutate({ 
      id, 
      data: { assigned_to, assigned_team: val === 'unassigned' ? null : 'reliability-eng' } 
    })
  }

  const isMutating = 
    ackMutation.isPending || 
    resolveMutation.isPending || 
    closeMutation.isPending || 
    reopenMutation.isPending || 
    updateMutation.isPending

  return (
    <ErrorBoundary>
      <div className="space-y-4 select-none">
        
        {/* Back navigation & Refresh row */}
        <div className="flex items-center justify-between">
          <Link 
            href="/incidents" 
            className="flex items-center gap-2 text-xs font-bold text-muted-foreground hover:text-foreground transition-colors uppercase tracking-wider"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Incident Feed
          </Link>
          <Button
            variant="ghost"
            size="sm"
            onClick={refetchAll}
            className="text-muted-foreground border border-border hover:bg-muted hover:text-foreground text-xs font-bold gap-1"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Force Sync
          </Button>
        </div>

        {/* Incident Main Title Block */}
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 border-b border-border pb-4">
          <div className="space-y-2 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              {getSeverityBadge(incident.severity)}
              {getStateBadge(incident.state)}
              <span className="text-xs font-mono text-muted-foreground">Pipeline Run: {incident.pipeline_run_id.slice(0, 8)}...</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground flex items-start gap-2.5">
              <ShieldAlert className="h-7 w-7 text-critical mt-1 flex-shrink-0" />
              {incident.title}
            </h1>
            <p className="text-xs font-mono text-muted-foreground bg-muted/40 border border-border px-3 py-1 rounded inline-block">
              Target Source: {incident.table_name}
            </p>
          </div>
        </div>

        {/* Two Column Page Content */}
        <div className="grid gap-6 lg:grid-cols-3">
          
          {/* LEFT: Core diagnostics details */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Trust Score & Circular Gauge */}
            <div className="glass-panel p-6 rounded-xl flex flex-col md:flex-row items-center gap-8 bg-card border border-border">
              <div className="flex-shrink-0">
                <TrustScoreGauge score={score} size="md" />
              </div>
              <div className="space-y-4 flex-grow text-center md:text-left">
                <div className="space-y-1">
                  <h3 className="text-base font-bold text-foreground">Pipeline Run Quality</h3>
                  <p className="text-xs text-muted-foreground">
                    Calculated run scoring with penalty deductions logged at time of anomaly capture.
                  </p>
                </div>
                
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-left pt-2">
                  <div className="p-2 rounded bg-background/40 border border-border">
                    <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wide">Schema Failures</div>
                    <div className="text-xs font-bold text-foreground">-{rca ? (rca.primary_penalty === 'schema' ? '40' : '0') : '10'} pts</div>
                  </div>
                  <div className="p-2 rounded bg-background/40 border border-border">
                    <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wide">Freshness Lag</div>
                    <div className="text-xs font-bold text-foreground">-{rca ? (rca.primary_penalty === 'freshness' ? '30' : '0') : '0'} pts</div>
                  </div>
                  <div className="p-2 rounded bg-background/40 border border-border">
                    <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wide">Volume Drift</div>
                    <div className="text-xs font-bold text-foreground">-{rca ? (rca.primary_penalty === 'volume' ? '30' : '0') : '10'} pts</div>
                  </div>
                  <div className="p-2 rounded bg-background/40 border border-border">
                    <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wide">ML Anomalies</div>
                    <div className="text-xs font-bold text-foreground">-{rca ? (rca.primary_penalty === 'anomaly' ? '20' : '10') : '20'} pts</div>
                  </div>
                  <div className="p-2 rounded bg-background/40 border border-border col-span-2 sm:col-span-1">
                    <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wide">DBT Tests</div>
                    <div className="text-xs font-bold text-foreground">-{rca ? (rca.primary_penalty === 'dbt' ? '20' : '0') : '0'} pts</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Root Cause Analysis (RCA) Section */}
            <div className="glass-panel p-6 rounded-xl space-y-4 bg-card border border-border relative overflow-hidden group">
              <div className="flex items-center justify-between border-b border-border pb-4">
                <div className="space-y-0.5">
                  <h3 className="text-sm font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="h-4 w-4 text-primary animate-pulse" />
                    AI Root Cause Analysis (RCA)
                  </h3>
                  <p className="text-[11px] text-muted-foreground">ML models tracing telemetry and schema metrics</p>
                </div>
                {rca && (
                  <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 text-[10px] font-semibold h-5">
                    Confidence: {Math.round(rca.confidence * 100)}%
                  </Badge>
                )}
              </div>

              {rca ? (
                <div className="space-y-4 text-xs text-foreground/90">
                  <div className="space-y-1">
                    <span className="font-bold text-foreground uppercase tracking-wider text-[10px]">Summary</span>
                    <p className="bg-background/30 p-3 rounded-lg border border-border leading-relaxed">{rca.summary}</p>
                  </div>
                  
                  <div className="space-y-1">
                    <span className="font-bold text-foreground uppercase tracking-wider text-[10px]">Root Cause</span>
                    <p className="bg-background/30 p-3 rounded-lg border border-border leading-relaxed font-mono">{rca.root_cause}</p>
                  </div>

                  {rca.contributing_factors && rca.contributing_factors.length > 0 && (
                    <div className="space-y-1">
                      <span className="font-bold text-foreground uppercase tracking-wider text-[10px]">Contributing Factors</span>
                      <ul className="list-disc pl-4 space-y-1 bg-background/30 p-3 rounded-lg border border-border">
                        {rca.contributing_factors.map((factor, index) => (
                          <li key={index} className="leading-relaxed">{factor}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {rca.recommendation && (
                    <div className="space-y-1">
                      <span className="font-bold text-foreground uppercase tracking-wider text-[10px]">Recommendation</span>
                      <p className="bg-background/30 p-3 rounded-lg border border-border leading-relaxed text-healthy bg-healthy/10">{rca.recommendation}</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-10 text-center space-y-3">
                  <AlertCircle className="h-8 w-8 text-muted-foreground opacity-60" />
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground font-bold">No RCA Telemetry Generated</p>
                    <p className="text-[11px] text-muted-foreground">Run manual analysis diagnostics below.</p>
                  </div>
                  <Button
                    size="sm"
                    onClick={handleRegenerateRCA}
                    disabled={rcaMutation.isPending}
                    className="bg-primary text-white hover:bg-emerald-600 font-bold text-xs"
                  >
                    {rcaMutation.isPending ? 'Generating...' : 'Run Diagnostics'}
                  </Button>
                </div>
              )}
            </div>

            {/* Chronological Timeline */}
            <div className="glass-panel p-6 rounded-xl space-y-4 bg-card border border-border">
              <div className="border-b border-border pb-4">
                <h3 className="text-sm font-bold text-foreground uppercase tracking-wider">
                  Timeline Events
                </h3>
                <p className="text-[11px] text-muted-foreground">Audit logs tracking incident transitions and alerts</p>
              </div>

              <div className="relative pl-6 border-l border-border ml-3 space-y-6 pt-2">
                {timeline.map((event) => {
                  return (
                    <div key={event.id} className="relative group select-none">
                      {/* Blip dot */}
                      <span className={`absolute -left-[30px] top-1 h-3.5 w-3.5 rounded-full border-2 border-background flex items-center justify-center ${
                        event.event_type.includes('CREATE') ? 'bg-critical' :
                        event.event_type.includes('ACKNOWLEDGE') ? 'bg-warning' :
                        event.event_type.includes('RESOLVE') ? 'bg-healthy' : 'bg-muted-foreground'
                      }`} />
                      
                      <div className="space-y-1">
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-bold text-foreground">{event.event_type.replace(/_/g, ' ')}</span>
                          <span className="text-[10px] font-mono text-muted-foreground">{format(new Date(event.created_at), 'yyyy-MM-dd HH:mm:ss')}</span>
                        </div>
                        {event.created_by && (
                          <div className="text-[10px] text-muted-foreground flex items-center gap-1 font-medium">
                            <User className="h-3 w-3 text-muted-foreground/80" />
                            Triggered by: <span className="font-bold text-foreground">{event.created_by}</span>
                          </div>
                        )}
                        {event.event_data && Object.keys(event.event_data).length > 0 && (
                          <div className="text-[11px] bg-background/40 border border-border rounded p-2.5 mt-1 text-muted-foreground font-mono overflow-x-auto leading-normal">
                            {JSON.stringify(event.event_data, null, 2)}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

          </div>

          {/* RIGHT: Status commands and Comments */}
          <div className="space-y-6">
            
            {/* Quick Actions Panel */}
            <div className="glass-panel p-6 rounded-xl space-y-4 bg-card border border-border">
              <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest border-b border-border pb-2">
                Operations Commands
              </h3>

              {/* Status Buttons */}
              <div className="space-y-3">
                {incident.state.toUpperCase() === 'OPEN' && (
                  <Button
                    onClick={handleAcknowledge}
                    disabled={isMutating}
                    className="w-full bg-warning text-black hover:bg-amber-400 font-bold text-xs uppercase"
                  >
                    {ackMutation.isPending ? 'Acknowledging...' : 'Acknowledge Incident'}
                  </Button>
                )}

                {(incident.state.toUpperCase() === 'OPEN' || incident.state.toUpperCase() === 'ACKNOWLEDGED') && (
                  <Dialog open={isResolveOpen} onOpenChange={setIsResolveOpen}>
                    <DialogTrigger asChild>
                      <Button
                        disabled={isMutating}
                        className="w-full bg-healthy text-white hover:bg-emerald-600 font-bold text-xs uppercase"
                      >
                        Resolve Incident
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="bg-card border border-border text-foreground max-w-md rounded-xl shadow-2xl">
                      <form onSubmit={handleResolve} className="space-y-4">
                        <DialogHeader>
                          <DialogTitle className="text-base font-extrabold text-foreground flex items-center gap-2">
                            <CheckCircle2 className="h-5 w-5 text-healthy" />
                            Resolve Data Breach
                          </DialogTitle>
                          <DialogDescription className="text-muted-foreground text-xs leading-relaxed">
                            Provide short, specific engineering resolution notes. Describe the fixes applied or investigations completed.
                          </DialogDescription>
                        </DialogHeader>
                        
                        <div className="space-y-1">
                          <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Resolution Notes</label>
                          <Textarea
                            placeholder="Describe how the schema breach or anomaly was corrected..."
                            value={resolutionNotes}
                            onChange={(e) => setResolutionNotes(e.target.value)}
                            required
                            className="bg-background border-border text-foreground text-xs h-24 focus:border-primary focus:ring-1 focus:ring-primary rounded-lg resize-none"
                          />
                        </div>

                        <DialogFooter className="gap-2">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => setIsResolveOpen(false)}
                            className="text-muted-foreground border border-border hover:bg-muted hover:text-foreground text-xs font-bold"
                          >
                            Cancel
                          </Button>
                          <Button
                            type="submit"
                            size="sm"
                            disabled={resolveMutation.isPending}
                            className="bg-healthy text-white hover:bg-emerald-600 font-bold text-xs"
                          >
                            {resolveMutation.isPending ? 'Resolving...' : 'Confirm Resolution'}
                          </Button>
                        </DialogFooter>
                      </form>
                    </DialogContent>
                  </Dialog>
                )}

                {incident.state.toUpperCase() === 'RESOLVED' && (
                  <Button
                    onClick={handleClose}
                    disabled={isMutating}
                    className="w-full bg-muted text-muted-foreground border border-border hover:bg-muted/80 hover:text-foreground font-bold text-xs uppercase"
                  >
                    {closeMutation.isPending ? 'Closing...' : 'Close Incident'}
                  </Button>
                )}

                {(incident.state.toUpperCase() === 'RESOLVED' || incident.state.toUpperCase() === 'CLOSED') && (
                  <Button
                    onClick={handleReopen}
                    disabled={isMutating}
                    className="w-full bg-background border border-border hover:bg-muted text-muted-foreground hover:text-foreground font-bold text-xs uppercase"
                  >
                    {reopenMutation.isPending ? 'Reopening...' : 'Reopen Incident'}
                  </Button>
                )}
              </div>

              {/* Assignee selector */}
              <div className="space-y-1.5 pt-2 border-t border-border">
                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                  <UserCheck className="h-3.5 w-3.5 text-muted-foreground/80" />
                  Assign Operator
                </label>
                <Select 
                  value={incident.assigned_to || 'unassigned'} 
                  onValueChange={handleAssignOperator}
                  disabled={updateMutation.isPending}
                >
                  <SelectTrigger className="bg-background border-border text-foreground h-9 font-medium text-xs rounded-lg">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-card border-border text-foreground">
                    {MOCK_OPERATORS.map((o) => (
                      <SelectItem key={o.value} value={o.value} className="text-xs">
                        {o.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Regenerate RCA Button */}
              {rca && (
                <div className="pt-2">
                  <Button
                    onClick={handleRegenerateRCA}
                    disabled={rcaMutation.isPending}
                    variant="outline"
                    className="w-full border-border text-muted-foreground hover:bg-muted hover:text-foreground text-[10px] font-bold uppercase tracking-wider h-8 gap-1 bg-card"
                  >
                    <Wrench className="h-3.5 w-3.5" />
                    {rcaMutation.isPending ? 'Re-analyzing...' : 'Regenerate RCA'}
                  </Button>
                </div>
              )}
            </div>

            {/* Incident Comments thread */}
            <div className="glass-panel p-6 rounded-xl flex flex-col justify-between min-h-[350px] bg-card border border-border">
              <div className="border-b border-border pb-2">
                <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
                  Discussion Thread
                </h3>
              </div>

              {/* Comments Thread Area */}
              <div className="flex-1 overflow-y-auto py-4 space-y-4 max-h-[300px] pr-1">
                {comments.length > 0 ? (
                  comments.map((comment) => (
                    <div key={comment.id} className="space-y-1 text-xs">
                      <div className="flex items-center justify-between text-[10px] text-muted-foreground font-semibold">
                        <span className="text-foreground font-bold">{comment.created_by}</span>
                        <span>{format(new Date(comment.created_at), 'MM-dd HH:mm')}</span>
                      </div>
                      <p className="bg-background/40 border border-border rounded-lg p-2.5 text-foreground/90 leading-normal">
                        {comment.comment}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="flex flex-col items-center justify-center h-full py-16 text-center text-muted-foreground text-xs">
                    <User className="h-8 w-8 opacity-40 mb-2" />
                    <span>No comments posted. Add a team note below.</span>
                  </div>
                )}
              </div>

              {/* Comment Input */}
              <form onSubmit={handlePostComment} className="pt-4 border-t border-border flex gap-2">
                <Textarea
                  placeholder="Ask a question or add details..."
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  required
                  disabled={commentMutation.isPending}
                  className="bg-background border-border text-foreground text-xs h-9 min-h-[36px] max-h-[80px] focus:border-primary focus:ring-1 focus:ring-primary rounded-lg resize-none flex-grow"
                />
                <Button
                  type="submit"
                  size="icon"
                  disabled={commentMutation.isPending || !commentText.trim()}
                  className="h-9 w-9 bg-primary text-white hover:bg-emerald-600 rounded-lg flex-shrink-0"
                >
                  <Send className="h-3.5 w-3.5" />
                </Button>
              </form>
            </div>

          </div>

        </div>

      </div>
    </ErrorBoundary>
  )
}

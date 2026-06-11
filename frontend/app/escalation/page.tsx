'use client'

import React, { useState } from 'react'
import { useEscalationPolicies, useCheckEscalations } from '@/hooks/useEscalationPolicies'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorBoundary from '@/components/common/ErrorBoundary'
import EmptyState from '@/components/common/EmptyState'
import EscalationCard from '@/components/escalation/EscalationCard'
import EscalationForm from '@/components/escalation/EscalationForm'

import { 
  ServerCrash, 
  Plus, 
  Play, 
  ShieldAlert, 
  Clock, 
  CheckSquare,
  RefreshCw
} from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function EscalationsPage() {
  const { data: policies = [], isLoading, isError, error } = useEscalationPolicies()
  const checkMutation = useCheckEscalations()
  const [isFormOpen, setIsFormOpen] = useState(false)

  // Calculate metrics
  const totalPolicies = policies.length
  const maxTimeout = policies.length > 0 
    ? Math.max(...policies.map(p => p.timeout_minutes)) 
    : 0

  const handleRunChecks = () => {
    checkMutation.mutate()
  }

  return (
    <ErrorBoundary>
      <div className="space-y-6 max-w-7xl mx-auto p-4 md:p-6 pb-20">
        
        {/* Header Action Row */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-white/5 pb-5">
          <div className="space-y-1">
            <h1 className="text-2xl font-extrabold tracking-tight bg-gradient-to-r from-slate-900 via-slate-800 to-slate-600 dark:from-white dark:via-slate-100 dark:to-slate-400 bg-clip-text text-transparent">
              Incident Escalation Policies
            </h1>
            <p className="text-xs text-slate-600 dark:text-slate-400 max-w-xl leading-relaxed">
              Define automated routing policies for open incidents. When incidents remain unacknowledged beyond configured deadlines, the system escalates the assignment to standby shifts.
            </p>
          </div>
          <div className="flex items-center gap-2.5 self-start md:self-auto">
            <Button
              variant="outline"
              onClick={handleRunChecks}
              disabled={checkMutation.isPending}
              className="border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-slate-900/40 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white font-bold text-xs h-9 px-3.5 gap-1.5 transition-all"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${checkMutation.isPending ? 'animate-spin' : ''}`} />
              Run Escalation Check
            </Button>
            <Button
              onClick={() => setIsFormOpen(true)}
              className="bg-primary hover:bg-primary/80 text-white font-bold text-xs h-9 px-4 gap-1.5 shadow-lg shadow-primary/20 transition-all hover:scale-[1.02]"
            >
              <Plus className="h-4 w-4" />
              Create Policy
            </Button>
          </div>
        </div>

        {/* Stats Summary Panel */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="glass-panel p-4 rounded-xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-slate-900/10 flex items-center gap-4">
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg">
              <ServerCrash className="h-5 w-5" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-600 dark:text-slate-500 tracking-wider block font-mono">Active Rules</span>
              <span className="text-lg font-black text-slate-900 dark:text-slate-100 font-mono">{totalPolicies}</span>
            </div>
          </div>

          <div className="glass-panel p-4 rounded-xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-slate-900/10 flex items-center gap-4">
            <div className="p-3 bg-primary/10 border border-primary/20 text-primary rounded-lg">
              <Clock className="h-5 w-5" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-600 dark:text-slate-500 tracking-wider block font-mono">Max Escalation Deadline</span>
              <span className="text-lg font-black text-slate-900 dark:text-slate-100 font-mono">{maxTimeout} mins</span>
            </div>
          </div>

          <div className="glass-panel p-4 rounded-xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-slate-900/10 flex items-center gap-4">
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg">
              <CheckSquare className="h-5 w-5" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-600 dark:text-slate-500 tracking-wider block font-mono">Policy Check Daemon</span>
              <span className="text-xs font-black text-emerald-400 font-mono flex items-center gap-1.5 mt-0.5 uppercase tracking-wide">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                Active
              </span>
            </div>
          </div>
        </div>

        {/* List Grid */}
        {isLoading ? (
          <div className="py-20 flex justify-center items-center">
            <LoadingSpinner text="Fetching escalation routing rules..." />
          </div>
        ) : isError ? (
          <div className="glass-panel p-8 rounded-xl border border-rose-500/20 bg-rose-500/5 text-center space-y-3">
            <ShieldAlert className="h-10 w-10 text-rose-400 mx-auto" />
            <h3 className="font-extrabold text-slate-800 dark:text-slate-200">Sync Error</h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 max-w-md mx-auto">
              {error instanceof Error ? error.message : 'Could not query escalation services from Backend API.'}
            </p>
          </div>
        ) : policies.length === 0 ? (
          <EmptyState
            icon={ServerCrash}
            title="No Escalation Policies Configured"
            description="Create policy rules to route unacknowledged high-severity anomalies and alerts to backup channels."
            action={{
              label: "Create Policy",
              onClick: () => setIsFormOpen(true)
            }}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {policies.map((policy) => (
              <EscalationCard 
                key={policy.id} 
                policy={policy} 
              />
            ))}
          </div>
        )}

        {/* Create Policy Modal */}
        <EscalationForm
          open={isFormOpen}
          onOpenChange={setIsFormOpen}
        />

      </div>
    </ErrorBoundary>
  )
}

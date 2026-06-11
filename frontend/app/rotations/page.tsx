'use client'

import React, { useState } from 'react'
import { useRotations } from '@/hooks/useRotations'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorBoundary from '@/components/common/ErrorBoundary'
import EmptyState from '@/components/common/EmptyState'
import RotationCard from '@/components/rotations/RotationCard'
import RotationForm from '@/components/rotations/RotationForm'

import { 
  Users, 
  Plus, 
  Calendar, 
  Clock, 
  ShieldAlert 
} from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function RotationsPage() {
  const { data: rotations = [], isLoading, isError, error } = useRotations()
  const [isFormOpen, setIsFormOpen] = useState(false)

  // Calculate quick stats
  const totalRotations = rotations.length
  const uniqueTeams = Array.from(new Set(rotations.map(r => r.team_name))).length
  const currentEngineersCount = rotations.filter(r => r.members && r.members.length > 0).length

  return (
    <ErrorBoundary>
      <div className="space-y-6 max-w-7xl mx-auto p-4 md:p-6 pb-20">
        
        {/* Header Action Row */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-white/5 pb-5">
          <div className="space-y-1">
            <h1 className="text-2xl font-extrabold tracking-tight bg-gradient-to-r from-slate-900 via-slate-800 to-slate-600 dark:from-white dark:via-slate-100 dark:to-slate-400 bg-clip-text text-transparent">
              On-Call Shift Rotations
            </h1>
            <p className="text-xs text-slate-600 dark:text-slate-400 max-w-xl leading-relaxed">
              Designate operations shift members and schedule automatic handovers. Assigned engineers receive priority mobile and webhook notifications.
            </p>
          </div>
          <Button
            onClick={() => setIsFormOpen(true)}
            className="bg-primary hover:bg-primary/80 text-white font-bold text-xs h-9 px-4 self-start md:self-auto gap-1.5 shadow-lg shadow-primary/20 transition-all hover:scale-[1.02]"
          >
            <Plus className="h-4 w-4" />
            Create Rotation
          </Button>
        </div>

        {/* Stats Summary Panel */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="glass-panel p-4 rounded-xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-slate-900/10 flex items-center gap-4">
            <div className="p-3 bg-primary/10 border border-primary/20 text-primary rounded-lg">
              <Calendar className="h-5 w-5" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-600 dark:text-slate-500 tracking-wider block">Active Schedules</span>
              <span className="text-lg font-black text-slate-900 dark:text-slate-100 font-mono">{totalRotations}</span>
            </div>
          </div>

          <div className="glass-panel p-4 rounded-xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-slate-900/10 flex items-center gap-4">
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg">
              <Users className="h-5 w-5" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-600 dark:text-slate-500 tracking-wider block">Teams Managed</span>
              <span className="text-lg font-black text-slate-900 dark:text-slate-100 font-mono">{uniqueTeams}</span>
            </div>
          </div>

          <div className="glass-panel p-4 rounded-xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-slate-900/10 flex items-center gap-4">
            <div className="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg">
              <Clock className="h-5 w-5" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-600 dark:text-slate-500 tracking-wider block">Active Shift Officers</span>
              <span className="text-lg font-black text-slate-900 dark:text-slate-100 font-mono">{currentEngineersCount}</span>
            </div>
          </div>
        </div>

        {/* Main content area */}
        {isLoading ? (
          <div className="py-20 flex justify-center items-center">
            <LoadingSpinner text="Fetching rotation schedules..." />
          </div>
        ) : isError ? (
          <div className="glass-panel p-8 rounded-xl border border-rose-500/20 bg-rose-500/5 text-center space-y-3">
            <ShieldAlert className="h-10 w-10 text-rose-400 mx-auto" />
            <h3 className="font-extrabold text-slate-800 dark:text-slate-200">Sync Error</h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 max-w-md mx-auto">
              {error instanceof Error ? error.message : 'Could not query rotation services from Backend API.'}
            </p>
          </div>
        ) : rotations.length === 0 ? (
          <EmptyState
            icon={Users}
            title="No On-call Rotations Configured"
            description="Create schedules to assign incident response tasks to operational staff members in rotation shifts."
            action={{
              label: "Create Schedule",
              onClick: () => setIsFormOpen(true)
            }}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {rotations.map((rotation) => (
              <RotationCard 
                key={rotation.id} 
                rotation={rotation} 
              />
            ))}
          </div>
        )}

        {/* Create Rotation Modal */}
        <RotationForm
          open={isFormOpen}
          onOpenChange={setIsFormOpen}
        />

      </div>
    </ErrorBoundary>
  )
}

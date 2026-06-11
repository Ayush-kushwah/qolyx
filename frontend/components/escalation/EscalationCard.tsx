'use client'

import React from 'react'
import { EscalationPolicy } from '@/types'
import { Badge } from '@/components/ui/badge'
import { 
  Clock, 
  ArrowRight, 
  User, 
  Users, 
  Slack, 
  Network 
} from 'lucide-react'

interface EscalationCardProps {
  policy: EscalationPolicy
}

export default function EscalationCard({ policy }: EscalationCardProps) {
  const { name, severity, timeout_minutes, target_type, target_identifier } = policy

  // Severity color maps
  const getSeverityStyles = (sev: string) => {
    switch (sev.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20'
      case 'HIGH':
        return 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20'
      case 'MEDIUM':
        return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
      case 'LOW':
      default:
        return 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20'
    }
  }

  // Get icons matching Target Types
  const getTargetDetails = (type: string, id: string) => {
    switch (type.toUpperCase()) {
      case 'ROTATION':
        return {
          icon: <Network className="h-4 w-4 text-emerald-400" />,
          label: 'On-Call Rotation',
          value: id
        }
      case 'SLACK_CHANNEL':
        return {
          icon: <Slack className="h-4 w-4 text-emerald-400" />,
          label: 'Slack Channel Notification',
          value: id.startsWith('#') ? id : `#${id}`
        }
      case 'MEMBER':
        return {
          icon: <User className="h-4 w-4 text-sky-400" />,
          label: 'Standby Officer',
          value: id
        }
      case 'TEAM':
      default:
        return {
          icon: <Users className="h-4 w-4 text-amber-400" />,
          label: 'Operations Team Escalation',
          value: id
        }
    }
  }

  const target = getTargetDetails(target_type, target_identifier)

  return (
    <div className="glass-panel p-5 rounded-xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-slate-900/10 flex flex-col justify-between min-h-[180px] transition-all hover:scale-[1.01] hover:border-slate-300 dark:hover:border-white/10 relative group">
      
      {/* Background glow animation */}
      <div className="absolute -inset-px bg-gradient-to-r from-primary/5 to-emerald-500/5 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none duration-500" />

      <div className="space-y-4 relative z-10">
        
        {/* Title & Severity Row */}
        <div className="flex items-start justify-between gap-4">
          <h3 className="font-extrabold text-slate-800 dark:text-slate-200 text-sm tracking-tight leading-snug line-clamp-1">
            {name}
          </h3>
          <Badge className={`border py-0.5 text-[8px] font-extrabold uppercase font-mono tracking-wider ${getSeverityStyles(severity)}`}>
            {severity}
          </Badge>
        </div>

        {/* Timeout Indicator */}
        <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 font-semibold select-none">
          <Clock className="h-3.5 w-3.5 text-primary flex-shrink-0" />
          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-600 dark:text-slate-500 font-mono">DEADLINE:</span>
          <span className="text-xs text-slate-700 dark:text-slate-300 font-mono font-black">{timeout_minutes} minutes</span>
        </div>

        {/* Target Route Details */}
        <div className="bg-slate-100/50 dark:bg-slate-950/30 p-3 rounded-lg border border-slate-200 dark:border-white/5 flex items-center justify-between gap-4 select-none">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-slate-200 dark:bg-slate-900 border border-slate-300 dark:border-white/5 rounded-md flex items-center justify-center flex-shrink-0">
              {target.icon}
            </div>
            <div className="space-y-0.5 min-w-0">
              <span className="text-[8px] uppercase font-bold text-slate-600 dark:text-slate-500 tracking-wider block font-mono">
                {target.label}
              </span>
              <span className="text-xs font-black text-slate-800 dark:text-slate-200 truncate block font-mono" title={target.value}>
                {target.value}
              </span>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-slate-600 group-hover:text-primary transition-colors flex-shrink-0" />
        </div>

      </div>
    </div>
  )
}

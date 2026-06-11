'use client'

import React from 'react'
import { OncallRotation } from '@/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useRotateRotation } from '@/hooks/useRotations'
import { 
  Users, 
  RefreshCw, 
  Calendar, 
  ArrowRight,
  ShieldCheck,
  UserCheck
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface RotationCardProps {
  rotation: OncallRotation
}

export default function RotationCard({ rotation }: RotationCardProps) {
  const rotateMutation = useRotateRotation()
  const { id, name, team_name, members, current_index, rotation_type, last_rotated_at } = rotation

  const activeOncall = members[current_index] || 'None'
  const isRotating = rotateMutation.isPending && rotateMutation.variables === id

  // Format initials for avatar display
  const getInitials = (nameStr: string) => {
    if (!nameStr || nameStr === 'None') return '??'
    const parts = nameStr.split(/[.@_]/).filter(Boolean)
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase()
    }
    return nameStr.slice(0, 2).toUpperCase()
  }

  const handleRotate = () => {
    rotateMutation.mutate(id)
  }

  // Helper to format date nicely
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never rotated'
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString(undefined, { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div className="glass-panel p-5 rounded-xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-slate-900/10 flex flex-col justify-between min-h-[300px] transition-all hover:scale-[1.01] hover:border-slate-300 dark:hover:border-white/10 relative group">
      
      {/* Glow Effect on Hover */}
      <div className="absolute -inset-px bg-gradient-to-r from-primary/10 to-emerald-500/10 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none duration-500" />

      <div className="space-y-4 relative z-10">
        
        {/* Header Details */}
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
              <Users className="h-3.5 w-3.5" />
              <span className="text-[10px] font-bold uppercase tracking-wider font-mono">{team_name}</span>
            </div>
            <h3 className="font-extrabold text-slate-800 dark:text-slate-200 text-sm tracking-tight leading-snug line-clamp-1">
              {name}
            </h3>
          </div>
          <Badge variant="outline" className="bg-slate-100 dark:bg-slate-950/40 text-[9px] font-mono font-bold text-slate-600 dark:text-slate-400 border-slate-200 dark:border-white/5 py-0.5 uppercase tracking-wide">
            {rotation_type}
          </Badge>
        </div>

        {/* Current Active Engineer Highlight */}
        <div className="p-3.5 rounded-lg bg-primary/5 border border-primary/10 flex items-center justify-between gap-4 select-none relative overflow-hidden">
          <div className="flex items-center gap-3">
            {/* Initials Avatar with pulsating ring */}
            <div className="relative">
              <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary to-emerald-500 flex items-center justify-center text-xs font-black text-white shadow-md border border-white/10 font-mono">
                {getInitials(activeOncall)}
              </div>
              <span className="absolute bottom-0 right-0 block h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-slate-900 animate-pulse" />
            </div>
            <div className="space-y-0.5">
              <span className="text-[9px] uppercase font-bold text-primary tracking-widest block font-mono">ON SHIFT NOW</span>
              <span className="text-xs font-black text-slate-800 dark:text-slate-200 truncate max-w-[140px] block" title={activeOncall}>
                {activeOncall}
              </span>
            </div>
          </div>
          <div className="p-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-md text-emerald-400">
            <UserCheck className="h-4 w-4" />
          </div>
        </div>

        {/* Rotation List Timeline */}
        <div className="space-y-1.5">
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block font-mono">Shift Rotation Track</span>
          <div className="bg-slate-100/50 dark:bg-slate-950/35 p-3 rounded-lg border border-slate-200 dark:border-white/5 space-y-2 max-h-[120px] overflow-y-auto custom-scrollbar">
            {members.map((member, idx) => {
              const isActive = idx === current_index
              return (
                <div 
                  key={`${member}-${idx}`} 
                  className={cn(
                    "flex items-center justify-between text-xs py-1 px-1.5 rounded transition-all",
                    isActive 
                      ? "bg-slate-200/50 dark:bg-white/5 text-slate-900 dark:text-slate-100 font-bold border border-slate-200 dark:border-white/5 shadow-inner" 
                      : "text-slate-600 dark:text-slate-400"
                  )}
                >
                  <div className="flex items-center gap-2 truncate">
                    <span className={cn(
                      "font-mono text-[9px] h-4 w-4 rounded-full flex items-center justify-center font-bold",
                      isActive ? "bg-primary text-white" : "bg-slate-200 dark:bg-slate-900 text-slate-600 dark:text-slate-500"
                    )}>
                      {idx + 1}
                    </span>
                    <span className="truncate">{member}</span>
                  </div>
                  {isActive && (
                    <Badge className="bg-primary/20 text-primary border-primary/20 text-[8px] font-extrabold py-0 px-1 font-mono uppercase">
                      Current
                    </Badge>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Footer rotated timestamp and Action Trigger */}
      <div className="border-t border-slate-200 dark:border-white/5 pt-3 mt-4 flex items-center justify-between relative z-10 select-none">
        <div className="space-y-0.5">
          <span className="text-[8px] font-bold text-slate-500 uppercase tracking-wide block font-mono">Last Shift Rotation</span>
          <span className="text-[10px] text-slate-600 dark:text-slate-400 font-semibold font-mono">
            {formatDate(last_rotated_at)}
          </span>
        </div>

        <Button
          size="sm"
          variant="outline"
          onClick={handleRotate}
          disabled={isRotating || members.length <= 1}
          className="h-8 px-3 text-primary hover:text-white border-primary/20 bg-primary/10 hover:bg-primary/20 text-xs font-bold gap-1.5 transition-all"
        >
          <RefreshCw className={cn("h-3 w-3", isRotating && "animate-spin")} />
          Rotate Shift
        </Button>
      </div>
    </div>
  )
}

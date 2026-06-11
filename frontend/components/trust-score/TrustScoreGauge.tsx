'use client'

import React from 'react'
import { cn } from '@/lib/utils'

interface TrustScoreGaugeProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export default function TrustScoreGauge({ score, size = 'md', className }: TrustScoreGaugeProps) {
  const clampedScore = Math.max(0, Math.min(100, score))
  const radius = 50
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (clampedScore / 100) * circumference

  // Color mapping based on score
  const getColor = (val: number) => {
    if (val >= 80) return 'text-healthy stroke-healthy'
    if (val >= 60) return 'text-warning stroke-warning'
    if (val >= 40) return 'text-degraded stroke-degraded'
    return 'text-critical stroke-critical'
  }

  const getBgColor = (val: number) => {
    if (val >= 80) return 'stroke-healthy/10'
    if (val >= 60) return 'stroke-warning/10'
    if (val >= 40) return 'stroke-degraded/10'
    return 'stroke-critical/10'
  }

  const dimensions = {
    sm: 'h-24 w-24 text-xl',
    md: 'h-36 w-36 text-3xl',
    lg: 'h-48 w-48 text-4xl',
  }

  return (
    <div className={cn("relative flex items-center justify-center select-none", className)}>
      <svg className={cn("transform -rotate-90", dimensions[size].split(' ')[0], dimensions[size].split(' ')[1])} viewBox="0 0 120 120">
        {/* Track circle */}
        <circle
          cx="60"
          cy="60"
          r={radius}
          className={cn("fill-transparent stroke-[10px]", getBgColor(clampedScore))}
        />
        {/* Progress circle */}
        <circle
          cx="60"
          cy="60"
          r={radius}
          className={cn("fill-transparent stroke-[10px] transition-all duration-500 ease-out", getColor(clampedScore))}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
        />
      </svg>
      {/* Centered text */}
      <div className="absolute flex flex-col items-center justify-center text-center">
        <span className={cn("font-extrabold tracking-tighter text-slate-900 dark:text-slate-100", dimensions[size].split(' ')[2])}>
          {clampedScore}%
        </span>
        <span className="text-[10px] font-semibold text-slate-600 dark:text-slate-500 uppercase tracking-widest mt-0.5">
          Health
        </span>
      </div>
    </div>
  )
}

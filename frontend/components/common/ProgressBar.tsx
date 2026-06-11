import React from 'react'

interface ProgressBarProps {
  value: number // 0-100
  label: string
  subtext?: string
  showPercentage?: boolean
}

export default function ProgressBar({
  value,
  label,
  subtext,
  showPercentage = true
}: ProgressBarProps) {
  // Clamp value between 0 and 100
  const clampedValue = Math.min(100, Math.max(0, value))

  // Determine gradient color class based on progress percentage
  let gradientClass = 'bg-gradient-to-r from-red-500 to-rose-600' // low (< 40%)
  if (clampedValue >= 100) {
    gradientClass = 'bg-gradient-to-r from-emerald-500 to-teal-500' // complete (100%)
  } else if (clampedValue >= 40) {
    gradientClass = 'bg-gradient-to-r from-amber-500 to-yellow-500' // medium (40-99%)
  }

  return (
    <div className="w-full space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-semibold text-slate-700 dark:text-slate-300">{label}</span>
        {showPercentage && (
          <span className="font-bold text-slate-900 dark:text-slate-200">
            {Math.round(clampedValue)}%
          </span>
        )}
      </div>
      <div className="h-3 w-full rounded-full bg-slate-100 dark:bg-slate-800/80 overflow-hidden border border-slate-200/50 dark:border-slate-700/50">
        <div
          className={`h-full rounded-full ${gradientClass} transition-all duration-700 ease-out`}
          style={{ width: `${clampedValue}%` }}
        />
      </div>
      {subtext && (
        <p className="text-xs text-slate-500 dark:text-slate-400">{subtext}</p>
      )}
    </div>
  )
}

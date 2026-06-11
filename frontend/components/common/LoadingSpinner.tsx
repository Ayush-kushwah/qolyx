import React from 'react'
import { Loader2 } from 'lucide-react'

interface LoadingSpinnerProps {
  text?: string
  fullPage?: boolean
}

export default function LoadingSpinner({ text = 'Loading...', fullPage = false }: LoadingSpinnerProps) {
  const content = (
    <div className="flex flex-col items-center justify-center gap-3 p-6 select-none">
      <div className="relative flex items-center justify-center">
        <Loader2 className="h-10 w-10 text-primary animate-spin" />
        <div className="absolute h-10 w-10 rounded-full border-2 border-primary/20 animate-ping opacity-75" />
      </div>
      {text && (
        <span className="text-sm font-medium text-slate-400 animate-pulse tracking-wide">
          {text}
        </span>
      )}
    </div>
  )

  if (fullPage) {
    return (
      <div className="fixed inset-0 bg-background/80 backdrop-blur-md flex items-center justify-center z-50">
        {content}
      </div>
    )
  }

  return (
    <div className="w-full flex items-center justify-center min-h-[200px]">
      {content}
    </div>
  )
}

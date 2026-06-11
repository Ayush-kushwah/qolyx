import React from 'react'
import { LucideIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
  }
}

export default function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center min-h-[300px] rounded-xl glass-panel select-none">
      <div className="bg-white/5 p-4 rounded-full border border-white/10 mb-4 text-slate-400">
        <Icon className="h-10 w-10" />
      </div>
      <h3 className="text-lg font-bold mb-1">{title}</h3>
      <p className="text-slate-400 text-sm max-w-sm mb-6 leading-relaxed">
        {description}
      </p>
      {action && (
        <Button onClick={action.onClick} className="shadow-lg hover:shadow-primary/20">
          {action.label}
        </Button>
      )}
    </div>
  )
}

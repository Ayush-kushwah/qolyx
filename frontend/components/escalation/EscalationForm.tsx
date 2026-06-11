'use client'

import React, { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCreateEscalationPolicy } from '@/hooks/useEscalationPolicies'
import { useRotations } from '@/hooks/useRotations'
import { EscalationPolicyCreate } from '@/types'

// Zod validation schema
const escalationSchema = z.object({
  name: z.string().min(1, 'Policy name is required'),
  severity: z.enum(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']),
  timeout_minutes: z.string().refine((val) => {
    const parsed = parseInt(val, 10)
    return !isNaN(parsed) && parsed >= 1
  }, {
    message: 'Timeout must be a positive integer (minimum 1 minute)'
  }),
  target_type: z.enum(['TEAM', 'MEMBER', 'ROTATION', 'SLACK_CHANNEL']),
  target_identifier: z.string().min(1, 'Target destination is required'),
})

type EscalationFormValues = z.infer<typeof escalationSchema>

interface EscalationFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function EscalationForm({ open, onOpenChange }: EscalationFormProps) {
  const createMutation = useCreateEscalationPolicy()
  const { data: rotations = [] } = useRotations()

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<EscalationFormValues>({
    resolver: zodResolver(escalationSchema),
    defaultValues: {
      name: '',
      severity: 'HIGH',
      timeout_minutes: '15',
      target_type: 'ROTATION',
      target_identifier: '',
    },
  })

  const targetType = watch('target_type')
  const severity = watch('severity')
  const targetIdentifier = watch('target_identifier')

  // Reset fields on open/close
  useEffect(() => {
    if (open) {
      reset({
        name: '',
        severity: 'HIGH',
        timeout_minutes: '15',
        target_type: 'ROTATION',
        target_identifier: '',
      })
    }
  }, [open, reset])

  // Automatically reset target identifier if target type changes
  useEffect(() => {
    setValue('target_identifier', '')
  }, [targetType, setValue])

  const onSubmit = async (values: EscalationFormValues) => {
    try {
      const payload: EscalationPolicyCreate = {
        name: values.name,
        severity: values.severity,
        timeout_minutes: parseInt(values.timeout_minutes, 10),
        target_type: values.target_type,
        target_identifier: values.target_identifier,
      }
      await createMutation.mutateAsync(payload)
      onOpenChange(false)
    } catch (e) {
      // Backend error handled by React Query toast
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white rounded-xl shadow-2xl">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold tracking-tight bg-gradient-to-r from-primary to-emerald-400 bg-clip-text text-transparent">
            Create Escalation Policy
          </DialogTitle>
          <DialogDescription className="text-slate-550 dark:text-slate-400 text-sm">
            Set up automated rules to route unresolved alerts after timeout limits expire.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          
          {/* Policy Name */}
          <div className="space-y-1">
            <Label htmlFor="name" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
              Policy Name
            </Label>
            <Input
              id="name"
              placeholder="e.g. Critical Escalation Pipeline"
              className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9"
              {...register('name')}
            />
            {errors.name && (
              <p className="text-xs text-rose-500 font-medium">{errors.name.message}</p>
            )}
          </div>

          {/* Severity & Timeout */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                Severity Level
              </Label>
              <Select
                value={severity}
                onValueChange={(val) => setValue('severity', val as any)}
              >
                <SelectTrigger className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 text-slate-800 dark:text-white text-xs h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-white dark:bg-slate-900 border-slate-200 dark:border-white/10 text-slate-800 dark:text-white text-xs">
                  <SelectItem value="LOW">LOW</SelectItem>
                  <SelectItem value="MEDIUM">MEDIUM</SelectItem>
                  <SelectItem value="HIGH">HIGH</SelectItem>
                  <SelectItem value="CRITICAL">CRITICAL</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label htmlFor="timeout_minutes" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                Timeout (Minutes)
              </Label>
              <Input
                id="timeout_minutes"
                type="number"
                placeholder="15"
                className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9 font-mono"
                {...register('timeout_minutes')}
              />
              {errors.timeout_minutes && (
                <p className="text-xs text-rose-500 font-medium">{errors.timeout_minutes.message}</p>
              )}
            </div>
          </div>

          {/* Grid: Target Type & Identifier */}
          <div className="space-y-3 border-t border-slate-100 dark:border-white/5 pt-3">
            <div className="space-y-1">
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                Escalation Route Type
              </Label>
              <Select
                value={targetType}
                onValueChange={(val) => setValue('target_type', val as any)}
              >
                <SelectTrigger className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 text-slate-800 dark:text-white text-xs h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-white dark:bg-slate-900 border-slate-200 dark:border-white/10 text-slate-800 dark:text-white text-xs">
                  <SelectItem value="ROTATION">On-Call Rotation</SelectItem>
                  <SelectItem value="SLACK_CHANNEL">Slack Channel</SelectItem>
                  <SelectItem value="MEMBER">Standby Member</SelectItem>
                  <SelectItem value="TEAM">Operations Team</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Target Identifier Field (context aware) */}
            <div className="space-y-1">
              <Label htmlFor="target_identifier" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                Route Destination
              </Label>

              {targetType === 'ROTATION' ? (
                <Select
                  value={targetIdentifier}
                  onValueChange={(val) => setValue('target_identifier', val)}
                >
                  <SelectTrigger className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 text-slate-800 dark:text-white text-xs h-9">
                    <SelectValue placeholder="Select active rotation schedule..." />
                  </SelectTrigger>
                  <SelectContent className="bg-white dark:bg-slate-900 border-slate-200 dark:border-white/10 text-slate-800 dark:text-white text-xs">
                    {rotations.length === 0 ? (
                      <div className="text-[10px] text-slate-500 italic p-3 text-center">
                        No rotations exist. Create a rotation schedule first.
                      </div>
                    ) : (
                      rotations.map((rot) => (
                        <SelectItem key={rot.id} value={rot.name}>
                          {rot.name} ({rot.team_name})
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  id="target_identifier"
                  placeholder={
                    targetType === 'SLACK_CHANNEL' 
                      ? 'e.g. #ops-critical-alerts' 
                      : targetType === 'MEMBER' 
                        ? 'e.g. engineer@org.com' 
                        : 'e.g. Platform Team'
                  }
                  className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9"
                  {...register('target_identifier')}
                />
              )}

              {errors.target_identifier && (
                <p className="text-xs text-rose-500 font-medium">{errors.target_identifier.message}</p>
              )}
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0 pt-4 border-t border-slate-100 dark:border-white/5">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              className="hover:bg-slate-100 dark:hover:bg-white/5 text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || createMutation.isPending}
              className="bg-primary hover:bg-primary/80 text-white font-semibold text-xs h-9 px-4 min-w-[100px]"
            >
              Create Policy
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

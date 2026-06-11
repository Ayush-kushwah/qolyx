'use client'

import React, { useState, useEffect } from 'react'
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
import { useCreateRotation } from '@/hooks/useRotations'
import { OncallRotationCreate } from '@/types'
import { X, Plus, AlertCircle } from 'lucide-react'

// Zod validation schema
const rotationSchema = z.object({
  name: z.string().min(1, 'Rotation schedule name is required'),
  team_name: z.string().min(1, 'Team designation name is required'),
  rotation_type: z.enum(['DAILY', 'WEEKLY', 'HOURLY']),
  members: z.array(z.string().min(1)).min(1, 'At least one shift member must participate in the rotation'),
})

type RotationFormValues = z.infer<typeof rotationSchema>

interface RotationFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function RotationForm({ open, onOpenChange }: RotationFormProps) {
  const createMutation = useCreateRotation()
  const [memberInput, setMemberInput] = useState('')

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<RotationFormValues>({
    resolver: zodResolver(rotationSchema),
    defaultValues: {
      name: '',
      team_name: '',
      rotation_type: 'WEEKLY',
      members: [],
    },
  })

  const membersList = watch('members')
  const rotationType = watch('rotation_type')

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (open) {
      reset({
        name: '',
        team_name: '',
        rotation_type: 'WEEKLY',
        members: [],
      })
      setMemberInput('')
    }
  }, [open, reset])

  // Append new member helper
  const handleAddMember = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const trimmed = memberInput.trim()
    if (!trimmed) return
    if (membersList.includes(trimmed)) {
      setMemberInput('')
      return
    }
    setValue('members', [...membersList, trimmed], { shouldValidate: true })
    setMemberInput('')
  }

  // Remove existing member helper
  const handleRemoveMember = (idxToRemove: number) => {
    const updated = membersList.filter((_, idx) => idx !== idxToRemove)
    setValue('members', updated, { shouldValidate: true })
  }

  const onSubmit = async (values: RotationFormValues) => {
    try {
      await createMutation.mutateAsync(values as OncallRotationCreate)
      onOpenChange(false)
    } catch (e) {
      // API error handled by toast in useCreateRotation hook
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white rounded-xl shadow-2xl">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold tracking-tight bg-gradient-to-r from-primary to-emerald-400 bg-clip-text text-transparent">
            Create On-Call Rotation
          </DialogTitle>
          <DialogDescription className="text-slate-550 dark:text-slate-400 text-sm">
            Define a developer shift schedule to automatically direct incident escalations.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          
          {/* Name Field */}
          <div className="space-y-1">
            <Label htmlFor="name" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
              Rotation Name
            </Label>
            <Input
              id="name"
              placeholder="e.g. Core Engine Tier-1 On-Call"
              className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9"
              {...register('name')}
            />
            {errors.name && (
              <p className="text-xs text-rose-500 font-medium">{errors.name.message}</p>
            )}
          </div>

          {/* Grid: Team & Rotation Type */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <Label htmlFor="team_name" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                Team Designation
              </Label>
              <Input
                id="team_name"
                placeholder="e.g. Platform Team"
                className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9"
                {...register('team_name')}
              />
              {errors.team_name && (
                <p className="text-xs text-rose-500 font-medium">{errors.team_name.message}</p>
              )}
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                Rotation Frequency
              </Label>
              <Select
                value={rotationType}
                onValueChange={(val) => setValue('rotation_type', val as any)}
              >
                <SelectTrigger className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 text-slate-800 dark:text-white text-xs h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-white dark:bg-slate-900 border-slate-200 dark:border-white/10 text-slate-800 dark:text-white text-xs">
                  <SelectItem value="HOURLY">HOURLY</SelectItem>
                  <SelectItem value="DAILY">DAILY</SelectItem>
                  <SelectItem value="WEEKLY">WEEKLY</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Members Chip Builder Field */}
          <div className="space-y-2 border-t border-slate-100 dark:border-white/5 pt-3">
            <Label className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
              Shift Participants
            </Label>
            
            {/* Input & Add Button */}
            <div className="flex gap-2">
              <Input
                value={memberInput}
                onChange={(e) => setMemberInput(e.target.value)}
                placeholder="Enter member email or username"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    handleAddMember()
                  }
                }}
                className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9"
              />
              <Button
                type="button"
                onClick={() => handleAddMember()}
                className="bg-slate-50 dark:bg-slate-950/40 border border-slate-200 dark:border-white/5 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 text-xs px-3 h-9"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>

            {/* Chips Box */}
            <div className="bg-slate-50 dark:bg-slate-950/30 p-2.5 rounded-lg border border-slate-200 dark:border-white/5 min-h-[75px] max-h-[140px] overflow-y-auto">
              {membersList.length === 0 ? (
                <div className="text-[10px] text-slate-550 dark:text-slate-500 italic py-4 text-center">
                  No participants added yet. Type a username and hit Enter.
                </div>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {membersList.map((member, idx) => (
                    <div
                      key={`${member}-${idx}`}
                      className="bg-primary/10 border border-primary/20 text-slate-700 dark:text-slate-300 px-2 py-0.5 rounded text-[11px] font-medium flex items-center gap-1 select-none"
                    >
                      <span className="truncate max-w-[120px] font-mono">{member}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveMember(idx)}
                        className="text-slate-400 hover:text-rose-500 dark:hover:text-rose-400 transition-colors"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {errors.members && (
              <p className="text-xs text-rose-500 font-medium flex items-center gap-1">
                <AlertCircle className="h-3.5 w-3.5" />
                {errors.members.message}
              </p>
            )}
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
              Add Schedule
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

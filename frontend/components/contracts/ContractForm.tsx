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
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { useCreateContract, useUpdateContract } from '@/hooks/useContracts'
import { Contract, ContractCreate } from '@/types'

// Zod Schema
const contractSchema = z.object({
  name: z.string().min(1, 'Contract Name is required'),
  table_name: z.string().min(1, 'Database Table Name is required'),
  schema_definition_str: z.string().refine((val) => {
    try {
      const parsed = JSON.parse(val)
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        return false
      }
      for (const key in parsed) {
        const item = parsed[key]
        if (typeof item !== 'object' || item === null || typeof item.data_type !== 'string') {
          return false
        }
      }
      return true
    } catch {
      return false
    }
  }, 'Must be a valid JSON mapping column names to expectation objects (e.g. {"column_name": {"data_type": "VARCHAR", "nullable": true}})'),
  is_active: z.boolean().default(true),
})

type ContractFormValues = z.infer<typeof contractSchema>

interface ContractFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  contract?: Contract | null
  initialValues?: Partial<ContractCreate> | null
}

const DEFAULT_SCHEMA_TEMPLATE = `{
  "id": {
    "data_type": "UUID",
    "nullable": false,
    "is_required": true
  },
  "created_at": {
    "data_type": "TIMESTAMP",
    "nullable": false,
    "is_required": true
  }
}`

export default function ContractForm({
  open,
  onOpenChange,
  contract,
  initialValues,
}: ContractFormProps) {
  const createMutation = useCreateContract()
  const updateMutation = useUpdateContract()
  const isEdit = !!contract

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ContractFormValues>({
    resolver: zodResolver(contractSchema),
    defaultValues: {
      name: '',
      table_name: '',
      schema_definition_str: DEFAULT_SCHEMA_TEMPLATE,
      is_active: true,
    },
  })

  // Watch is_active switch state
  const isActive = watch('is_active')

  // Set form values on edit or initialValues load
  useEffect(() => {
    if (open) {
      if (contract) {
        reset({
          name: contract.name,
          table_name: contract.table_name,
          schema_definition_str: JSON.stringify(contract.schema_definition, null, 2),
          is_active: contract.is_active,
        })
      } else if (initialValues) {
        reset({
          name: initialValues.name || '',
          table_name: initialValues.table_name || '',
          schema_definition_str: initialValues.schema_definition
            ? JSON.stringify(initialValues.schema_definition, null, 2)
            : DEFAULT_SCHEMA_TEMPLATE,
          is_active: initialValues.is_active ?? true,
        })
      } else {
        reset({
          name: '',
          table_name: '',
          schema_definition_str: DEFAULT_SCHEMA_TEMPLATE,
          is_active: true,
        })
      }
    }
  }, [open, contract, initialValues, reset])

  const onSubmit = async (values: ContractFormValues) => {
    try {
      const schemaDefinition = JSON.parse(values.schema_definition_str)
      
      if (isEdit && contract) {
        await updateMutation.mutateAsync({
          id: contract.id,
          data: {
            name: values.name,
            schema_definition: schemaDefinition,
            is_active: values.is_active,
          },
        })
      } else {
        await createMutation.mutateAsync({
          name: values.name,
          table_name: values.table_name,
          schema_definition: schemaDefinition,
          is_active: values.is_active,
        })
      }
      onOpenChange(false)
    } catch (e) {
      // Handled by hook toasts
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white rounded-xl shadow-2xl">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold tracking-tight bg-gradient-to-r from-primary to-emerald-400 bg-clip-text text-transparent">
            {isEdit ? 'Edit Data Contract' : 'Create Data Contract'}
          </DialogTitle>
          <DialogDescription className="text-slate-550 dark:text-slate-400 text-sm">
            Configure schemas and validation criteria to detect anomalies in incoming ingestion streams.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5 py-2">
          {/* Contract Name */}
          <div className="space-y-2">
            <Label htmlFor="name" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
              Contract Name
            </Label>
            <Input
              id="name"
              placeholder="e.g. candles-contract"
              className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white"
              {...register('name')}
            />
            {errors.name && (
              <p className="text-xs text-rose-500 font-medium">{errors.name.message}</p>
            )}
          </div>

          {/* Table Name */}
          <div className="space-y-2">
            <Label htmlFor="table_name" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
              Database Table Name
            </Label>
            <Input
              id="table_name"
              placeholder="e.g. bronze_financial_candles"
              disabled={isEdit}
              className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed"
              {...register('table_name')}
            />
            {errors.table_name && (
              <p className="text-xs text-rose-500 font-medium">{errors.table_name.message}</p>
            )}
            {!isEdit && (
              <p className="text-[10px] text-slate-500 dark:text-slate-400">
                Must match the ingestion table name where incoming events are loaded.
              </p>
            )}
          </div>

          {/* Active Toggle */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-950/30 border border-slate-200 dark:border-white/5">
            <div className="space-y-0.5">
              <Label className="text-sm font-semibold text-slate-700 dark:text-slate-300">Active Status</Label>
              <p className="text-[11px] text-slate-550 dark:text-slate-400">
                Whether this contract should be enforced during next pipeline runs.
              </p>
            </div>
            <Switch
              checked={isActive}
              onCheckedChange={(checked) => setValue('is_active', checked)}
              className="data-[state=checked]:bg-primary"
            />
          </div>

          {/* Schema JSON Editor */}
          <div className="space-y-2">
            <Label htmlFor="schema_definition_str" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
              Schema Definition (JSON)
            </Label>
            <Textarea
              id="schema_definition_str"
              rows={8}
              className="font-mono text-xs bg-slate-50 dark:bg-slate-950/70 border-slate-200 dark:border-white/10 focus:border-primary/50 text-emerald-700 dark:text-emerald-400 focus-visible:ring-0 focus-visible:ring-offset-0"
              {...register('schema_definition_str')}
            />
            {errors.schema_definition_str && (
              <p className="text-xs text-rose-500 font-medium leading-relaxed">
                {errors.schema_definition_str.message}
              </p>
            )}
          </div>

          <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t border-slate-100 dark:border-white/5">
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
              disabled={isSubmitting || createMutation.isPending || updateMutation.isPending}
              className="bg-primary hover:bg-primary/80 text-white font-semibold"
            >
              {isEdit ? 'Save Changes' : 'Create Contract'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

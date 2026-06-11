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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCreateAlertConfig, useUpdateAlertConfig } from '@/hooks/useAlertConfigs'
import { AlertConfig, AlertConfigCreate } from '@/types'

// Zod validation schema
const alertConfigSchema = z.object({
  name: z.string().min(1, 'Alert channel name is required'),
  channel_type: z.enum(['slack', 'discord', 'teams', 'telegram', 'email', 'ntfy', 'webhook']),
  webhook_url: z.string().url('Must be a valid URL').optional().or(z.literal('')),
  telegram_bot_token: z.string().optional().or(z.literal('')),
  telegram_chat_id: z.string().optional().or(z.literal('')),
  smtp_server: z.string().optional().or(z.literal('')),
  smtp_port: z.string().optional().or(z.literal('')), // handle as string then parse
  smtp_user: z.string().optional().or(z.literal('')),
  smtp_password: z.string().optional().or(z.literal('')),
  from_address: z.string().optional().or(z.literal('')),
  to_addresses_str: z.string().optional().or(z.literal('')),
  severity_threshold: z.enum(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']),
  is_active: z.boolean().default(true),
}).superRefine((data, ctx) => {
  const { channel_type, webhook_url, telegram_bot_token, telegram_chat_id, smtp_server, smtp_port, from_address, to_addresses_str } = data

  // Validate webhook-based channels
  if (['slack', 'discord', 'teams', 'webhook'].includes(channel_type)) {
    if (!webhook_url || webhook_url.trim() === '') {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['webhook_url'],
        message: `Webhook URL is required for ${channel_type}`,
      })
    }
  }

  // Validate telegram channel
  if (channel_type === 'telegram') {
    if (!telegram_bot_token || telegram_bot_token.trim() === '') {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['telegram_bot_token'],
        message: 'Telegram Bot Token is required',
      })
    }
    if (!telegram_chat_id || telegram_chat_id.trim() === '') {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['telegram_chat_id'],
        message: 'Telegram Chat ID is required',
      })
    }
  }

  // Validate email channel
  if (channel_type === 'email') {
    if (!smtp_server || smtp_server.trim() === '') {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['smtp_server'],
        message: 'SMTP host is required',
      })
    }
    if (!smtp_port || smtp_port.trim() === '') {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['smtp_port'],
        message: 'SMTP port is required',
      })
    }
    if (!from_address || from_address.trim() === '') {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['from_address'],
        message: 'Sender (From) address is required',
      })
    } else if (!z.string().email().safeParse(from_address).success) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['from_address'],
        message: 'Must be a valid sender email address',
      })
    }
    
    if (!to_addresses_str || to_addresses_str.trim() === '') {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['to_addresses_str'],
        message: 'At least one recipient email address is required',
      })
    } else {
      const emails = to_addresses_str.split(',').map(e => e.trim())
      const invalid = emails.some(e => !z.string().email().safeParse(e).success)
      if (invalid) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['to_addresses_str'],
          message: 'All recipient entries must be valid email addresses separated by commas',
        })
      }
    }
  }
})

type AlertConfigFormValues = z.infer<typeof alertConfigSchema>

interface AlertConfigFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  config?: AlertConfig | null
}

export default function AlertConfigForm({ open, onOpenChange, config }: AlertConfigFormProps) {
  const createMutation = useCreateAlertConfig()
  const updateMutation = useUpdateAlertConfig()
  const isEdit = !!config

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AlertConfigFormValues>({
    resolver: zodResolver(alertConfigSchema),
    defaultValues: {
      name: '',
      channel_type: 'slack',
      webhook_url: '',
      telegram_bot_token: '',
      telegram_chat_id: '',
      smtp_server: '',
      smtp_port: '',
      smtp_user: '',
      smtp_password: '',
      from_address: '',
      to_addresses_str: '',
      severity_threshold: 'MEDIUM',
      is_active: true,
    },
  })

  const channelType = watch('channel_type')
  const isActive = watch('is_active')

  // Set form fields when opening in edit mode
  useEffect(() => {
    if (open) {
      if (config) {
        reset({
          name: config.name,
          channel_type: config.channel_type,
          webhook_url: config.webhook_url || '',
          telegram_bot_token: config.telegram_bot_token || '',
          telegram_chat_id: config.telegram_chat_id || '',
          smtp_server: config.email_config?.smtp_server || '',
          smtp_port: config.email_config?.smtp_port ? String(config.email_config.smtp_port) : '',
          smtp_user: config.email_config?.smtp_user || '',
          smtp_password: config.email_config?.smtp_password || '',
          from_address: config.email_config?.from_address || '',
          to_addresses_str: Array.isArray(config.email_config?.to_addresses)
            ? config.email_config.to_addresses.join(', ')
            : (typeof config.email_config?.to_addresses === 'string'
              ? config.email_config.to_addresses
              : ''),
          severity_threshold: config.severity_threshold as any,
          is_active: config.is_active,
        })
      } else {
        reset({
          name: '',
          channel_type: 'slack',
          webhook_url: '',
          telegram_bot_token: '',
          telegram_chat_id: '',
          smtp_server: '',
          smtp_port: '',
          smtp_user: '',
          smtp_password: '',
          from_address: '',
          to_addresses_str: '',
          severity_threshold: 'MEDIUM',
          is_active: true,
        })
      }
    }
  }, [open, config, reset])

  const onSubmit = async (values: AlertConfigFormValues) => {
    try {
      const payload: any = {
        name: values.name,
        channel_type: values.channel_type,
        severity_threshold: values.severity_threshold,
        is_active: values.is_active,
      }

      if (['slack', 'discord', 'teams', 'webhook'].includes(values.channel_type)) {
        payload.webhook_url = values.webhook_url || null
      }

      if (values.channel_type === 'telegram') {
        payload.telegram_bot_token = values.telegram_bot_token || null
        payload.telegram_chat_id = values.telegram_chat_id || null
      }

      if (values.channel_type === 'email') {
        payload.email_config = {
          smtp_server: values.smtp_server || null,
          smtp_port: values.smtp_port ? parseInt(values.smtp_port) : null,
          smtp_user: values.smtp_user || null,
          smtp_password: values.smtp_password || null,
          from_address: values.from_address || null,
          to_addresses: values.to_addresses_str
            ? values.to_addresses_str.split(',').map(e => e.trim()).filter(Boolean)
            : [],
        }
      }

      if (isEdit && config) {
        await updateMutation.mutateAsync({
          id: config.id,
          data: payload,
        })
      } else {
        await createMutation.mutateAsync(payload)
      }
      onOpenChange(false)
    } catch (e) {
      // Errors handled by React Query onError toast
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white rounded-xl shadow-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold tracking-tight bg-gradient-to-r from-primary to-emerald-400 bg-clip-text text-transparent">
            {isEdit ? 'Edit Alert Integration' : 'Add Alert Integration'}
          </DialogTitle>
          <DialogDescription className="text-slate-600 dark:text-slate-400 text-sm">
            Route anomaly notifications and schema violations to your preferred operations channel.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* Name Field */}
          <div className="space-y-1">
            <Label htmlFor="name" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
              Configuration Name
            </Label>
            <Input
              id="name"
              placeholder="e.g. Ops Telegram Alerts"
              className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9"
              {...register('name')}
            />
            {errors.name && (
              <p className="text-xs text-rose-500 font-medium">{errors.name.message}</p>
            )}
          </div>

          {/* Grid: Channel Type & Severity */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                Channel Type
              </Label>
              <Select
                value={channelType}
                onValueChange={(val) => setValue('channel_type', val as any)}
              >
                <SelectTrigger className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 text-slate-800 dark:text-white text-xs h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-white dark:bg-slate-900 border-slate-200 dark:border-white/10 text-slate-800 dark:text-white text-xs">
                  <SelectItem value="slack">Slack Webhook</SelectItem>
                  <SelectItem value="discord">Discord Webhook</SelectItem>
                  <SelectItem value="teams">MS Teams Webhook</SelectItem>
                  <SelectItem value="telegram">Telegram Bot</SelectItem>
                  <SelectItem value="email">Email SMTP</SelectItem>
                  <SelectItem value="ntfy">Ntfy Service</SelectItem>
                  <SelectItem value="webhook">Custom Webhook</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                Min Severity Threshold
              </Label>
              <Select
                defaultValue="MEDIUM"
                value={watch('severity_threshold')}
                onValueChange={(val) => setValue('severity_threshold', val as any)}
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
          </div>

          {/* Active Status Switch */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-950/30 border border-slate-200 dark:border-white/5">
            <div className="space-y-0.5">
              <Label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Active status</Label>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">
                Toggle whether alerts should be dispatched to this channel.
              </p>
            </div>
            <Switch
              checked={isActive}
              onCheckedChange={(checked) => setValue('is_active', checked)}
              className="data-[state=checked]:bg-primary"
            />
          </div>

          {/* Webhook URLs (Slack, Discord, Teams, Custom Webhook) */}
          {['slack', 'discord', 'teams', 'webhook'].includes(channelType) && (
            <div className="space-y-1 border-t border-slate-100 dark:border-white/5 pt-3">
              <Label htmlFor="webhook_url" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                {channelType === 'webhook' ? 'Webhook Endpoint URL' : `${channelType.toUpperCase()} Webhook URL`}
              </Label>
              <Input
                id="webhook_url"
                type="url"
                placeholder="https://..."
                className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9 font-mono"
                {...register('webhook_url')}
              />
              {errors.webhook_url && (
                <p className="text-xs text-rose-500 font-medium">{errors.webhook_url.message}</p>
              )}
            </div>
          )}

          {/* Telegram bot configurations */}
          {channelType === 'telegram' && (
            <div className="space-y-3 border-t border-slate-100 dark:border-white/5 pt-3">
              <div className="space-y-1">
                <Label htmlFor="telegram_bot_token" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                  Telegram Bot Token
                </Label>
                <Input
                  id="telegram_bot_token"
                  placeholder="e.g. 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
                  className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9 font-mono"
                  {...register('telegram_bot_token')}
                />
                {errors.telegram_bot_token && (
                  <p className="text-xs text-rose-500 font-medium">{errors.telegram_bot_token.message}</p>
                )}
              </div>
              <div className="space-y-1">
                <Label htmlFor="telegram_chat_id" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                  Telegram Chat ID
                </Label>
                <Input
                  id="telegram_chat_id"
                  placeholder="e.g. -100123456789"
                  className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9 font-mono"
                  {...register('telegram_chat_id')}
                />
                {errors.telegram_chat_id && (
                  <p className="text-xs text-rose-500 font-medium">{errors.telegram_chat_id.message}</p>
                )}
              </div>
            </div>
          )}

          {/* Email SMTP configurations */}
          {channelType === 'email' && (
            <div className="space-y-3 border-t border-slate-100 dark:border-white/5 pt-3">
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2 space-y-1">
                  <Label htmlFor="smtp_server" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                    SMTP Host
                  </Label>
                  <Input
                    id="smtp_server"
                    placeholder="e.g. smtp.gmail.com"
                    className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9"
                    {...register('smtp_server')}
                  />
                  {errors.smtp_server && (
                    <p className="text-xs text-rose-500 font-medium">{errors.smtp_server.message}</p>
                  )}
                </div>
                <div className="space-y-1">
                  <Label htmlFor="smtp_port" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                    SMTP Port
                  </Label>
                  <Input
                    id="smtp_port"
                    placeholder="e.g. 587"
                    className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9"
                    {...register('smtp_port')}
                  />
                  {errors.smtp_port && (
                    <p className="text-xs text-rose-500 font-medium">{errors.smtp_port.message}</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label htmlFor="smtp_user" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                    SMTP User (Optional)
                  </Label>
                  <Input
                    id="smtp_user"
                    placeholder="User/Email"
                    className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9"
                    {...register('smtp_user')}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="smtp_password" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                    SMTP Password (Optional)
                  </Label>
                  <Input
                    id="smtp_password"
                    type="password"
                    placeholder="••••••••"
                    className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9"
                    {...register('smtp_password')}
                  />
                </div>
              </div>

              <div className="space-y-1">
                <Label htmlFor="from_address" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                  Sender (From Email Address)
                </Label>
                <Input
                  id="from_address"
                  type="email"
                  placeholder="alerts@yourdomain.com"
                  className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs h-9"
                  {...register('from_address')}
                />
                {errors.from_address && (
                  <p className="text-xs text-rose-500 font-medium">{errors.from_address.message}</p>
                )}
              </div>

              <div className="space-y-1">
                <Label htmlFor="to_addresses_str" className="text-xs font-semibold uppercase tracking-wider text-slate-550 dark:text-slate-400">
                  Recipients (Comma separated)
                </Label>
                <Textarea
                  id="to_addresses_str"
                  placeholder="operator1@org.com, devops@org.com"
                  rows={2}
                  className="bg-slate-50 dark:bg-slate-950/50 border-slate-200 dark:border-white/10 focus:border-primary/50 text-slate-800 dark:text-white text-xs p-2.5 resize-none"
                  {...register('to_addresses_str')}
                />
                {errors.to_addresses_str && (
                  <p className="text-xs text-rose-500 font-medium">{errors.to_addresses_str.message}</p>
                )}
              </div>
            </div>
          )}

          {channelType === 'ntfy' && (
            <div className="p-3 bg-slate-50 dark:bg-slate-950/40 border border-slate-200 dark:border-white/5 rounded-lg text-xs text-slate-600 dark:text-slate-400 leading-relaxed space-y-1 mt-3">
              <span className="font-bold text-slate-800 dark:text-slate-300">Ntfy Service Alert:</span>
              <p>
                Using ntfy does not require custom credentials. When triggered, the system publishes notifications to the global Ntfy topic configured on this Qolyx deployment.
              </p>
            </div>
          )}

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
              disabled={isSubmitting || createMutation.isPending || updateMutation.isPending}
              className="bg-primary hover:bg-primary/80 text-white font-semibold text-xs h-9 px-4 min-w-[100px]"
            >
              {isEdit ? 'Save Changes' : 'Add Integration'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

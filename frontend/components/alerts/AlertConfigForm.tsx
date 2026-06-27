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
      <DialogContent className="max-w-lg bg-popover border border-border text-popover-foreground rounded-xl shadow-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold tracking-tight bg-gradient-to-r from-primary to-emerald-400 bg-clip-text text-transparent">
            {isEdit ? 'Edit Alert Integration' : 'Add Alert Integration'}
          </DialogTitle>
          <DialogDescription className="text-muted-foreground text-sm">
            Route anomaly notifications and schema violations to your preferred operations channel.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* Name Field */}
          <div className="space-y-1">
            <Label htmlFor="name" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Configuration Name
            </Label>
            <Input
              id="name"
              placeholder="e.g. Ops Telegram Alerts"
              className="bg-background border-border text-foreground text-xs h-9"
              {...register('name')}
            />
            {errors.name && (
              <p className="text-xs text-rose-500 font-medium">{errors.name.message}</p>
            )}
          </div>

          {/* Grid: Channel Type & Severity */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Channel Type
              </Label>
              <Select
                value={channelType}
                onValueChange={(val) => setValue('channel_type', val as any)}
              >
                <SelectTrigger className="bg-background border-border text-foreground text-xs h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                  <SelectItem value="slack" className="cursor-pointer focus:bg-accent focus:text-accent-foreground">Slack Webhook</SelectItem>
                  <SelectItem value="discord" className="cursor-pointer focus:bg-accent focus:text-accent-foreground">Discord Webhook</SelectItem>
                  <SelectItem value="teams" className="cursor-pointer focus:bg-accent focus:text-accent-foreground">MS Teams Webhook</SelectItem>
                  <SelectItem value="telegram" className="cursor-pointer focus:bg-accent focus:text-accent-foreground">Telegram Bot</SelectItem>
                  <SelectItem value="email" className="cursor-pointer focus:bg-accent focus:text-accent-foreground">Email SMTP</SelectItem>
                  <SelectItem value="ntfy" className="cursor-pointer focus:bg-accent focus:text-accent-foreground">Ntfy Service</SelectItem>
                  <SelectItem value="webhook" className="cursor-pointer focus:bg-accent focus:text-accent-foreground">Custom Webhook</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Min Severity Threshold
              </Label>
              <Select
                defaultValue="MEDIUM"
                value={watch('severity_threshold')}
                onValueChange={(val) => setValue('severity_threshold', val as any)}
              >
                <SelectTrigger className="bg-background border-border text-foreground text-xs h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                  <SelectItem value="LOW" className="cursor-pointer focus:bg-accent focus:text-accent-foreground">LOW</SelectItem>
                  <SelectItem value="MEDIUM" className="cursor-pointer focus:bg-accent focus:text-accent-foreground">MEDIUM</SelectItem>
                  <SelectItem value="HIGH" className="cursor-pointer focus:bg-accent focus:text-accent-foreground">HIGH</SelectItem>
                  <SelectItem value="CRITICAL" className="cursor-pointer focus:bg-accent focus:text-accent-foreground">CRITICAL</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Active Status Switch */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border">
            <div className="space-y-0.5">
              <Label className="text-xs font-semibold text-foreground">Active status</Label>
              <p className="text-[10px] text-muted-foreground">
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
            <div className="space-y-1 border-t border-border pt-3">
              <Label htmlFor="webhook_url" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {channelType === 'webhook' ? 'Webhook Endpoint URL' : `${channelType.toUpperCase()} Webhook URL`}
              </Label>
              <Input
                id="webhook_url"
                type="url"
                placeholder="https://..."
                className="bg-background border-border text-foreground text-xs h-9 font-mono"
                {...register('webhook_url')}
              />
              {errors.webhook_url && (
                <p className="text-xs text-rose-500 font-medium">{errors.webhook_url.message}</p>
              )}
            </div>
          )}

          {/* Telegram bot configurations */}
          {channelType === 'telegram' && (
            <div className="space-y-3 border-t border-border pt-3">
              <div className="space-y-1">
                <Label htmlFor="telegram_bot_token" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Telegram Bot Token
                </Label>
                <Input
                  id="telegram_bot_token"
                  placeholder="e.g. 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
                  className="bg-background border-border text-foreground text-xs h-9 font-mono"
                  {...register('telegram_bot_token')}
                />
                {errors.telegram_bot_token && (
                  <p className="text-xs text-rose-500 font-medium">{errors.telegram_bot_token.message}</p>
                )}
              </div>
              <div className="space-y-1">
                <Label htmlFor="telegram_chat_id" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Telegram Chat ID
                </Label>
                <Input
                  id="telegram_chat_id"
                  placeholder="e.g. -100123456789"
                  className="bg-background border-border text-foreground text-xs h-9 font-mono"
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
            <div className="space-y-3 border-t border-border pt-3">
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2 space-y-1">
                  <Label htmlFor="smtp_server" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    SMTP Host
                  </Label>
                  <Input
                    id="smtp_server"
                    placeholder="e.g. smtp.gmail.com"
                    className="bg-background border-border text-foreground text-xs h-9"
                    {...register('smtp_server')}
                  />
                  {errors.smtp_server && (
                    <p className="text-xs text-rose-500 font-medium">{errors.smtp_server.message}</p>
                  )}
                </div>
                <div className="space-y-1">
                  <Label htmlFor="smtp_port" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    SMTP Port
                  </Label>
                  <Input
                    id="smtp_port"
                    placeholder="e.g. 587"
                    className="bg-background border-border text-foreground text-xs h-9"
                    {...register('smtp_port')}
                  />
                  {errors.smtp_port && (
                    <p className="text-xs text-rose-500 font-medium">{errors.smtp_port.message}</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label htmlFor="smtp_user" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    SMTP User (Optional)
                  </Label>
                  <Input
                    id="smtp_user"
                    placeholder="User/Email"
                    className="bg-background border-border text-foreground text-xs h-9"
                    {...register('smtp_user')}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="smtp_password" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    SMTP Password (Optional)
                  </Label>
                  <Input
                    id="smtp_password"
                    type="password"
                    placeholder="••••••••"
                    className="bg-background border-border text-foreground text-xs h-9"
                    {...register('smtp_password')}
                  />
                </div>
              </div>

              <div className="space-y-1">
                <Label htmlFor="from_address" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Sender (From Email Address)
                </Label>
                <Input
                  id="from_address"
                  type="email"
                  placeholder="alerts@yourdomain.com"
                  className="bg-background border-border text-foreground text-xs h-9"
                  {...register('from_address')}
                />
                {errors.from_address && (
                  <p className="text-xs text-rose-500 font-medium">{errors.from_address.message}</p>
                )}
              </div>

              <div className="space-y-1">
                <Label htmlFor="to_addresses_str" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Recipients (Comma separated)
                </Label>
                <Textarea
                  id="to_addresses_str"
                  placeholder="operator1@org.com, devops@org.com"
                  rows={2}
                  className="bg-background border-border text-foreground text-xs p-2.5 resize-none"
                  {...register('to_addresses_str')}
                />
                {errors.to_addresses_str && (
                  <p className="text-xs text-rose-500 font-medium">{errors.to_addresses_str.message}</p>
                )}
              </div>
            </div>
          )}

          {channelType === 'ntfy' && (
            <div className="p-3 bg-muted/30 border border-border rounded-lg text-xs text-muted-foreground leading-relaxed space-y-1 mt-3">
              <span className="font-bold text-foreground">Ntfy Service Alert:</span>
              <p>
                Using ntfy does not require custom credentials. When triggered, the system publishes notifications to the global Ntfy topic configured on this Qolyx deployment.
              </p>
            </div>
          )}

          <DialogFooter className="gap-2 sm:gap-0 pt-4 border-t border-border">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              className="hover:bg-accent text-muted-foreground hover:text-accent-foreground"
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

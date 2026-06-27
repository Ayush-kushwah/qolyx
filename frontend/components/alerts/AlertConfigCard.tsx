'use client'

import React from 'react'
import { AlertConfig } from '@/types'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import {
  Mail,
  Send,
  Link as LinkIcon,
  Smartphone,
  Edit3,
  Trash2,
  Play,
  Loader2
} from 'lucide-react'

interface AlertConfigCardProps {
  config: AlertConfig
  onToggle: (id: string, isActive: boolean) => void
  onTest: (id: string) => void
  onEdit: (config: AlertConfig) => void
  onDelete: (id: string) => void
  isTesting: boolean
}

export default function AlertConfigCard({
  config,
  onToggle,
  onTest,
  onEdit,
  onDelete,
  isTesting
}: AlertConfigCardProps) {
  
  // Get channel icon helper
  const getChannelIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'email':
        return <Mail className="h-4 w-4 text-emerald-400" />
      case 'telegram':
        return <Send className="h-4 w-4 text-sky-400" />
      case 'ntfy':
        return <Smartphone className="h-4 w-4 text-orange-400" />
      case 'slack':
      case 'discord':
      case 'teams':
      case 'webhook':
      default:
        return <LinkIcon className="h-4 w-4 text-emerald-400" />
    }
  }

  // Render specific detail properties
  const renderChannelDetails = () => {
    const { channel_type, webhook_url, telegram_bot_token, telegram_chat_id, email_config } = config

    if (['slack', 'discord', 'teams', 'webhook'].includes(channel_type.toLowerCase())) {
      const displayUrl = webhook_url 
        ? webhook_url.length > 35 
          ? `${webhook_url.slice(0, 20)}...${webhook_url.slice(-10)}` 
          : webhook_url
        : 'Not Configured'
      return (
        <div className="text-[11px] text-muted-foreground font-mono flex flex-col gap-0.5">
          <span className="text-[9px] font-bold text-muted-foreground uppercase">Webhook URL</span>
          <span className="truncate text-foreground font-semibold" title={webhook_url || ''}>{displayUrl}</span>
        </div>
      )
    }

    if (channel_type.toLowerCase() === 'telegram') {
      const maskedToken = telegram_bot_token
        ? telegram_bot_token.length > 20
          ? `${telegram_bot_token.slice(0, 10)}...${telegram_bot_token.slice(-6)}`
          : telegram_bot_token
        : 'Not Configured'
      return (
        <div className="text-[11px] text-muted-foreground font-mono flex flex-col gap-1">
          <div>
            <span className="text-[9px] font-bold text-muted-foreground uppercase block">Bot Token</span>
            <span className="text-foreground font-semibold">{maskedToken}</span>
          </div>
          <div>
            <span className="text-[9px] font-bold text-muted-foreground uppercase block">Chat ID</span>
            <span className="text-foreground font-semibold">{telegram_chat_id || 'Not Configured'}</span>
          </div>
        </div>
      )
    }

    if (channel_type.toLowerCase() === 'email') {
      const smtpServer = email_config?.smtp_server || 'system-default'
      const smtpPort = email_config?.smtp_port || 587
      const rawRecipients = email_config?.to_addresses
      const recipients = Array.isArray(rawRecipients) 
        ? rawRecipients.join(', ') 
        : (typeof rawRecipients === 'string' ? rawRecipients : 'None')
      const displayRecipients = recipients.length > 30 ? `${recipients.slice(0, 27)}...` : recipients

      return (
        <div className="text-[11px] text-muted-foreground flex flex-col gap-1 font-semibold">
          <div>
            <span className="text-[9px] font-mono font-bold text-muted-foreground uppercase block">Recipients</span>
            <span className="truncate text-foreground" title={recipients}>{displayRecipients}</span>
          </div>
          <div className="flex gap-4 font-mono text-[10px]">
            <div>
              <span className="text-[9px] font-bold text-muted-foreground uppercase">SMTP Server</span>
              <div className="truncate text-muted-foreground">{smtpServer}:{smtpPort}</div>
            </div>
          </div>
        </div>
      )
    }

    if (channel_type.toLowerCase() === 'ntfy') {
      return (
        <div className="text-[11px] text-muted-foreground leading-normal flex flex-col gap-0.5 font-semibold">
          <span className="text-[9px] font-bold text-muted-foreground uppercase">Subscription mode</span>
          <span className="text-foreground">Uses personal subscriber topic alerts.</span>
        </div>
      )
    }

    return null
  }

  return (
    <div
      className={`glass-panel p-5 rounded-xl border relative transition-all hover:scale-[1.01] hover:border-muted-foreground/30 flex flex-col justify-between min-h-[175px] ${
        config.is_active 
          ? 'border-border bg-card' 
          : 'border-dashed border-border opacity-60 bg-transparent'
      }`}
    >
      {/* Header Info */}
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-muted rounded border border-border flex items-center justify-center">
              {getChannelIcon(config.channel_type)}
            </div>
            <h3 className="font-bold text-foreground text-sm tracking-tight leading-tight line-clamp-1">
              {config.name}
            </h3>
          </div>

          <Switch
            checked={config.is_active}
            onCheckedChange={(checked) => onToggle(config.id, checked)}
            className="scale-75"
          />
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" className="bg-muted text-[9px] font-bold text-muted-foreground border-border py-0.5 uppercase tracking-wide">
            {config.channel_type}
          </Badge>
          <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 text-[9px] font-bold py-0.5 uppercase tracking-wide">
            Min Threshold: {config.severity_threshold}
          </Badge>
        </div>
      </div>

      {/* Channel specific configs */}
      <div className="bg-muted/30 p-2.5 rounded-lg border border-border mt-4 min-h-[60px] flex flex-col justify-center">
        {renderChannelDetails()}
      </div>

      {/* Footer Controls */}
      <div className="flex items-center justify-between border-t border-border pt-3 mt-4">
        <Button
          size="sm"
          variant="outline"
          onClick={() => onTest(config.id)}
          disabled={isTesting}
          className="h-8 px-2.5 text-primary hover:text-white border-primary/20 bg-primary/10 hover:bg-primary/20 text-xs font-bold gap-1"
        >
          {isTesting ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Play className="h-3 w-3 fill-current" />
          )}
          Test Channel
        </Button>

        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="outline"
            onClick={() => onEdit(config)}
            className="h-8 px-3 border-border text-muted-foreground hover:bg-accent hover:text-accent-foreground text-xs font-bold gap-1"
          >
            <Edit3 className="h-3.5 w-3.5" />
            Configure
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onDelete(config.id)}
            className="h-8 w-8 p-0 border-border text-muted-foreground hover:bg-rose-500/10 hover:text-rose-500"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  )
}

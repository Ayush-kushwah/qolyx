'use client'

import React from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Check, Copy, Download, Loader2, Shield } from 'lucide-react'

interface NtfySectionProps {
  topic: string
  qrCode: string
  onCopyTopic: () => void
  onDownloadQR: () => void
}

export default function NtfySection({
  topic,
  qrCode,
  onCopyTopic,
  onDownloadQR
}: NtfySectionProps) {
  const isGenerating = !topic || !qrCode

  return (
    <div className="glass-panel p-5 rounded-xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-slate-900/10 flex flex-col md:flex-row items-center gap-6 select-none">
      {/* Instructions & Details */}
      <div className="flex-1 space-y-3">
        <Badge className="bg-orange-500/10 text-orange-400 border-orange-500/20 text-[9px] font-bold py-0.5 uppercase tracking-wider">
          📱 NTFY Mobile Notifications
        </Badge>
        <h2 className="text-base font-extrabold text-slate-800 dark:text-slate-200">Subscribe on your Mobile Device</h2>
        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
          Get real-time push notifications on your phone — no accounts, no setup required. Download the free ntfy app, scan the QR code to subscribe, and you will automatically receive Qolyx alerts.
        </p>
        
        {/* Setup steps */}
        <div className="space-y-1 text-xs text-slate-600 dark:text-slate-400">
          <p>1. Download Ntfy app from <a href="https://apps.apple.com/us/app/ntfy/id1613581534" target="_blank" rel="noreferrer" className="text-primary hover:underline font-semibold">App Store</a> or <a href="https://play.google.com/store/apps/details?id=io.heckel.ntfy" target="_blank" rel="noreferrer" className="text-primary hover:underline font-semibold">Play Store</a>.</p>
          <p>2. Scan the QR code or subscribe manually to your topic.</p>
        </div>

        {/* Topic details */}
        <div className="space-y-2 pt-1.5 text-xs text-slate-700 dark:text-slate-300">
          <div className="flex items-center gap-2">
            <Check className="h-3.5 w-3.5 text-healthy flex-shrink-0" />
            <span>
              Your personal topic: <code className="font-mono text-amber-600 dark:text-amber-400 font-bold bg-slate-200/50 dark:bg-slate-950/40 px-1.5 py-0.5 rounded">{topic || 'Generating...'}</code>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Shield className="h-3.5 w-3.5 text-primary flex-shrink-0" />
            <span className="text-[10px] text-slate-600 dark:text-slate-500 leading-normal">
              🔒 This channel is private to you. Share the QR code with your team to add them to the same alerts.
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2 pt-2">
          <Button
            size="sm"
            variant="outline"
            onClick={onCopyTopic}
            disabled={isGenerating}
            className="h-8 border-slate-200 dark:border-white/5 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 text-xs font-bold gap-1.5"
          >
            <Copy className="h-3.5 w-3.5" />
            Copy Topic
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onDownloadQR}
            disabled={isGenerating}
            className="h-8 border-slate-200 dark:border-white/5 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 text-xs font-bold gap-1.5"
          >
            <Download className="h-3.5 w-3.5" />
            Download QR Code
          </Button>
        </div>
      </div>

      {/* QR Code Container */}
      <div className="flex-shrink-0 bg-white p-2.5 rounded-xl border border-slate-200 dark:border-white/10 flex items-center justify-center min-w-[130px] min-h-[130px] shadow-xl relative select-none">
        {isGenerating ? (
          <div className="flex flex-col items-center gap-1">
            <Loader2 className="h-5 w-5 text-slate-900 animate-spin" />
            <span className="text-[9px] text-slate-500 font-semibold uppercase">Generating...</span>
          </div>
        ) : (
          <img
            src={qrCode}
            alt="Ntfy Subscription QR Code"
            className="h-28 w-28 object-contain"
          />
        )}
      </div>
    </div>
  )
}

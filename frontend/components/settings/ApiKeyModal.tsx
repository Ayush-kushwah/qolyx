'use client'

import React from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Copy, Check, Eye, AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'

interface ApiKeyModalProps {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  apiKey: string
  keyName: string
}

export default function ApiKeyModal({ isOpen, onOpenChange, apiKey, keyName }: ApiKeyModalProps) {
  const [copied, setCopied] = React.useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey)
    setCopied(true)
    toast.success('API Key copied to clipboard!')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px] bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl font-bold text-amber-500">
            <AlertTriangle className="h-5 w-5" />
            Save Your API Key
          </DialogTitle>
          <DialogDescription className="text-slate-500 dark:text-slate-400">
            Copy this token now. For security reasons, <strong className="text-rose-500 font-bold">you cannot see it again</strong> after closing this window.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-1">
            <Label className="text-xs text-slate-400">Key Name</Label>
            <p className="text-sm font-semibold">{keyName}</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="raw-key-value">API Key Token</Label>
            <div className="flex gap-2">
              <Input
                id="raw-key-value"
                readOnly
                value={apiKey}
                className="font-mono text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex-1 select-all"
              />
              <Button onClick={handleCopy} size="icon" variant="outline" className="border-slate-200 dark:border-slate-800">
                {copied ? <Check className="h-4 w-4 text-healthy" /> : <Copy className="h-4 w-4" />}
              </Button>
            </div>
          </div>
          <div className="p-3.5 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-500 flex items-start gap-2.5">
            <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              Treat this key as a password. Sharing or exposing this key online allows full write and admin access to your Qolyx reliability data pipelines.
            </p>
          </div>
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button className="w-full bg-primary hover:bg-primary/95 text-white">
              I have saved this API Key
            </Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

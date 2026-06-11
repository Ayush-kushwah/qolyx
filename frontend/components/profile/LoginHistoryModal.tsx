'use client'

import React, { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { History, ShieldCheck, ShieldX } from 'lucide-react'
import { useLoginHistory } from '@/hooks/useProfile'

export default function LoginHistoryModal() {
  const [open, setOpen] = useState(false)
  const { data: history, isLoading, isError } = useLoginHistory()

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="flex items-center gap-2 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
          <History className="h-4 w-4" />
          <span>Login History</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl font-bold">
            <History className="h-5 w-5 text-primary" />
            Login Audit History
          </DialogTitle>
          <DialogDescription className="text-slate-500 dark:text-slate-400">
            A history of recent login attempts to monitor for unauthorized access.
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-12 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-lg" />
              ))}
            </div>
          ) : isError ? (
            <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-500 text-sm">
              Failed to load login audit history.
            </div>
          ) : !history || history.length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-6">No recent login history recorded.</p>
          ) : (
            <div className="border border-slate-100 dark:border-slate-800 rounded-lg overflow-hidden">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-950 border-b border-slate-100 dark:border-slate-800 text-slate-500 uppercase font-semibold">
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Device / Browser</th>
                    <th className="px-4 py-3">Location & IP</th>
                    <th className="px-4 py-3">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {history.map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-50/50 dark:hover:bg-white/5">
                      <td className="px-4 py-3.5">
                        {entry.success ? (
                          <span className="flex items-center gap-1 text-healthy font-semibold">
                            <ShieldCheck className="h-4 w-4" />
                            <span>Success</span>
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-rose-500 font-semibold">
                            <ShieldX className="h-4 w-4" />
                            <span>Failed</span>
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="font-medium">{entry.device || 'Unknown Device'}</div>
                        <div className="text-slate-400 dark:text-slate-500 text-[10px]">{entry.browser || 'Unknown Browser'}</div>
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="font-medium">{entry.location || 'Unknown Location'}</div>
                        <div className="text-slate-400 dark:text-slate-500 text-[10px]">{entry.ip_address}</div>
                      </td>
                      <td className="px-4 py-3.5 text-slate-500 dark:text-slate-400">
                        {new Date(entry.timestamp).toLocaleString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit'
                        })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

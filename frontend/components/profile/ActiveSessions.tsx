'use client'

import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Laptop, Smartphone, MapPin, Globe, ShieldAlert } from 'lucide-react'
import { useSessions, useRevokeSession, useRevokeAllSessions } from '@/hooks/useProfile'

export default function ActiveSessions() {
  const { data: sessions, isLoading, isError } = useSessions()
  const revokeSessionMutation = useRevokeSession()
  const revokeAllSessionsMutation = useRevokeAllSessions()

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2].map((i) => (
          <div key={i} className="h-24 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-lg" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-500 text-sm">
        Failed to load active login sessions.
      </div>
    )
  }

  const activeSessions = sessions?.filter((s) => s.is_active) || []

  return (
    <Card className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div>
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <Globe className="h-5 w-5 text-primary" />
            Active Login Sessions
          </CardTitle>
          <CardDescription className="text-slate-500 dark:text-slate-400">
            These are the devices and locations currently logged into your account.
          </CardDescription>
        </div>
        {activeSessions.length > 1 && (
          <Button
            variant="destructive"
            size="sm"
            onClick={() => revokeAllSessionsMutation.mutate()}
            disabled={revokeAllSessionsMutation.isPending}
            className="flex items-center gap-1.5"
          >
            <ShieldAlert className="h-3.5 w-3.5" />
            <span>Revoke All Others</span>
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {activeSessions.length === 0 ? (
          <p className="text-sm text-slate-500">No active login sessions found.</p>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {activeSessions.map((session) => (
              <div key={session.id} className="flex items-center justify-between py-4 first:pt-0 last:pb-0">
                <div className="flex items-start gap-4">
                  <div className="p-2.5 bg-slate-100 dark:bg-slate-800 rounded-lg text-slate-700 dark:text-slate-300">
                    {session.device?.toLowerCase().includes('iphone') || session.device?.toLowerCase().includes('android') ? (
                      <Smartphone className="h-5 w-5" />
                    ) : (
                      <Laptop className="h-5 w-5" />
                    )}
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold">{session.device || 'Unknown Device'}</p>
                      <span className="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-healthy/10 border border-healthy/20 text-healthy">
                        Current Session
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                      <span>{session.browser || 'Unknown Browser'}</span>
                      <span>•</span>
                      <span>IP: {session.ip_address}</span>
                    </p>
                    <p className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      <span>{session.location || 'Unknown Location'}</span>
                      <span>•</span>
                      <span>Last active: {new Date(session.last_active_at).toLocaleTimeString()}</span>
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => revokeSessionMutation.mutate(session.id)}
                  disabled={revokeSessionMutation.isPending}
                  className="text-slate-500 hover:text-rose-500 hover:bg-rose-500/10 dark:hover:bg-rose-500/20"
                >
                  Revoke
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

'use client'

import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Download } from 'lucide-react'
import { useRequestDataExport } from '@/hooks/useProfile'

export default function DataExport() {
  const exportMutation = useRequestDataExport()

  return (
    <Card className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
      <CardHeader>
        <CardTitle className="text-lg font-bold flex items-center gap-2">
          <Download className="h-5 w-5 text-primary" />
          Export Personal Data
        </CardTitle>
        <CardDescription className="text-slate-500 dark:text-slate-400">
          Request a full download of your profile data, active sessions, and settings history in JSON format.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md">
            This export contains settings, preferences, registered integrations, and audit activity. Files are generated securely in real-time.
          </p>
          <Button
            onClick={() => exportMutation.mutate()}
            disabled={exportMutation.isPending}
            className="bg-primary hover:bg-primary/95 text-white flex items-center gap-2 whitespace-nowrap self-end sm:self-center"
          >
            {exportMutation.isPending ? (
              <span>Compiling archive...</span>
            ) : (
              <>
                <Download className="h-4 w-4" />
                <span>Export Profile Data</span>
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

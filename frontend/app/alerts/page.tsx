'use client'

import React, { useState } from 'react'
import {
  useAlertConfigs,
  useUpdateAlertConfig,
  useDeleteAlertConfig,
  useTestAlertConfig,
  useNtfyQRCode
} from '@/hooks/useAlertConfigs'
import { AlertConfig } from '@/types'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorBoundary from '@/components/common/ErrorBoundary'
import EmptyState from '@/components/common/EmptyState'
import AlertConfigForm from '@/components/alerts/AlertConfigForm'
import AlertConfigCard from '@/components/alerts/AlertConfigCard'
import NtfySection from '@/components/alerts/NtfySection'

import {
  Bell,
  Plus,
  AlertTriangle,
  Loader2,
  Play
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog'
import { toast } from 'sonner'

export default function AlertsPage() {
  const { data: configs = [], isLoading, isError, error, refetch } = useAlertConfigs()
  const { data: ntfyData, isLoading: isLoadingNtfy } = useNtfyQRCode()

  const updateMutation = useUpdateAlertConfig()
  const deleteMutation = useDeleteAlertConfig()
  const testMutation = useTestAlertConfig()

  // Form Modal & Dialog States
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [selectedConfig, setSelectedConfig] = useState<AlertConfig | null>(null)
  
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [targetDeleteId, setTargetDeleteId] = useState<string | null>(null)

  const [isTestDialogOpen, setIsTestDialogOpen] = useState(false)
  const [testChannelType, setTestChannelType] = useState('')
  const [testingConfigId, setTestingConfigId] = useState<string | null>(null)
  const [testMessage, setTestMessage] = useState('Manual reliability test alert dispatched from Qolyx Operator Panel.')

  // Open form to create a new alert configuration
  const handleAddConfig = () => {
    setSelectedConfig(null)
    setIsFormOpen(true)
  }

  // Open form to edit an existing alert configuration
  const handleEditConfig = (config: AlertConfig) => {
    setSelectedConfig(config)
    setIsFormOpen(true)
  }

  // Toggle config active status
  const handleToggleActive = (id: string, isActive: boolean) => {
    updateMutation.mutate({
      id,
      data: {
        is_active: isActive
      }
    })
  }

  // Copy Ntfy topic to clipboard
  const handleCopyTopic = () => {
    if (ntfyData?.topic) {
      navigator.clipboard.writeText(ntfyData.topic)
      toast.success('Ntfy Topic ID copied to clipboard!')
    }
  }

  // Download Ntfy QR code as PNG image
  const handleDownloadQR = () => {
    if (ntfyData?.qr_code) {
      const link = document.createElement('a')
      link.href = ntfyData.qr_code
      link.download = `qolyx_ntfy_${ntfyData.topic || 'topic'}.png`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      toast.success('QR Code downloaded successfully!')
    }
  }

  // Trigger test alert modal
  const handleTriggerTest = (id: string) => {
    const targetConfig = configs.find(c => c.id === id)
    if (!targetConfig) return

    setTestChannelType(targetConfig.channel_type)
    setTestingConfigId(id)
    setTestMessage('Manual reliability test alert dispatched from Qolyx Operator Panel.')
    setIsTestDialogOpen(true)
  }

  // Dispatch manual test alert
  const handleSendTest = (e: React.FormEvent) => {
    e.preventDefault()
    if (!testMessage.trim()) return

    testMutation.mutate({
      channelType: testChannelType,
      message: testMessage
    }, {
      onSuccess: () => {
        setIsTestDialogOpen(false)
        setTestingConfigId(null)
      },
      onError: () => {
        setTestingConfigId(null)
      }
    })
  }

  // Trigger delete dialog
  const triggerDelete = (id: string) => {
    setTargetDeleteId(id)
    setIsDeleteDialogOpen(true)
  }

  // Confirm delete alert configuration
  const executeDelete = () => {
    if (targetDeleteId) {
      deleteMutation.mutate(targetDeleteId, {
        onSuccess: () => {
          setIsDeleteDialogOpen(false)
          setTargetDeleteId(null)
        }
      })
    }
  }

  return (
    <ErrorBoundary>
      <div className="space-y-8 select-none">
        
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-400 bg-clip-text text-transparent flex items-center gap-2">
              <Bell className="h-7 w-7 text-primary" />
              Alert Configurations
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Configure notification channels for Trust Score breaches and anomalies.
            </p>
          </div>

          <Button
            onClick={handleAddConfig}
            className="shadow-lg hover:shadow-primary/20 text-xs font-bold gap-1.5 h-9 self-start sm:self-center"
          >
            <Plus className="h-4 w-4" />
            Add Channel
          </Button>
        </div>

        {/* Ntfy Mobile Integration Section */}
        <NtfySection
          topic={ntfyData?.topic || ''}
          qrCode={ntfyData?.qr_code || ''}
          onCopyTopic={handleCopyTopic}
          onDownloadQR={handleDownloadQR}
        />

        {/* Alert Channels List Section */}
        {isLoading ? (
          <div className="py-24">
            <LoadingSpinner text="Retrieving Active Alert Integrations..." />
          </div>
        ) : isError ? (
          <EmptyState
            title="Error Loading Alerts"
            description={error instanceof Error ? error.message : 'Failed to retrieve active integrations.'}
            icon={AlertTriangle}
            action={{
              label: 'Retry',
              onClick: () => refetch()
            }}
          />
        ) : configs.length === 0 ? (
          <EmptyState
            title="No Alert Integrations Configured"
            description="Operational alerts will not be routed. Hook up a Slack, Telegram, or Email integration to start."
            icon={Bell}
            action={{
              label: 'Add First Channel',
              onClick: handleAddConfig
            }}
          />
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {configs.map((config) => (
              <AlertConfigCard
                key={config.id}
                config={config}
                onToggle={handleToggleActive}
                onTest={handleTriggerTest}
                onEdit={handleEditConfig}
                onDelete={triggerDelete}
                isTesting={testMutation.isPending && testingConfigId === config.id}
              />
            ))}
          </div>
        )}

        {/* ==========================================
            ADD/EDIT ALERT CONFIGURATION DIALOG
            ========================================== */}
        <AlertConfigForm
          open={isFormOpen}
          onOpenChange={setIsFormOpen}
          config={selectedConfig}
        />

        {/* ==========================================
            MANUAL TEST ALERT DIALOG
            ========================================== */}
        <Dialog open={isTestDialogOpen} onOpenChange={setIsTestDialogOpen}>
          <DialogContent className="bg-popover border border-border text-popover-foreground select-none max-w-sm p-5 rounded-xl shadow-2xl backdrop-blur-xl">
            <DialogHeader className="space-y-1">
              <DialogTitle className="text-foreground text-base font-extrabold flex items-center gap-1.5">
                <Play className="h-4 w-4 text-primary fill-current" />
                Dispatch Test Notification
              </DialogTitle>
              <DialogDescription className="text-muted-foreground text-xs">
                Send a manual verification payload to verify the `{testChannelType}` channel endpoint.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSendTest} className="space-y-4 pt-3">
              <div className="space-y-1">
                <Label htmlFor="t-msg" className="text-xs font-bold text-muted-foreground">Test Alert Content</Label>
                <Textarea
                  id="t-msg"
                  value={testMessage}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setTestMessage(e.target.value)}
                  placeholder="Enter custom validation message..."
                  rows={3}
                  className="bg-background border-border text-foreground text-xs resize-none"
                  required
                />
              </div>

              <DialogFooter className="pt-2 gap-2 sm:gap-0">
                <DialogClose asChild>
                  <Button
                    type="button"
                    variant="outline"
                    className="border-border text-muted-foreground hover:bg-accent hover:text-accent-foreground text-xs font-bold h-9"
                    onClick={() => setTestingConfigId(null)}
                  >
                    Cancel
                  </Button>
                </DialogClose>
                <Button
                  type="submit"
                  disabled={testMutation.isPending || !testMessage.trim()}
                  className="text-xs font-bold h-9 shadow-lg gap-1.5 min-w-[90px]"
                >
                  {testMutation.isPending && (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  )}
                  Send Test
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* ==========================================
            DELETE INTEGRATION CONFIRMATION DIALOG
            ========================================== */}
        <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
          <DialogContent className="bg-popover border border-border text-popover-foreground select-none max-w-sm p-5 rounded-xl shadow-2xl backdrop-blur-xl">
            <DialogHeader className="space-y-2">
              <DialogTitle className="text-foreground text-base font-extrabold flex items-center gap-1.5">
                <AlertTriangle className="h-5 w-5 text-rose-500" />
                Delete Integration?
              </DialogTitle>
              <DialogDescription className="text-muted-foreground text-xs leading-relaxed">
                This action is irreversible. Operation notices and telemetry alert warnings will no longer route to this channel endpoint.
              </DialogDescription>
            </DialogHeader>

            <DialogFooter className="pt-4 gap-2 sm:gap-0">
              <DialogClose asChild>
                <Button
                  variant="outline"
                  className="border-border text-muted-foreground hover:bg-accent hover:text-accent-foreground text-xs font-bold h-9"
                >
                  Keep Channel
                </Button>
              </DialogClose>
              <Button
                onClick={executeDelete}
                disabled={deleteMutation.isPending}
                className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold h-9 shadow-lg gap-1.5 min-w-[90px]"
              >
                {deleteMutation.isPending && (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                )}
                Confirm Delete
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

      </div>
    </ErrorBoundary>
  )
}

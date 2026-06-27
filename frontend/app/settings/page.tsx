'use client'

import React, { useState, useEffect } from 'react'
import {
  useSettings,
  useUpdateSettings,
  useApiKeys,
  useCreateApiKey,
  useRevokeApiKey,
  useIntegrations,
  useDeleteIntegration,
  useSyncIntegration,
  useLlmProviders,
  useCreateLlmProvider,
  useUpdateLlmProvider,
  useDeleteLlmProvider,
} from '@/hooks/useSettings'
import { testLlmProviderConnection } from '@/lib/api'

import { useSettingsStore } from '@/store/settingsStore'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from 'sonner'
import ErrorBoundary from '@/components/common/ErrorBoundary'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import { 
  Settings as SettingsIcon,
  Sliders, 
  AlertTriangle, 
  ChevronDown, 
  ChevronUp, 
  Clock,
  Volume2,
  Activity,
  Terminal,
  FileCode,
  Save,
  RotateCcw,
  Database,
  Link2,
  Server,
  Key,
  Shield,
  ShieldCheck,
  ShieldX,
  Trash2,
  RefreshCw,
  Plus,
  Globe,
  ListFilter
} from 'lucide-react'
import ApiKeyModal from '@/components/settings/ApiKeyModal'
import IntegrationForm from '@/components/settings/IntegrationForm'
import { IntegrationConnection, SyncedAsset } from '@/types'

export default function SettingsPage() {
  // --- react-query Hooks ---
  const { data: globalSettings, isLoading: isGlobalLoading } = useSettings()
  const updateSettingsMutation = useUpdateSettings()
  const { data: apiKeys = [], isLoading: isKeysLoading } = useApiKeys()
  const createKeyMutation = useCreateApiKey()
  const revokeKeyMutation = useRevokeApiKey()
  const { data: integrations = [], isLoading: isIntegrationsLoading } = useIntegrations()
  const deleteIntegrationMutation = useDeleteIntegration()
  const syncIntegrationMutation = useSyncIntegration()
  const { data: llmProviders = [], isLoading: isLlmLoading } = useLlmProviders()
  const createLlmMutation = useCreateLlmProvider()
  const updateLlmMutation = useUpdateLlmProvider()
  const deleteLlmMutation = useDeleteLlmProvider()


  // --- Zustand Pipeline Settings ---
  const {
    pipelineSettings,
    isLoading: isPipelineSettingsLoading,
    fetchSettings,
    setPipelineRunFrequency,
    setAlertFrequency,
    setAnomalyImmediateAlert,
    setSensitivity,
    setSeverityOverride,
    saveSettings: savePipelineSettings
  } = useSettingsStore()

  useEffect(() => {
    fetchSettings()
  }, [])

  // --- Local UI States ---
  const [activeTab, setActiveTab] = useState('pipelines')
  const [isSaving, setIsSaving] = useState(false)
  const [collapsedPipeline, setCollapsedPipeline] = useState<Record<string, boolean>>({
    finnhub: true,
    fda: true,
    github: true
  })

  // Global thresholds states
  const [incidentThreshold, setIncidentThreshold] = useState(70)
  const [alertCooldown, setAlertCooldown] = useState(15)

  // API Keys state
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyExpiry, setNewKeyExpiry] = useState<number | null>(null)
  const [rawCreatedKey, setRawCreatedKey] = useState('')
  const [rawCreatedName, setRawCreatedName] = useState('')
  const [isKeyCopyOpen, setIsKeyCopyOpen] = useState(false)

  // Integrations state
  const [isIntegrationOpen, setIsIntegrationOpen] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState('')
  const [syncedAssetsMap, setSyncedAssetsMap] = useState<Record<string, SyncedAsset[]>>({})

  // Admin settings state
  const [corsOrigins, setCorsOrigins] = useState<string[]>([])
  const [retentionDays, setRetentionDays] = useState(90)
  const [globalWebhook, setGlobalWebhook] = useState('')

  // LLM states
  const [isLlmFormOpen, setIsLlmFormOpen] = useState(false)
  const [editingLlmId, setEditingLlmId] = useState<string | null>(null)
  const [llmName, setLlmName] = useState('')
  const [llmProviderType, setLlmProviderType] = useState('OPENAI')
  const [llmBaseUrl, setLlmBaseUrl] = useState('https://api.openai.com/v1')
  const [llmModelName, setLlmModelName] = useState('gpt-4o')
  const [llmApiKey, setLlmApiKey] = useState('')
  const [llmPriority, setLlmPriority] = useState(0)
  const [llmIsActive, setLlmIsActive] = useState(true)
  const [isTestingLlm, setIsTestingLlm] = useState(false)

  // Handle LLM Provider Type Selection pre-fill helper
  const handleLlmProviderTypeChange = (value: string) => {
    setLlmProviderType(value)
    switch (value) {
      case 'OPENAI':
        setLlmBaseUrl('https://api.openai.com/v1')
        setLlmModelName('gpt-4o')
        break
      case 'ANTHROPIC':
        setLlmBaseUrl('https://api.anthropic.com/v1/messages')
        setLlmModelName('claude-3-5-sonnet-20241022')
        break
      case 'OLLAMA':
        setLlmBaseUrl('http://localhost:11434/v1')
        setLlmModelName('llama3.2')
        break
      case 'CUSTOM':
      default:
        setLlmBaseUrl('')
        setLlmModelName('')
        break
    }
  }

  const handleTestLlmConnection = async () => {
    setIsTestingLlm(true)
    try {
      const result = await testLlmProviderConnection({
        provider_type: llmProviderType,
        base_url: llmBaseUrl,
        model_name: llmModelName,
        api_key: llmApiKey || undefined,
      })
      if (result.success) {
        toast.success(`Connection successful! Response: ${result.response_preview || ''}`)
      } else {
        toast.error(`Connection failed: ${result.message}`)
      }
    } catch (err: any) {
      toast.error(`Connectivity check error: ${err.message || err}`)
    } finally {
      setIsTestingLlm(false)
    }
  }

  const handleSaveLlmProvider = (e: React.FormEvent) => {
    e.preventDefault()
    if (!llmName || !llmProviderType || !llmBaseUrl || !llmModelName) {
      toast.error('Please fill in all required fields.')
      return
    }

    const payload = {
      name: llmName,
      provider_type: llmProviderType,
      base_url: llmBaseUrl,
      model_name: llmModelName,
      api_key: llmApiKey || undefined,
      is_active: llmIsActive,
      priority: llmPriority,
    }

    if (editingLlmId) {
      updateLlmMutation.mutate(
        { id: editingLlmId, data: payload },
        {
          onSuccess: () => {
            setIsLlmFormOpen(false)
            setEditingLlmId(null)
            resetLlmForm()
          },
        }
      )
    } else {
      createLlmMutation.mutate(payload, {
        onSuccess: () => {
          setIsLlmFormOpen(false)
          resetLlmForm()
        },
      })
    }
  }

  const resetLlmForm = () => {
    setLlmName('')
    setLlmProviderType('OPENAI')
    setLlmBaseUrl('https://api.openai.com/v1')
    setLlmModelName('gpt-4o')
    setLlmApiKey('')
    setLlmPriority(0)
    setLlmIsActive(true)
  }

  const handleEditLlm = (provider: any) => {
    setEditingLlmId(provider.id)
    setLlmName(provider.name)
    setLlmProviderType(provider.provider_type)
    setLlmBaseUrl(provider.base_url)
    setLlmModelName(provider.model_name)
    setLlmApiKey('') // Kept blank to avoid exposing/changing it unless edited
    setLlmPriority(provider.priority)
    setLlmIsActive(provider.is_active)
    setIsLlmFormOpen(true)
  }


  useEffect(() => {
    if (globalSettings) {
      setIncidentThreshold(globalSettings.incident_threshold)
      setCorsOrigins(globalSettings.cors_origins || [])
      setRetentionDays(globalSettings.data_retention_days || 90)
      setGlobalWebhook(globalSettings.global_webhook_url || '')
    }
  }, [globalSettings])

  const toggleCollapse = (pipeline: string) => {
    setCollapsedPipeline(prev => ({
      ...prev,
      [pipeline]: !prev[pipeline]
    }))
  }

  // Handle saving customization values (Pipelines)
  const handleSavePipelines = async () => {
    setIsSaving(true)
    try {
      await savePipelineSettings()
    } catch {
      toast.error('Failed to commit configurations.')
    } finally {
      setIsSaving(false)
    }
  }

  // Reset to default settings helper
  const handleResetDefaults = () => {
    const pipelines = Object.keys(pipelineSettings)
    pipelines.forEach(p => {
      setPipelineRunFrequency(p, 15)
      setAlertFrequency(p, 30)
      setAnomalyImmediateAlert(p, true)
      setSensitivity(p, 'MEDIUM')
      setSeverityOverride(p, 'CRITICAL', 1)
      setSeverityOverride(p, 'HIGH', 5)
      setSeverityOverride(p, 'MEDIUM', 15)
      setSeverityOverride(p, 'LOW', 60)
    })
    toast.info('Settings reset to default parameters.')
  }

  // Helper to get pipeline icons
  const getPipelineIcon = (name: string) => {
    switch (name) {
      case 'finnhub':
        return <Activity className="h-5 w-5 text-emerald-400" />
      case 'fda':
        return <Terminal className="h-5 w-5 text-sky-400" />
      case 'github':
      default:
        return <FileCode className="h-5 w-5 text-emerald-400" />
    }
  }

  const getPipelineTitle = (name: string) => {
    switch (name) {
      case 'finnhub':
        return 'Finnhub Stock Market Ingestion'
      case 'fda':
        return 'FDA Adverse Events Ingestion'
      case 'github':
      default:
        return 'GitHub Activity Records Ingestion'
    }
  }

  // Create API Key
  const handleCreateKey = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newKeyName) return
    createKeyMutation.mutate(
      {
        name: newKeyName,
        expires_in_days: newKeyExpiry
      },
      {
        onSuccess: (data) => {
          setRawCreatedKey(data.key)
          setRawCreatedName(data.name)
          setIsKeyCopyOpen(true)
          setNewKeyName('')
          setNewKeyExpiry(null)
        }
      }
    )
  }

  // Sync Integration assets
  const handleSyncIntegration = (id: string) => {
    syncIntegrationMutation.mutate(id, {
      onSuccess: (data) => {
        setSyncedAssetsMap((prev) => ({
          ...prev,
          [id]: data.assets
        }))
      }
    })
  }

  // Save Reliability & Thresholds
  const handleSaveReliability = () => {
    updateSettingsMutation.mutate({
      incident_threshold: incidentThreshold
    })
  }

  // Save admin settings
  const handleSaveAdmin = () => {
    updateSettingsMutation.mutate({
      cors_origins: corsOrigins,
      data_retention_days: retentionDays,
      global_webhook_url: globalWebhook
    })
  }

  const getIntegrationProviderIcon = (provider: string) => {
    switch (provider) {
      case 'POSTGRESQL':
      case 'REDSHIFT':
        return <Database className="h-5 w-5 text-sky-400" />
      case 'AIRFLOW':
        return <Link2 className="h-5 w-5 text-emerald-400" />
      case 'SNOWFLAKE':
        return <Server className="h-5 w-5 text-cyan-400" />
      case 'BIGQUERY':
        return <Key className="h-5 w-5 text-yellow-400" />
      case 'POWERBI':
        return <Globe className="h-5 w-5 text-amber-500" />
      case 'TABLEAU':
        return <Sliders className="h-5 w-5 text-indigo-500" />
      case 'LOOKER':
        return <Activity className="h-5 w-5 text-violet-500" />
      default:
        return <Database className="h-5 w-5 text-slate-400" />
    }
  }

  return (
    <ErrorBoundary>
      <div className="space-y-6 max-w-5xl mx-auto p-4 md:p-6 pb-28 text-foreground">
        
        {/* Header Title Row */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-5">
          <div className="space-y-1">
            <h1 className="text-2xl font-extrabold tracking-tight bg-gradient-to-r from-slate-900 via-slate-800 to-slate-600 dark:from-white dark:via-slate-100 dark:to-slate-400 bg-clip-text text-transparent flex items-center gap-2">
              <SettingsIcon className="h-6 w-6 text-primary" />
              Settings Hub
            </h1>
            <p className="text-xs text-muted-foreground max-w-xl leading-relaxed">
              Configure ingestion schedules, setup multi-source databases, manage access credentials, and adjust log retention rules.
            </p>
          </div>
        </div>

        <Tabs defaultValue="pipelines" className="w-full space-y-6" onValueChange={setActiveTab}>
          <TabsList className="flex overflow-x-auto bg-muted p-1 w-full max-w-2xl rounded-lg">
            <TabsTrigger value="pipelines" className="flex items-center gap-1.5 flex-1 whitespace-nowrap">
              <Sliders className="h-4 w-4" />
              <span>Pipelines</span>
            </TabsTrigger>
            <TabsTrigger value="reliability" className="flex items-center gap-1.5 flex-1 whitespace-nowrap">
              <Shield className="h-4 w-4" />
              <span>Reliability</span>
            </TabsTrigger>
            <TabsTrigger value="integrations" className="flex items-center gap-1.5 flex-1 whitespace-nowrap">
              <Database className="h-4 w-4" />
              <span>Integrations</span>
            </TabsTrigger>
            <TabsTrigger value="api-keys" className="flex items-center gap-1.5 flex-1 whitespace-nowrap">
              <Key className="h-4 w-4" />
              <span>API Keys</span>
            </TabsTrigger>
            <TabsTrigger value="llm" className="flex items-center gap-1.5 flex-1 whitespace-nowrap">
              <Activity className="h-4 w-4" />
              <span>LLM Providers</span>
            </TabsTrigger>
            <TabsTrigger value="admin" className="flex items-center gap-1.5 flex-1 whitespace-nowrap">
              <Globe className="h-4 w-4" />
              <span>Admin</span>
            </TabsTrigger>
          </TabsList>


          {/* 1. Pipelines Tab Content */}
          <TabsContent value="pipelines" className="space-y-6">
            {isPipelineSettingsLoading ? (
              <div className="flex flex-col items-center justify-center py-20 gap-2 text-slate-500 dark:text-slate-400">
                <LoadingSpinner text="Fetching schedules from Qolyx database..." />
              </div>
            ) : (
              <>
                <div className="space-y-6">
                  {Object.keys(pipelineSettings).map((pipelineKey) => {
                    const config = pipelineSettings[pipelineKey]
                    const isAlertInvalid = config.alert_frequency_minutes < config.run_frequency_minutes

                    return (
                      <div 
                        key={pipelineKey}
                        className="glass-panel p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/10 space-y-6 relative overflow-hidden"
                      >
                        <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-primary to-transparent" />

                        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
                          <div className="flex items-center gap-3">
                            <div className="p-2 bg-slate-100 dark:bg-slate-950/40 rounded-lg border border-slate-200 dark:border-white/5">
                              {getPipelineIcon(pipelineKey)}
                            </div>
                            <div>
                              <h3 className="font-extrabold text-slate-800 dark:text-slate-200 text-sm tracking-tight">
                                {getPipelineTitle(pipelineKey)}
                              </h3>
                              <span className="text-[10px] text-slate-600 dark:text-slate-500 font-mono">Key: {pipelineKey}</span>
                            </div>
                          </div>
                          <Badge variant="outline" className="bg-slate-100 dark:bg-slate-950/40 border-slate-200 dark:border-slate-800 text-[9px] font-mono font-bold py-0.5 px-2 text-slate-600 dark:text-slate-400">
                            Active
                          </Badge>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                          <div className="space-y-3">
                            <div className="flex items-center justify-between">
                              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
                                <Clock className="h-3.5 w-3.5 text-primary" />
                                Ingestion Interval
                              </Label>
                              <div className="flex items-center gap-1.5">
                                <Input
                                  type="number"
                                  min="1"
                                  max="1440"
                                  value={config.run_frequency_minutes}
                                  onChange={(e) => setPipelineRunFrequency(pipelineKey, parseInt(e.target.value, 10) || 1)}
                                  className="w-16 h-7 text-center bg-background border-border text-xs font-mono font-black text-foreground p-0"
                                />
                                <span className="text-[10px] text-muted-foreground font-bold">m</span>
                              </div>
                            </div>

                            <div className="flex items-center gap-4">
                              <input 
                                type="range"
                                min="1"
                                max="360"
                                value={config.run_frequency_minutes}
                                onChange={(e) => setPipelineRunFrequency(pipelineKey, parseInt(e.target.value, 10) || 1)}
                                className="w-full h-1 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                              />
                              <span className="text-[10px] text-muted-foreground font-mono min-w-[30px] text-right">360m</span>
                            </div>
                            <span className="text-[10px] text-muted-foreground leading-normal block">
                              Controls how frequently schedulers invoke the raw fetch methods.
                            </span>
                          </div>

                          <div className="space-y-3">
                            <div className="flex items-center justify-between">
                              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                                <Volume2 className="h-3.5 w-3.5 text-emerald-400" />
                                Alert Suppress Duration
                              </Label>
                              <div className="flex items-center gap-1.5">
                                <Input
                                  type="number"
                                  min="1"
                                  max="1440"
                                  value={config.alert_frequency_minutes}
                                  onChange={(e) => setAlertFrequency(pipelineKey, parseInt(e.target.value, 10) || 1)}
                                  className="w-16 h-7 text-center bg-background border-border text-xs font-mono font-black text-foreground p-0"
                                />
                                <span className="text-[10px] text-muted-foreground font-bold">m</span>
                              </div>
                            </div>

                            <div className="flex items-center gap-4">
                              <input 
                                type="range"
                                min="1"
                                max="360"
                                value={config.alert_frequency_minutes}
                                onChange={(e) => setAlertFrequency(pipelineKey, parseInt(e.target.value, 10) || 1)}
                                className="w-full h-1 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                              />
                              <span className="text-[10px] text-muted-foreground font-mono min-w-[30px] text-right">360m</span>
                            </div>
                            <span className="text-[10px] text-muted-foreground leading-normal block">
                              Suppresses consecutive notifications to avoid spamming alerts to Teams/Slack channels.
                            </span>
                          </div>
                        </div>

                        {isAlertInvalid && (
                          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-500 flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                            <span>
                              Warning: Alert suppression interval ({config.alert_frequency_minutes}m) should be greater than or equal to ingestion run frequency ({config.run_frequency_minutes}m) to avoid skipped alerts.
                            </span>
                          </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="flex items-center justify-between p-3.5 rounded-lg bg-muted/50 border border-border">
                            <div className="space-y-0.5">
                              <span className="text-xs font-bold text-foreground">Bypass Suppression</span>
                              <p className="text-[10px] text-muted-foreground">
                                Disregard suppressions and alert immediately when statistical anomalies are detected.
                              </p>
                            </div>
                            <Switch
                              checked={config.anomaly_immediate_alert}
                              onCheckedChange={(checked) => setAnomalyImmediateAlert(pipelineKey, checked)}
                              className="data-[state=checked]:bg-primary"
                            />
                          </div>

                          <div className="flex items-center justify-between p-3.5 rounded-lg bg-muted/50 border border-border gap-4">
                            <div className="space-y-0.5">
                              <span className="text-xs font-bold text-foreground">Anomaly Sensitivity</span>
                              <p className="text-[10px] text-muted-foreground">
                                Tune outlier detection sensitivity threshold for Isolation Forest.
                              </p>
                            </div>
                            <Select
                              value={config.sensitivity || 'MEDIUM'}
                              onValueChange={(val) => setSensitivity(pipelineKey, val as any)}
                            >
                              <SelectTrigger className="w-28 h-8 text-xs font-bold bg-background border-border text-foreground">
                                <SelectValue placeholder="Sensitivity" />
                              </SelectTrigger>
                              <SelectContent className="bg-card border-border text-foreground">
                                <SelectItem value="LOW" className="text-xs font-semibold">Low</SelectItem>
                                <SelectItem value="MEDIUM" className="text-xs font-semibold">Medium</SelectItem>
                                <SelectItem value="HIGH" className="text-xs font-semibold">High</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>

                        <div className="border-t border-slate-200 dark:border-slate-800 pt-4">
                          <button
                            type="button"
                            onClick={() => toggleCollapse(pipelineKey)}
                            className="flex items-center justify-between w-full text-xs font-bold text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
                          >
                            <span className="flex items-center gap-1.5 uppercase tracking-wider font-mono">
                              <Sliders className="h-3.5 w-3.5 text-primary" />
                              Severity-Based Alert Overrides
                            </span>
                            {collapsedPipeline[pipelineKey] ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronUp className="h-4 w-4" />
                            )}
                          </button>

                          {!collapsedPipeline[pipelineKey] && (
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mt-4 p-4 rounded-lg bg-slate-100 dark:bg-slate-950/20 border border-slate-200 dark:border-slate-800 animate-fadeIn">
                              <div className="space-y-2">
                                <div className="flex items-center justify-between text-[10px] font-bold">
                                  <span className="text-rose-500">CRITICAL</span>
                                  <span className="font-mono">{config.severity_overrides?.CRITICAL ?? 'N/A'} min</span>
                                </div>
                                <input
                                  type="range"
                                  min="1"
                                  max="120"
                                  value={config.severity_overrides?.CRITICAL ?? 1}
                                  onChange={(e) => setSeverityOverride(pipelineKey, 'CRITICAL', parseInt(e.target.value, 10))}
                                  className="w-full h-1 bg-slate-200 dark:bg-slate-900 rounded-lg appearance-none cursor-pointer accent-rose-500"
                                />
                              </div>
                              <div className="space-y-2">
                                <div className="flex items-center justify-between text-[10px] font-bold">
                                  <span className="text-orange-500">HIGH</span>
                                  <span className="font-mono">{config.severity_overrides?.HIGH ?? 'N/A'} min</span>
                                </div>
                                <input
                                  type="range"
                                  min="1"
                                  max="120"
                                  value={config.severity_overrides?.HIGH ?? 5}
                                  onChange={(e) => setSeverityOverride(pipelineKey, 'HIGH', parseInt(e.target.value, 10))}
                                  className="w-full h-1 bg-slate-200 dark:bg-slate-900 rounded-lg appearance-none cursor-pointer accent-orange-500"
                                />
                              </div>
                              <div className="space-y-2">
                                <div className="flex items-center justify-between text-[10px] font-bold">
                                  <span className="text-amber-500">MEDIUM</span>
                                  <span className="font-mono">{config.severity_overrides?.MEDIUM ?? 'N/A'} min</span>
                                </div>
                                <input
                                  type="range"
                                  min="1"
                                  max="120"
                                  value={config.severity_overrides?.MEDIUM ?? 15}
                                  onChange={(e) => setSeverityOverride(pipelineKey, 'MEDIUM', parseInt(e.target.value, 10))}
                                  className="w-full h-1 bg-slate-200 dark:bg-slate-900 rounded-lg appearance-none cursor-pointer accent-amber-500"
                                />
                              </div>
                              <div className="space-y-2">
                                <div className="flex items-center justify-between text-[10px] font-bold">
                                  <span className="text-sky-500">LOW</span>
                                  <span className="font-mono">{config.severity_overrides?.LOW ?? 'N/A'} min</span>
                                </div>
                                <input
                                  type="range"
                                  min="1"
                                  max="240"
                                  value={config.severity_overrides?.LOW ?? 60}
                                  onChange={(e) => setSeverityOverride(pipelineKey, 'LOW', parseInt(e.target.value, 10))}
                                  className="w-full h-1 bg-slate-200 dark:bg-slate-900 rounded-lg appearance-none cursor-pointer accent-sky-500"
                                />
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </>
            )}
            
            {/* Sticky footer Save Action (Pipelines Tab Only) */}
            <div className="fixed bottom-0 left-0 right-0 md:left-64 bg-background/85 backdrop-blur-md border-t border-border py-4 px-6 flex items-center justify-between z-30">
              <div className="text-[10px] text-muted-foreground font-mono hidden sm:block">
                💾 Persisting pipeline values in local store.
              </div>
              <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
                <Button variant="outline" onClick={handleResetDefaults} className="border-border text-xs h-9 px-4">
                  Reset Defaults
                </Button>
                <Button onClick={handleSavePipelines} disabled={isSaving} className="bg-primary hover:bg-primary/95 text-white font-bold text-xs h-9 px-6">
                  {isSaving ? 'Saving...' : 'Save Pipeline Settings'}
                </Button>
              </div>
            </div>
          </TabsContent>

          {/* 2. Reliability & Alerts Tab Content */}
          <TabsContent value="reliability">
            <Card className="bg-card border border-border text-foreground">
              <CardHeader>
                <CardTitle className="text-lg font-bold">Reliability Parameters</CardTitle>
                <CardDescription className="text-muted-foreground">
                  Global data quality parameters and threshold scores.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <Label htmlFor="global-threshold">Incident Trigger Trust Score Threshold</Label>
                    <span className="font-mono text-sm font-bold bg-primary/10 border border-primary/20 text-primary px-2 py-0.5 rounded">
                      {incidentThreshold} / 100
                    </span>
                  </div>
                  <input
                    id="global-threshold"
                    type="range"
                    min="1"
                    max="99"
                    value={incidentThreshold}
                    onChange={(e) => setIncidentThreshold(parseInt(e.target.value, 10))}
                    className="w-full h-1 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    Incidents are automatically triggered when a dataset's consolidated Trust Score falls below this threshold.
                  </p>
                </div>

                <div className="space-y-2 pt-2">
                  <Label htmlFor="cooldown-input">Incident Alert Cooldown (minutes)</Label>
                  <Input
                    id="cooldown-input"
                    type="number"
                    min="1"
                    max="1440"
                    value={alertCooldown}
                    onChange={(e) => setAlertCooldown(parseInt(e.target.value, 10) || 15)}
                    className="w-full max-w-xs bg-background border border-border text-foreground"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    Suppress dispatch of new notifications for recurring alerts under the same incident cluster within this block.
                  </p>
                </div>
              </CardContent>
              <CardFooter className="border-t border-border pt-4 flex justify-end">
                <Button onClick={handleSaveReliability} disabled={updateSettingsMutation.isPending} className="bg-primary hover:bg-primary/95 text-white flex items-center gap-1.5">
                  {updateSettingsMutation.isPending ? 'Saving...' : 'Save Parameters'}
                </Button>
              </CardFooter>
            </Card>
          </TabsContent>          {/* 3. Integrations Tab Content */}
          <TabsContent value="integrations" className="space-y-6">
            <Card className="bg-card border border-border text-foreground">
              <CardHeader>
                <CardTitle className="text-lg font-bold">Multi-Source Connectivity</CardTitle>
                <CardDescription className="text-muted-foreground">
                  Select a third-party source to connect its schemas and tasks to Qolyx.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
                  {[
                    { id: 'POSTGRESQL', name: 'PostgreSQL', desc: 'Query relational tables', icon: <Database className="h-5 w-5 text-sky-400" /> },
                    { id: 'AIRFLOW', name: 'Apache Airflow', desc: 'Sync pipeline DAGs', icon: <Link2 className="h-5 w-5 text-emerald-400" /> },
                    { id: 'SNOWFLAKE', name: 'Snowflake', desc: 'Monitor cloud catalogs', icon: <Server className="h-5 w-5 text-cyan-400" /> },
                    { id: 'BIGQUERY', name: 'BigQuery', desc: 'Audit serverless datasets', icon: <Key className="h-5 w-5 text-yellow-400" /> },
                    { id: 'REDSHIFT', name: 'Redshift', desc: 'Track data warehouse runs', icon: <Database className="h-5 w-5 text-rose-400" /> },
                    { id: 'POWERBI', name: 'Power BI', desc: 'Sync workspaces & reports', icon: <Globe className="h-5 w-5 text-amber-500" /> },
                    { id: 'TABLEAU', name: 'Tableau', desc: 'Query workbook details', icon: <Sliders className="h-5 w-5 text-indigo-500" /> },
                    { id: 'LOOKER', name: 'Looker', desc: 'Monitor dashboard Explores', icon: <Activity className="h-5 w-5 text-violet-500" /> }
                  ].map((provider) => (
                    <button
                      key={provider.id}
                      type="button"
                      onClick={() => {
                        setSelectedProvider(provider.id)
                        setIsIntegrationOpen(true)
                      }}
                      className="flex flex-col items-center justify-center p-4 rounded-xl border border-border hover:border-primary/50 hover:bg-muted transition-all text-center gap-3 group"
                    >
                      <div className="p-3 bg-muted rounded-lg group-hover:scale-110 transition-transform">
                        {provider.icon}
                      </div>
                      <div>
                        <p className="text-xs font-bold font-sans">{provider.name}</p>
                        <p className="text-[10px] text-muted-foreground mt-1 leading-normal">{provider.desc}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Connected Integrations */}
            {isIntegrationsLoading ? (
              <div className="h-28 bg-muted animate-pulse rounded-lg" />
            ) : integrations.length === 0 ? (
              <div className="text-center py-8 border border-dashed border-border rounded-lg text-muted-foreground">
                No active source connections found. Add a connection above to start.
              </div>
            ) : (
              <div className="space-y-6">
                <h3 className="font-extrabold text-sm uppercase tracking-wider text-muted-foreground">Connected Sources</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {integrations.map((conn) => {
                    const assets = syncedAssetsMap[conn.id] || []
                    return (
                      <Card key={conn.id} className="bg-card border border-border text-foreground overflow-hidden">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b border-border">
                          <div className="flex items-center gap-2.5">
                            {getIntegrationProviderIcon(conn.provider)}
                            <div>
                              <CardTitle className="text-sm font-bold leading-none">{conn.name}</CardTitle>
                              <span className="text-[9px] text-muted-foreground font-mono mt-0.5 block">{conn.provider}</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleSyncIntegration(conn.id)}
                              disabled={syncIntegrationMutation.isPending}
                              className="h-8 px-2.5 border-border text-[10px] font-bold flex items-center gap-1"
                            >
                              <RefreshCw className={`h-3 w-3 ${syncIntegrationMutation.isPending ? 'animate-spin' : ''}`} />
                              <span>Sync</span>
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => deleteIntegrationMutation.mutate(conn.id)}
                              disabled={deleteIntegrationMutation.isPending}
                              className="h-8 w-8 text-muted-foreground hover:text-rose-500 hover:bg-rose-500/10"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </CardHeader>
                        <CardContent className="pt-4 space-y-4">
                          {assets.length === 0 ? (
                            <p className="text-[10px] text-muted-foreground leading-normal">
                              Connection initialized. Click <strong>Sync</strong> above to discover metadata tables or pipeline workflows from this connection.
                            </p>
                          ) : (
                            <div className="space-y-2">
                              <p className="text-[10px] font-bold text-muted-foreground flex items-center gap-1">
                                <ListFilter className="h-3.5 w-3.5" />
                                Discovered Assets ({assets.length})
                              </p>
                              <div className="divide-y divide-border max-h-48 overflow-y-auto border border-border rounded-lg p-2 bg-background/50">
                                {assets.map((asset, idx) => (
                                  <div key={idx} className="flex items-center justify-between py-2 text-xs">
                                    <div className="font-mono">
                                      <span className="font-semibold text-foreground">{asset.name}</span>
                                      {asset.type && (
                                        <span className="ml-2 px-1 py-0.5 rounded text-[8px] bg-muted text-muted-foreground font-bold uppercase">
                                          {asset.type}
                                        </span>
                                      )}
                                    </div>
                                    <div className="flex items-center gap-3">
                                      {asset.records !== undefined && asset.records !== null && (
                                        <span className="text-[10px] text-muted-foreground">{asset.records.toLocaleString()} rows</span>
                                      )}
                                      {asset.schedule && (
                                        <span className="text-[10px] text-muted-foreground font-mono">{asset.schedule}</span>
                                      )}
                                      <Switch checked={asset.reliability_enabled} className="scale-75 data-[state=checked]:bg-primary" />
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>
              </div>
            )}

            <IntegrationForm
              isOpen={isIntegrationOpen}
              onOpenChange={setIsIntegrationOpen}
              provider={selectedProvider}
            />
          </TabsContent>

          {/* 4. API Keys Tab Content */}
          <TabsContent value="api-keys" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
              
              {/* Generate form */}
              <Card className="bg-card border border-border text-foreground">
                <CardHeader>
                  <CardTitle className="text-lg font-bold">Generate API Key</CardTitle>
                  <CardDescription className="text-muted-foreground">
                    Create keys for pipeline scripts and automated integrations.
                  </CardDescription>
                </CardHeader>
                <form onSubmit={handleCreateKey}>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="key-name-field">Key Description Name</Label>
                      <Input
                        id="key-name-field"
                        required
                        placeholder="e.g. CI/CD Ingestion Trigger"
                        value={newKeyName}
                        onChange={(e) => setNewKeyName(e.target.value)}
                        className="bg-background border-border text-foreground"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="key-expiry-field">Expiry (Days)</Label>
                      <Select
                        value={newKeyExpiry === null ? 'never' : String(newKeyExpiry)}
                        onValueChange={(val) => setNewKeyExpiry(val === 'never' ? null : parseInt(val, 10))}
                      >
                        <SelectTrigger className="bg-background border-border text-foreground">
                          <SelectValue placeholder="Select expiry duration" />
                        </SelectTrigger>
                        <SelectContent className="bg-card border-border text-foreground">
                          <SelectItem value="never">Never Expires</SelectItem>
                          <SelectItem value="30">30 Days</SelectItem>
                          <SelectItem value="90">90 Days</SelectItem>
                          <SelectItem value="365">1 Year</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </CardContent>
                  <CardFooter className="pt-2 border-t border-border flex justify-end">
                    <Button type="submit" disabled={createKeyMutation.isPending || !newKeyName} className="bg-primary hover:bg-primary/95 text-white flex items-center gap-1.5 w-full">
                      <Plus className="h-4 w-4" />
                      <span>Generate Key</span>
                    </Button>
                  </CardFooter>
                </form>
              </Card>

              {/* Keys list */}
              <Card className="col-span-1 md:col-span-2 bg-card border border-border text-foreground">
                <CardHeader>
                  <CardTitle className="text-lg font-bold">Active API Keys</CardTitle>
                  <CardDescription className="text-muted-foreground">
                    API keys allow programmatic access to the Qolyx dataset validation services.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {isKeysLoading ? (
                    <div className="space-y-3">
                      {[1, 2].map((i) => (
                        <div key={i} className="h-12 bg-muted animate-pulse rounded-lg" />
                      ))}
                    </div>
                  ) : apiKeys.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-6">No API keys generated yet.</p>
                  ) : (
                    <div className="border border-border rounded-lg overflow-hidden">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="bg-muted border-b border-border text-muted-foreground uppercase font-semibold">
                            <th className="px-4 py-3">Key Details</th>
                            <th className="px-4 py-3">Created</th>
                            <th className="px-4 py-3">Expiry</th>
                            <th className="px-4 py-3">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                          {apiKeys.map((k) => (
                            <tr key={k.id} className="hover:bg-muted/50">
                              <td className="px-4 py-3.5">
                                <div className="font-semibold">{k.name}</div>
                                <div className="font-mono text-muted-foreground text-[10px] mt-0.5">{k.key_preview}</div>
                              </td>
                              <td className="px-4 py-3.5 text-muted-foreground">
                                {new Date(k.created_at).toLocaleDateString()}
                              </td>
                              <td className="px-4 py-3.5 text-muted-foreground">
                                {k.expires_at ? new Date(k.expires_at).toLocaleDateString() : 'Never'}
                              </td>
                              <td className="px-4 py-3.5">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => revokeKeyMutation.mutate(k.id)}
                                  disabled={revokeKeyMutation.isPending}
                                  className="text-muted-foreground hover:text-rose-500 hover:bg-rose-500/10 text-[10px] h-7 px-2"
                                >
                                  Revoke
                                </Button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Display raw key copied warning modal */}
            <ApiKeyModal
              isOpen={isKeyCopyOpen}
              onOpenChange={setIsKeyCopyOpen}
              apiKey={rawCreatedKey}
              keyName={rawCreatedName}
            />
          </TabsContent>

          {/* 5. System Admin Tab Content */}
          <TabsContent value="admin">
            <Card className="bg-card border border-border text-foreground">
              <CardHeader>
                <CardTitle className="text-lg font-bold">System Administration</CardTitle>
                <CardDescription className="text-muted-foreground">
                  Global allowed network settings and compliance database policies.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="cors-input">CORS Allowed Domains (Comma Separated)</Label>
                  <Input
                    id="cors-input"
                    placeholder="http://localhost:5173, http://127.0.0.1:5173"
                    value={corsOrigins.join(', ')}
                    onChange={(e) => setCorsOrigins(e.target.value.split(',').map((s) => s.trim()))}
                    className="bg-background border border-border text-foreground"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    Restricts which domain headers are permitted to contact the backend engine endpoints.
                  </p>
                </div>

                <div className="space-y-2 pt-2">
                  <Label htmlFor="retention-input">Reliability Logs Retention (Days)</Label>
                  <Input
                    id="retention-input"
                    type="number"
                    min="1"
                    max="1825"
                    value={retentionDays}
                    onChange={(e) => setRetentionDays(parseInt(e.target.value, 10) || 90)}
                    className="w-full max-w-xs bg-background border border-border text-foreground"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    Older logs representing statistical baseline values, anomaly records, and contract failures will be automatically pruned.
                  </p>
                </div>

                <div className="space-y-2 pt-2">
                  <Label htmlFor="global-webhook-input">Global Event Callback Webhook URL</Label>
                  <Input
                    id="global-webhook-input"
                    placeholder="https://api.company.com/webhooks/qolyx-events"
                    value={globalWebhook}
                    onChange={(e) => setGlobalWebhook(e.target.value)}
                    className="bg-background border border-border text-foreground"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    All reliability warnings and resolved status events will trigger a POST request with payload signatures to this endpoint.
                  </p>
                </div>
              </CardContent>
              <CardFooter className="border-t border-border pt-4 flex justify-end">
                <Button onClick={handleSaveAdmin} disabled={updateSettingsMutation.isPending} className="bg-primary hover:bg-primary/95 text-white flex items-center gap-1.5">
                  {updateSettingsMutation.isPending ? 'Saving...' : 'Save Settings'}
                </Button>
              </CardFooter>
            </Card>
          </TabsContent>

          {/* 6. LLM Providers Tab Content */}
          <TabsContent value="llm" className="space-y-6">
            {isLlmFormOpen ? (
              <form onSubmit={handleSaveLlmProvider}>
                <Card className="bg-card border border-border text-foreground">
                  <CardHeader>
                    <CardTitle className="text-lg font-bold">
                      {editingLlmId ? 'Edit LLM Provider' : 'Add LLM Provider'}
                    </CardTitle>
                    <CardDescription className="text-muted-foreground">
                      Configure connection endpoints and credentials for data summary models.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="llm-name">Provider Name</Label>
                        <Input
                          id="llm-name"
                          required
                          placeholder="e.g. My OpenAI"
                          value={llmName}
                          onChange={(e) => setLlmName(e.target.value)}
                          className="bg-background border-border text-foreground"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="llm-provider-type">Provider Type</Label>
                        <Select value={llmProviderType} onValueChange={handleLlmProviderTypeChange}>
                          <SelectTrigger className="bg-background border-border text-foreground">
                            <SelectValue placeholder="Select type" />
                          </SelectTrigger>
                          <SelectContent className="bg-card border-border text-foreground">
                            <SelectItem value="OPENAI">OpenAI (Cloud)</SelectItem>
                            <SelectItem value="ANTHROPIC">Anthropic (Cloud)</SelectItem>
                            <SelectItem value="OLLAMA">Ollama (Local)</SelectItem>
                            <SelectItem value="CUSTOM">Custom (OpenAI-compatible)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="llm-base-url">Base URL</Label>
                        <Input
                          id="llm-base-url"
                          required
                          placeholder="e.g. https://api.openai.com/v1"
                          value={llmBaseUrl}
                          onChange={(e) => setLlmBaseUrl(e.target.value)}
                          className="bg-background border-border text-foreground"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="llm-model-name">Model Name</Label>
                        <Input
                          id="llm-model-name"
                          required
                          placeholder="e.g. gpt-4o, llama3.2"
                          value={llmModelName}
                          onChange={(e) => setLlmModelName(e.target.value)}
                          className="bg-background border-border text-foreground"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="llm-api-key">API Key (BYOK)</Label>
                        <Input
                          id="llm-api-key"
                          type="password"
                          placeholder={editingLlmId ? "•••••••• (Leave blank to keep current key)" : "Enter provider API key"}
                          value={llmApiKey}
                          onChange={(e) => setLlmApiKey(e.target.value)}
                          className="bg-background border-border text-foreground"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="llm-priority">Priority (Lower runs first)</Label>
                        <Input
                          id="llm-priority"
                          type="number"
                          value={llmPriority}
                          onChange={(e) => setLlmPriority(parseInt(e.target.value, 10) || 0)}
                          className="bg-background border-border text-foreground"
                        />
                      </div>
                    </div>
                    <div className="flex items-center gap-2 pt-2">
                      <Switch id="llm-active" checked={llmIsActive} onCheckedChange={setLlmIsActive} />
                      <Label htmlFor="llm-active">Is Provider Active</Label>
                    </div>
                  </CardContent>
                  <CardFooter className="border-t border-border pt-4 flex justify-between">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleTestLlmConnection}
                      disabled={isTestingLlm}
                      className="border-border text-foreground hover:bg-muted bg-card"
                    >
                      {isTestingLlm ? 'Testing...' : 'Test Connection'}
                    </Button>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() => {
                          setIsLlmFormOpen(false)
                          setEditingLlmId(null)
                          resetLlmForm()
                        }}
                      >
                        Cancel
                      </Button>
                      <Button
                        type="submit"
                        disabled={createLlmMutation.isPending || updateLlmMutation.isPending}
                        className="bg-primary hover:bg-primary/95 text-white"
                      >
                        {createLlmMutation.isPending || updateLlmMutation.isPending ? 'Saving...' : 'Save Provider'}
                      </Button>
                    </div>
                  </CardFooter>
                </Card>
              </form>
            ) : (
              <div className="space-y-6">
                <div className="flex justify-between items-center">
                  <div>
                    <h3 className="text-lg font-bold">LLM Model Providers</h3>
                    <p className="text-xs text-muted-foreground">
                      Configure custom models to generate data quality summaries and RCA explanations.
                    </p>
                  </div>
                  <Button onClick={() => setIsLlmFormOpen(true)} className="bg-primary hover:bg-primary/95 text-white flex items-center gap-1">
                    <Plus className="h-4 w-4" />
                    <span>Add Provider</span>
                  </Button>
                </div>

                <Card className="bg-card border border-border text-foreground">
                  <CardContent className="p-0">
                    {isLlmLoading ? (
                      <div className="flex justify-center py-12">
                        <LoadingSpinner text="Loading LLM integrations..." />
                      </div>
                    ) : llmProviders.length === 0 ? (
                      <div className="text-center py-12 text-muted-foreground space-y-2">
                        <p className="text-sm">No LLM providers configured yet.</p>
                        <p className="text-xs text-muted-foreground/85">Bring your own key (BYOK) to unlock conversational troubleshooting.</p>
                      </div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm border-collapse">
                          <thead>
                            <tr className="border-b border-border text-muted-foreground text-xs">
                              <th className="py-3.5 px-4 font-semibold">Name</th>
                              <th className="py-3.5 px-4 font-semibold">Type</th>
                              <th className="py-3.5 px-4 font-semibold">Base URL</th>
                              <th className="py-3.5 px-4 font-semibold">Model Name</th>
                              <th className="py-3.5 px-4 font-semibold text-center">Priority</th>
                              <th className="py-3.5 px-4 font-semibold text-center">Status</th>
                              <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                            </tr>
                          </thead>
                          <tbody>
                            {llmProviders.map((prov: any) => (
                              <tr key={prov.id} className="border-b border-border/40 hover:bg-muted/50">
                                <td className="py-3.5 px-4 font-medium">{prov.name}</td>
                                <td className="py-3.5 px-4">
                                  <Badge variant="outline" className="text-[10px] py-0.5 px-1.5 uppercase font-semibold border-border">
                                    {prov.provider_type}
                                  </Badge>
                                </td>
                                <td className="py-3.5 px-4 font-mono text-xs text-muted-foreground truncate max-w-xs">{prov.base_url}</td>
                                <td className="py-3.5 px-4 font-mono text-xs text-muted-foreground">{prov.model_name}</td>
                                <td className="py-3.5 px-4 text-center">{prov.priority}</td>
                                <td className="py-3.5 px-4 text-center">
                                  {prov.is_active ? (
                                    <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px] py-0.5 px-1.5 font-bold">
                                      Active
                                    </Badge>
                                  ) : (
                                    <Badge className="bg-slate-500/10 text-slate-400 border-slate-500/20 text-[10px] py-0.5 px-1.5 font-bold">
                                      Disabled
                                    </Badge>
                                  )}
                                </td>
                                <td className="py-3.5 px-4 text-right space-x-2">
                                  <Button variant="ghost" size="sm" onClick={() => handleEditLlm(prov)} className="h-8 px-2 text-foreground">
                                    Edit
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => {
                                      if (confirm(`Are you sure you want to delete LLM provider '${prov.name}'?`)) {
                                        deleteLlmMutation.mutate(prov.id)
                                      }
                                    }}
                                    className="h-8 px-2 text-rose-500 hover:text-rose-400"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>
        </Tabs>

      </div>
    </ErrorBoundary>
  )
}

'use client'

import React, { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Database, Link2, Server, Key, Info, CheckCircle2, XCircle, Globe, Sliders, Activity } from 'lucide-react'
import { useCreateIntegration, useTestIntegration } from '@/hooks/useSettings'

interface IntegrationFormProps {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  provider: string // POSTGRESQL, AIRFLOW, SNOWFLAKE, BIGQUERY, REDSHIFT
}

export default function IntegrationForm({ isOpen, onOpenChange, provider }: IntegrationFormProps) {
  const [name, setName] = useState('')
  const [config, setConfig] = useState<Record<string, any>>({})
  const createMutation = useCreateIntegration()
  const testMutation = useTestIntegration()

  useEffect(() => {
    if (isOpen) {
      setName(`${provider.charAt(0) + provider.slice(1).toLowerCase()} Integration`)
      // Reset config schema
      if (provider === 'POSTGRESQL') {
        setConfig({ host: '127.0.0.1', port: '5432', database: 'postgres', username: 'postgres', password: '' })
      } else if (provider === 'AIRFLOW') {
        setConfig({ url: 'http://localhost:8080', auth_type: 'basic', username: '', password: '', token: '' })
      } else if (provider === 'SNOWFLAKE') {
        setConfig({ account: '', username: '', password: '', warehouse: '', database: '', schema: '' })
      } else if (provider === 'BIGQUERY') {
        setConfig({ project_id: '', client_email: '', private_key: '' })
      } else if (provider === 'REDSHIFT') {
        setConfig({ host: '', port: '5439', database: 'dev', username: 'awsuser', password: '' })
      } else if (provider === 'TABLEAU') {
        setConfig({ url: 'https://tableau.qolyx.local', token: '', token_name: 'qolyx_token', site_name: '' })
      } else if (provider === 'LOOKER') {
        setConfig({ url: 'https://looker.qolyx.local:19999', client_id: '', client_secret: '' })
      } else if (provider === 'POWERBI') {
        setConfig({ tenant_id: '', client_id: '', client_secret: '' })
      }
    }
  }, [isOpen, provider])

  const handleConfigChange = (key: string, val: any) => {
    setConfig((prev) => ({
      ...prev,
      [key]: val
    }))
  }

  const handleTest = () => {
    testMutation.mutate({
      name,
      provider,
      config
    })
  }

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate(
      {
        name,
        provider,
        config
      },
      {
        onSuccess: () => {
          onOpenChange(false)
        }
      }
    )
  }

  const getProviderIcon = () => {
    switch (provider) {
      case 'POSTGRESQL':
      case 'REDSHIFT':
        return <Database className="h-6 w-6 text-sky-400" />
      case 'AIRFLOW':
        return <Link2 className="h-6 w-6 text-emerald-400" />
      case 'SNOWFLAKE':
        return <Server className="h-6 w-6 text-cyan-400" />
      case 'BIGQUERY':
        return <Key className="h-6 w-6 text-yellow-400" />
      case 'POWERBI':
        return <Globe className="h-6 w-6 text-amber-500" />
      case 'TABLEAU':
        return <Sliders className="h-6 w-6 text-indigo-500" />
      case 'LOOKER':
        return <Activity className="h-6 w-6 text-violet-500" />
      default:
        return <Database className="h-6 w-6 text-primary" />
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
        <form onSubmit={handleSave} className="space-y-6">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-xl font-bold">
              {getProviderIcon()}
              <span>Connect {provider} Connection</span>
            </DialogTitle>
            <DialogDescription className="text-slate-500 dark:text-slate-400">
              Configure credentials to sync database metadata catalogs or workflow DAG runs.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="connection-name">Connection Name</Label>
              <Input
                id="connection-name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
              />
            </div>

            {/* PostgreSQL Fields */}
            {provider === 'POSTGRESQL' && (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2 space-y-1">
                    <Label htmlFor="pg-host">Host</Label>
                    <Input
                      id="pg-host"
                      required
                      value={config.host || ''}
                      onChange={(e) => handleConfigChange('host', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="pg-port">Port</Label>
                    <Input
                      id="pg-port"
                      required
                      value={config.port || ''}
                      onChange={(e) => handleConfigChange('port', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="pg-db">Database Name</Label>
                  <Input
                    id="pg-db"
                    required
                    value={config.database || ''}
                    onChange={(e) => handleConfigChange('database', e.target.value)}
                    className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="pg-user">Username</Label>
                    <Input
                      id="pg-user"
                      required
                      value={config.username || ''}
                      onChange={(e) => handleConfigChange('username', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="pg-pass">Password</Label>
                    <Input
                      id="pg-pass"
                      type="password"
                      value={config.password || ''}
                      onChange={(e) => handleConfigChange('password', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Redshift Fields */}
            {provider === 'REDSHIFT' && (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2 space-y-1">
                    <Label htmlFor="rs-host">Endpoint Host</Label>
                    <Input
                      id="rs-host"
                      required
                      placeholder="e.g. cluster.redshift.amazonaws.com"
                      value={config.host || ''}
                      onChange={(e) => handleConfigChange('host', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="rs-port">Port</Label>
                    <Input
                      id="rs-port"
                      required
                      value={config.port || ''}
                      onChange={(e) => handleConfigChange('port', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="rs-db">Database Name</Label>
                  <Input
                    id="rs-db"
                    required
                    value={config.database || ''}
                    onChange={(e) => handleConfigChange('database', e.target.value)}
                    className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="rs-user">Database User</Label>
                    <Input
                      id="rs-user"
                      required
                      value={config.username || ''}
                      onChange={(e) => handleConfigChange('username', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="rs-pass">Password</Label>
                    <Input
                      id="rs-pass"
                      type="password"
                      value={config.password || ''}
                      onChange={(e) => handleConfigChange('password', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Airflow Fields */}
            {provider === 'AIRFLOW' && (
              <div className="space-y-4">
                <div className="space-y-1">
                  <Label htmlFor="af-url">Webserver REST URL</Label>
                  <Input
                    id="af-url"
                    required
                    placeholder="http://localhost:8080"
                    value={config.url || ''}
                    onChange={(e) => handleConfigChange('url', e.target.value)}
                    className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="af-auth-type">Authentication Type</Label>
                  <Select
                    value={config.auth_type || 'basic'}
                    onValueChange={(val) => handleConfigChange('auth_type', val)}
                  >
                    <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs">
                      <SelectValue placeholder="Select auth method" />
                    </SelectTrigger>
                    <SelectContent className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
                      <SelectItem value="basic">Basic Auth (User/Password)</SelectItem>
                      <SelectItem value="token">Bearer Token (Header)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {config.auth_type !== 'token' ? (
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label htmlFor="af-user">Username</Label>
                      <Input
                        id="af-user"
                        required
                        value={config.username || ''}
                        onChange={(e) => handleConfigChange('username', e.target.value)}
                        className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor="af-pass">Password</Label>
                      <Input
                        id="af-pass"
                        type="password"
                        required
                        value={config.password || ''}
                        onChange={(e) => handleConfigChange('password', e.target.value)}
                        className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <Label htmlFor="af-token">Bearer Token</Label>
                    <Input
                      id="af-token"
                      type="password"
                      required
                      placeholder="e.g. eyJhbGciOi..."
                      value={config.token || ''}
                      onChange={(e) => handleConfigChange('token', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                )}
              </div>
            )}

            {/* Snowflake Fields */}
            {provider === 'SNOWFLAKE' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="sf-acc">Account Identifier</Label>
                    <Input
                      id="sf-acc"
                      required
                      placeholder="e.g. xy12345.us-east-1"
                      value={config.account || ''}
                      onChange={(e) => handleConfigChange('account', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="sf-user">User Login</Label>
                    <Input
                      id="sf-user"
                      required
                      value={config.username || ''}
                      onChange={(e) => handleConfigChange('username', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="sf-pass">Password</Label>
                    <Input
                      id="sf-pass"
                      type="password"
                      required
                      value={config.password || ''}
                      onChange={(e) => handleConfigChange('password', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="sf-wh">Warehouse</Label>
                    <Input
                      id="sf-wh"
                      required
                      placeholder="COMPUTE_WH"
                      value={config.warehouse || ''}
                      onChange={(e) => handleConfigChange('warehouse', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="sf-db">Database</Label>
                    <Input
                      id="sf-db"
                      required
                      placeholder="ANALYTICS"
                      value={config.database || ''}
                      onChange={(e) => handleConfigChange('database', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="sf-sch">Schema</Label>
                    <Input
                      id="sf-sch"
                      required
                      placeholder="PUBLIC"
                      value={config.schema || ''}
                      onChange={(e) => handleConfigChange('schema', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* BigQuery Fields */}
            {provider === 'BIGQUERY' && (
              <div className="space-y-4">
                <div className="space-y-1">
                  <Label htmlFor="bq-pid">GCP Project ID</Label>
                  <Input
                    id="bq-pid"
                    required
                    value={config.project_id || ''}
                    onChange={(e) => handleConfigChange('project_id', e.target.value)}
                    className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="bq-email">Service Account Email</Label>
                  <Input
                    id="bq-email"
                    required
                    placeholder="name@project.iam.gserviceaccount.com"
                    value={config.client_email || ''}
                    onChange={(e) => handleConfigChange('client_email', e.target.value)}
                    className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="bq-key">Private Key String</Label>
                  <Textarea
                    id="bq-key"
                    required
                    placeholder="-----BEGIN PRIVATE KEY-----\n..."
                    rows={4}
                    value={config.private_key || ''}
                    onChange={(e) => handleConfigChange('private_key', e.target.value)}
                    className="font-mono text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 resize-none"
                  />
                </div>
              </div>
            )}

            {/* Tableau Fields */}
            {provider === 'TABLEAU' && (
              <div className="space-y-4">
                <div className="space-y-1">
                  <Label htmlFor="tab-url">Tableau Server URL</Label>
                  <Input
                    id="tab-url"
                    required
                    placeholder="https://tableau.qolyx.local"
                    value={config.url || ''}
                    onChange={(e) => handleConfigChange('url', e.target.value)}
                    className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="tab-token-name">PAT Name</Label>
                    <Input
                      id="tab-token-name"
                      required
                      placeholder="qolyx_token"
                      value={config.token_name || ''}
                      onChange={(e) => handleConfigChange('token_name', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="tab-site-name">Site Name (contentUrl)</Label>
                    <Input
                      id="tab-site-name"
                      placeholder="Default Site (leave blank if empty)"
                      value={config.site_name || ''}
                      onChange={(e) => handleConfigChange('site_name', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="tab-token">Personal Access Token (PAT) Secret</Label>
                  <Input
                    id="tab-token"
                    type="password"
                    required
                    placeholder="PAT Secret String"
                    value={config.token || ''}
                    onChange={(e) => handleConfigChange('token', e.target.value)}
                    className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                  />
                </div>
              </div>
            )}

            {/* Looker Fields */}
            {provider === 'LOOKER' && (
              <div className="space-y-4">
                <div className="space-y-1">
                  <Label htmlFor="look-url">Looker Host URL (with Port)</Label>
                  <Input
                    id="look-url"
                    required
                    placeholder="https://looker.qolyx.local:19999"
                    value={config.url || ''}
                    onChange={(e) => handleConfigChange('url', e.target.value)}
                    className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="look-cid">Client ID</Label>
                    <Input
                      id="look-cid"
                      required
                      placeholder="API Client ID"
                      value={config.client_id || ''}
                      onChange={(e) => handleConfigChange('client_id', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="look-sec">Client Secret</Label>
                    <Input
                      id="look-sec"
                      type="password"
                      required
                      placeholder="API Client Secret"
                      value={config.client_secret || ''}
                      onChange={(e) => handleConfigChange('client_secret', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Power BI Fields */}
            {provider === 'POWERBI' && (
              <div className="space-y-4">
                <div className="space-y-1">
                  <Label htmlFor="pbi-tenant">Azure AD Tenant ID</Label>
                  <Input
                    id="pbi-tenant"
                    required
                    placeholder="Tenant UUID"
                    value={config.tenant_id || ''}
                    onChange={(e) => handleConfigChange('tenant_id', e.target.value)}
                    className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="pbi-cid">App Client ID</Label>
                    <Input
                      id="pbi-cid"
                      required
                      placeholder="App Client UUID"
                      value={config.client_id || ''}
                      onChange={(e) => handleConfigChange('client_id', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="pbi-sec">Client Secret</Label>
                    <Input
                      id="pbi-sec"
                      type="password"
                      required
                      placeholder="App Client Secret"
                      value={config.client_secret || ''}
                      onChange={(e) => handleConfigChange('client_secret', e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          <DialogFooter className="flex flex-col sm:flex-row gap-2 border-t border-slate-100 dark:border-slate-800 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={handleTest}
              disabled={testMutation.isPending}
              className="border-slate-200 dark:border-slate-800 flex-1"
            >
              {testMutation.isPending ? 'Testing...' : 'Test Connection'}
            </Button>
            <Button
              type="submit"
              disabled={createMutation.isPending || !name}
              className="bg-primary hover:bg-primary/95 text-white flex-1"
            >
              {createMutation.isPending ? 'Saving...' : 'Connect Provider'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

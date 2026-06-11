'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '@/lib/api'
import LineageGraph from '@/components/lineage/LineageGraph'
import TrustScoreGauge from '@/components/trust-score/TrustScoreGauge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorBoundary from '@/components/common/ErrorBoundary'
import { toast } from 'sonner'
import {
  Search,
  RefreshCw,
  Clock,
  Layers,
  Database,
  FileCode,
  ShieldAlert,
  Award,
  Eye,
  CheckCircle,
  HelpCircle,
  AlertTriangle,
  ArrowRight,
  TrendingDown,
  Info,
  GitBranch,
  ShieldAlert as AnomalyIcon,
  Play,
  Zap,
  Activity,
  ArrowUpRight,
  CheckSquare
} from 'lucide-react'

// Defined static time travel offsets
const OFFSETS = [
  { label: 'Current', hours: 0 },
  { label: '1 hour ago', hours: 1 },
  { label: '6 hours ago', hours: 6 },
  { label: '12 hours ago', hours: 12 },
  { label: '24 hours ago', hours: 24 },
  { label: '3 days ago', hours: 72 },
  { label: '7 days ago', hours: 168 }
]

export default function LineagePage() {
  const queryClient = useQueryClient()
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [timeOffset, setTimeOffset] = useState<number>(0)
  const [highlightCriticalPath, setHighlightCriticalPath] = useState(false)
  const [schemaCompareResult, setSchemaCompareResult] = useState<any | null>(null)
  const [isComparingSchema, setIsComparingSchema] = useState(false)

  // 1. Fetch nodes list
  const nodesListQuery = useQuery({
    queryKey: ['lineage', 'nodes', searchQuery],
    queryFn: () => api.fetchLineageNodes(1, 100, searchQuery),
  })

  // Auto-select first node if none is selected
  useEffect(() => {
    if (nodesListQuery.data?.items?.length > 0 && !selectedNodeId) {
      setSelectedNodeId(nodesListQuery.data.items[0].node_id)
    }
  }, [nodesListQuery.data, selectedNodeId])

  // Get active timestamp for time travel
  const activeTimestamp = useMemo(() => {
    const hours = OFFSETS[timeOffset].hours
    if (hours === 0) return undefined
    return new Date(Date.now() - hours * 60 * 60 * 1000).toISOString()
  }, [timeOffset])

  const displayTimeLabel = useMemo(() => {
    const hours = OFFSETS[timeOffset].hours
    if (hours === 0) return 'Current Lineage (Active)'
    const date = new Date(Date.now() - hours * 60 * 60 * 1000)
    return date.toLocaleString()
  }, [timeOffset])

  // 2. Fetch active/temporal lineage graph
  const graphQuery = useQuery({
    queryKey: ['lineage', 'graph', selectedNodeId, timeOffset],
    queryFn: () => {
      if (!selectedNodeId) return { nodes: [], edges: [] }
      return api.fetchLineageGraph(selectedNodeId, activeTimestamp)
    },
    enabled: !!selectedNodeId,
  })

  // 3. Fetch node details
  const nodeDetailsQuery = useQuery({
    queryKey: ['lineage', 'details', selectedNodeId],
    queryFn: () => {
      if (!selectedNodeId) return null
      return api.fetchLineageNodeDetails(selectedNodeId)
    },
    enabled: !!selectedNodeId,
  })

  // 4. Fetch downstream impact path list
  const impactQuery = useQuery({
    queryKey: ['lineage', 'impact', selectedNodeId],
    queryFn: () => {
      if (!selectedNodeId) return []
      return api.fetchLineageImpact(selectedNodeId)
    },
    enabled: !!selectedNodeId,
  })

  // 5. Fetch critical path trace
  const criticalPathQuery = useQuery({
    queryKey: ['lineage', 'critical-path', selectedNodeId],
    queryFn: () => {
      if (!selectedNodeId) return []
      return api.fetchLineageCriticalPath(selectedNodeId)
    },
    enabled: !!selectedNodeId && highlightCriticalPath,
  })

  // Map critical path details to list of string node_ids for the graph highlighters
  const criticalPathNodeIds = useMemo(() => {
    if (!highlightCriticalPath || !criticalPathQuery.data) return []
    return (criticalPathQuery.data as any[]).map((node: any) => node.node_id)
  }, [criticalPathQuery.data, highlightCriticalPath])

  // 6. Fetch health propagation decay pathway
  const healthPropagationQuery = useQuery({
    queryKey: ['lineage', 'health-propagation', selectedNodeId],
    queryFn: () => {
      if (!selectedNodeId) return null
      return api.fetchHealthPropagation(selectedNodeId)
    },
    enabled: !!selectedNodeId,
  })

  // 7. Temporal Diff Query (compared against current live graph)
  const diffQuery = useQuery({
    queryKey: ['lineage', 'diff', selectedNodeId, timeOffset],
    queryFn: () => {
      if (!selectedNodeId || !activeTimestamp) return null
      const currentTimestamp = new Date().toISOString()
      return api.fetchLineageDiff(selectedNodeId, activeTimestamp, currentTimestamp)
    },
    enabled: !!selectedNodeId && !!activeTimestamp,
  })

  // 8. Mutation to Sync Lineage Graph from backend parsing
  const syncMutation = useMutation({
    mutationFn: () => api.syncLineage(),
    onMutate: () => {
      toast.loading('Scanning workspace for SQL and Python lineage dependencies...', { id: 'sync-lineage' })
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Lineage graph synchronized successfully.', { id: 'sync-lineage' })
      queryClient.invalidateQueries({ queryKey: ['lineage'] })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Lineage synchronization failed.', { id: 'sync-lineage' })
    }
  })

  // Run on-demand schema baseline check
  const handleCompareSchema = async () => {
    if (!selectedNodeId) return
    setIsComparingSchema(true)
    try {
      const res = await api.compareSchemaLineage(selectedNodeId)
      setSchemaCompareResult(res)
      if (res.drift_detected) {
        toast.warning('Schema drift detected! Relational structure matches updated in incident log.', { duration: 5000 })
      } else {
        toast.success(res.message || 'Schema matches lineage baseline perfectly.')
      }
    } catch (e: any) {
      toast.error(e.message || 'Failed to compare schema.')
    } finally {
      setIsComparingSchema(false)
    }
  }

  // Handle node selection from list or inside the graph
  const handleSelectNode = (nodeId: string) => {
    setSelectedNodeId(nodeId)
    setSchemaCompareResult(null)
  }

  const getNodeIcon = (type: string) => {
    switch (type) {
      case 'source':
        return <Database className="h-4 w-4 text-indigo-400" />
      case 'model':
        return <FileCode className="h-4 w-4 text-sky-400" />
      case 'seed':
        return <Award className="h-4 w-4 text-teal-400" />
      case 'test':
        return <CheckCircle className="h-4 w-4 text-green-400" />
      case 'exposure':
        return <Eye className="h-4 w-4 text-purple-400" />
      case 'warehouse_table':
        return <Database className="h-4 w-4 text-emerald-400" />
      default:
        return <HelpCircle className="h-4 w-4 text-slate-400" />
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
    if (score >= 60) return 'text-amber-400 bg-amber-500/10 border-amber-500/20'
    return 'text-rose-400 bg-rose-500/10 border-rose-500/20'
  }

  // Main UI skeleton check
  const isInitialLoading = nodesListQuery.isLoading && !nodesListQuery.data

  return (
    <ErrorBoundary>
      <div className="space-y-6 select-none">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div className="space-y-1">
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent flex items-center gap-2">
              <GitBranch className="h-6 w-6 text-primary animate-pulse" /> Relational Data Lineage Hub
            </h1>
            <p className="text-sm text-slate-400">
              Deterministic AST pipeline parsing, interactive temporal time travel, and cascading health score decay paths.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="flex items-center gap-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-white font-medium shadow-lg"
            >
              <RefreshCw className={`h-4 w-4 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
              Sync Lineage
            </Button>
          </div>
        </div>

        {isInitialLoading ? (
          <LoadingSpinner text="Compiling Relational Data Lineage Graph..." />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Column 1: Search and Node List Selection (Col span 3) */}
            <div className="lg:col-span-3 space-y-4">
              <Card className="glass-panel border-white/5 shadow-xl">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                    <Database className="h-4 w-4 text-slate-400" /> Pipeline Entities
                  </CardTitle>
                  <CardDescription className="text-xs text-slate-400">
                    Select a node to trace upstream and downstream paths
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-500" />
                    <Input
                      type="text"
                      placeholder="Search entities..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9 bg-slate-900/50 border-white/5 focus:border-primary/50 text-xs text-slate-200"
                    />
                  </div>

                  <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                    {nodesListQuery.data?.items?.length === 0 ? (
                      <div className="text-center py-6 text-xs text-slate-500">
                        No pipeline nodes found matching query.
                      </div>
                    ) : (
                      nodesListQuery.data?.items?.map((node: any) => {
                        const isSelected = node.node_id === selectedNodeId
                        const score = node.trust_score ?? 100
                        return (
                          <div
                            key={node.node_id}
                            onClick={() => handleSelectNode(node.node_id)}
                            className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
                              isSelected
                                ? 'bg-primary/10 border-primary text-white shadow-md'
                                : 'bg-slate-900/30 border-white/5 text-slate-300 hover:bg-slate-900/60 hover:text-white'
                            }`}
                          >
                            <div className="flex items-center space-x-2 w-[70%] overflow-hidden">
                              {getNodeIcon(node.type)}
                              <span className="text-xs font-semibold truncate" title={node.node_id}>
                                {node.name}
                              </span>
                            </div>
                            <Badge
                              variant="outline"
                              className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${getScoreColor(score)}`}
                            >
                              {Math.round(score)}%
                            </Badge>
                          </div>
                        )
                      })
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Column 2: Main Workstation - Graph and Time Travel (Col span 6) */}
            <div className="lg:col-span-6 space-y-4">
              <Card className="glass-panel border-white/5 overflow-hidden flex flex-col min-h-[550px] shadow-2xl">
                {/* Workstation Header */}
                <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-slate-950/40">
                  <div>
                    <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                      <Layers className="h-4 w-4 text-slate-400" /> 
                      {nodeDetailsQuery.data?.name || 'Tracing lineage...'}
                    </h3>
                    <p className="text-[11px] text-slate-400 mt-0.5 max-w-sm truncate" title={selectedNodeId || ''}>
                      {selectedNodeId || 'No node selected'}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 self-stretch sm:self-auto justify-between sm:justify-start">
                    <Badge variant="outline" className="text-[10px] uppercase font-bold text-indigo-400 border-indigo-400/20 bg-indigo-400/5">
                      {nodeDetailsQuery.data?.type?.replace('_', ' ') || 'Table'}
                    </Badge>
                    
                    {timeOffset > 0 && (
                      <Badge variant="outline" className="text-[10px] uppercase font-bold text-amber-400 border-amber-400/20 bg-amber-400/5 animate-pulse">
                        Time Travel Active
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Graph Viewport */}
                <div className="flex-1 relative min-h-[420px] bg-slate-950/20">
                  {graphQuery.isLoading ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <LoadingSpinner text="Querying lineage bounds..." />
                    </div>
                  ) : graphQuery.data?.nodes?.length === 0 ? (
                    <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center">
                      <AlertTriangle className="h-10 w-10 text-amber-500 mb-2" />
                      <span className="text-xs font-semibold text-slate-300">No Lineage graph edges mapped.</span>
                      <p className="text-[10px] text-slate-500 max-w-xs mt-1">
                        Try running "Sync Lineage" to trigger parser scanning for database references.
                      </p>
                    </div>
                  ) : (
                    <div className="absolute inset-0 w-full h-full">
                      <LineageGraph
                        nodesData={graphQuery.data?.nodes || []}
                        edgesData={graphQuery.data?.edges || []}
                        onSelectNode={handleSelectNode}
                        selectedNodeId={selectedNodeId}
                        criticalPathNodeIds={criticalPathNodeIds}
                      />
                    </div>
                  )}
                </div>

                {/* Time Travel Slider Control Panel */}
                <div className="p-4 border-t border-slate-800 bg-slate-950/40 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-300 flex items-center gap-1.5">
                      <Clock className="h-4 w-4 text-slate-400" /> Temporal Snapshot Time Travel
                    </span>
                    <span className="text-slate-400 font-mono text-[11px] bg-slate-900 px-2.5 py-0.5 rounded border border-white/5">
                      {displayTimeLabel}
                    </span>
                  </div>

                  <div className="relative px-2 py-1">
                    <input
                      type="range"
                      min="0"
                      max={OFFSETS.length - 1}
                      value={timeOffset}
                      onChange={(e) => setTimeOffset(parseInt(e.target.value))}
                      className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-primary"
                    />
                    <div className="flex justify-between text-[9px] text-slate-500 mt-2 px-1">
                      {OFFSETS.map((o, idx) => (
                        <span 
                          key={idx} 
                          onClick={() => setTimeOffset(idx)}
                          className={`cursor-pointer transition-all ${
                            timeOffset === idx ? 'font-bold text-primary scale-110' : 'hover:text-slate-300'
                          }`}
                        >
                          {o.label}
                        </span>
                      ))}
                    </div>
                  </div>

                  {timeOffset > 0 && (
                    <div className="rounded-lg bg-amber-500/5 border border-amber-500/10 p-2 text-[10px] text-amber-400/80 flex items-start gap-1.5 leading-relaxed">
                      <Info className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                      <span>
                        Displaying lineage architecture as it existed on {displayTimeLabel}. Highlighted paths may differ from live execution paths.
                      </span>
                    </div>
                  )}
                </div>
              </Card>
            </div>

            {/* Column 3: Right Side Inspection Panel (Col span 3) */}
            <div className="lg:col-span-3 space-y-4">
              <Card className="glass-panel border-white/5 shadow-xl">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                    <Activity className="h-4 w-4 text-slate-400" /> Node Inspection
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <Tabs defaultValue="metadata" className="w-full">
                    <TabsList className="grid grid-cols-3 bg-slate-950/60 rounded-none border-b border-slate-800 p-0 h-10">
                      <TabsTrigger value="metadata" className="text-xs py-2 rounded-none data-[state=active]:bg-slate-900 data-[state=active]:border-b-2 data-[state=active]:border-primary">
                        Properties
                      </TabsTrigger>
                      <TabsTrigger value="propagation" className="text-xs py-2 rounded-none data-[state=active]:bg-slate-900 data-[state=active]:border-b-2 data-[state=active]:border-primary">
                        Health Decay
                      </TabsTrigger>
                      <TabsTrigger value="impact" className="text-xs py-2 rounded-none data-[state=active]:bg-slate-900 data-[state=active]:border-b-2 data-[state=active]:border-primary">
                        Impact & Critical
                      </TabsTrigger>
                    </TabsList>

                    {/* TAB 1: NODE METADATA */}
                    <TabsContent value="metadata" className="p-4 m-0 space-y-4">
                      {nodeDetailsQuery.isLoading ? (
                        <div className="text-center py-6 text-xs text-slate-500">Loading node metadata...</div>
                      ) : !nodeDetailsQuery.data ? (
                        <div className="text-center py-6 text-xs text-slate-500">No node selected.</div>
                      ) : (
                        <div className="space-y-4">
                          {/* Trust Score Visualizer */}
                          <div className="flex items-center space-x-4 bg-slate-950/40 p-3 rounded-lg border border-white/5">
                            <TrustScoreGauge score={nodeDetailsQuery.data.trust_score ?? 100} size="sm" />
                            <div className="space-y-1">
                              <span className="text-xs font-semibold text-slate-300">Trust Score Breakdown</span>
                              <div className="text-[10px] text-slate-400 space-y-0.5">
                                <div>Base Score: {Math.round(nodeDetailsQuery.data.meta?.base_score ?? 100)}%</div>
                                {nodeDetailsQuery.data.meta?.lineage_penalty > 0 && (
                                  <div className="text-rose-400 font-medium">
                                    Lineage Penalty: -{Math.round(nodeDetailsQuery.data.meta.lineage_penalty)}%
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Node details attributes */}
                          <div className="space-y-2 text-xs">
                            <div className="flex justify-between py-1 border-b border-slate-800/40">
                              <span className="text-slate-400">Schema</span>
                              <span className="text-slate-200 font-mono">{nodeDetailsQuery.data.schema}</span>
                            </div>
                            {nodeDetailsQuery.data.database && (
                              <div className="flex justify-between py-1 border-b border-slate-800/40">
                                <span className="text-slate-400">Database</span>
                                <span className="text-slate-200 font-mono">{nodeDetailsQuery.data.database}</span>
                              </div>
                            )}
                            {nodeDetailsQuery.data.materialized_type && (
                              <div className="flex justify-between py-1 border-b border-slate-800/40">
                                <span className="text-slate-400">Materialized</span>
                                <span className="text-slate-200 capitalize font-mono">{nodeDetailsQuery.data.materialized_type}</span>
                              </div>
                            )}
                            {nodeDetailsQuery.data.owner && (
                              <div className="flex justify-between py-1 border-b border-slate-800/40">
                                <span className="text-slate-400">Owner</span>
                                <span className="text-slate-200">{nodeDetailsQuery.data.owner}</span>
                              </div>
                            )}
                            <div className="flex justify-between py-1 border-b border-slate-800/40">
                              <span className="text-slate-400">Last Updated</span>
                              <span className="text-slate-300 font-mono text-[10px]">
                                {nodeDetailsQuery.data.last_updated_at 
                                  ? new Date(nodeDetailsQuery.data.last_updated_at).toLocaleString()
                                  : 'Never'}
                              </span>
                            </div>
                          </div>

                          {/* Description */}
                          {nodeDetailsQuery.data.description && (
                            <div className="space-y-1 text-xs">
                              <span className="text-slate-400 font-semibold">Description</span>
                              <p className="p-2 bg-slate-900/30 border border-white/5 rounded text-slate-300 leading-relaxed text-[11px]">
                                {nodeDetailsQuery.data.description}
                              </p>
                            </div>
                          )}

                          {/* Schema comparison drift checker */}
                          <div className="pt-2 border-t border-slate-800 space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-slate-300">Schema Drift Analysis</span>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={handleCompareSchema}
                                disabled={isComparingSchema}
                                className="h-7 text-[10px] bg-slate-900 hover:bg-slate-800 text-white"
                              >
                                {isComparingSchema ? 'Checking...' : 'Run Schema Check'}
                              </Button>
                            </div>

                            {schemaCompareResult && (
                              <div className="rounded-lg border border-white/5 bg-slate-950/60 p-3 text-xs space-y-2 animate-fadeIn">
                                <div className="flex items-center justify-between">
                                  <span>Drift Status:</span>
                                  {schemaCompareResult.drift_detected ? (
                                    <Badge variant="destructive" className="text-[10px] px-1.5 py-0">DRIFT DETECTED</Badge>
                                  ) : (
                                    <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px] px-1.5 py-0">MATCHED</Badge>
                                  )}
                                </div>

                                {schemaCompareResult.drift_detected && (
                                  <div className="space-y-1.5 text-[10px] text-slate-300 font-mono">
                                    {schemaCompareResult.added?.length > 0 && (
                                      <div className="text-emerald-400">
                                        + Added ({schemaCompareResult.added.length}): {schemaCompareResult.added.join(', ')}
                                      </div>
                                    )}
                                    {schemaCompareResult.removed?.length > 0 && (
                                      <div className="text-rose-400">
                                        - Removed ({schemaCompareResult.removed.length}): {schemaCompareResult.removed.join(', ')}
                                      </div>
                                    )}
                                    {Object.keys(schemaCompareResult.modified || {}).length > 0 && (
                                      <div className="text-amber-400">
                                        * Modified ({Object.keys(schemaCompareResult.modified).length}):
                                        {Object.entries(schemaCompareResult.modified).map(([col, typ]: any) => (
                                          <div key={col} className="pl-2">
                                            {col}: {typ.expected} ➔ {typ.actual}
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                )}

                                {!schemaCompareResult.drift_detected && (
                                  <p className="text-[10px] text-slate-400">
                                    Actual table structure matches the baselined column specifications.
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </TabsContent>

                    {/* TAB 2: HEALTH SCORE PROPAGATION */}
                    <TabsContent value="propagation" className="p-4 m-0 space-y-3">
                      {healthPropagationQuery.isLoading ? (
                        <div className="text-center py-6 text-xs text-slate-500">Loading propagation path...</div>
                      ) : !healthPropagationQuery.data?.propagation?.length ? (
                        <div className="text-center py-6 text-xs text-slate-500">
                          No downstream nodes affected by score decay.
                        </div>
                      ) : (
                        <div className="space-y-3">
                          <div className="text-[11px] text-slate-400 leading-relaxed bg-slate-900/30 p-2 border border-white/5 rounded">
                            Any quality degradation propagates downstream with a <span className="font-semibold text-primary">0.9 decay multiplier</span> per hop.
                          </div>

                          <div className="space-y-2 max-h-[350px] overflow-y-auto pr-1">
                            {healthPropagationQuery.data.propagation.map((propNode: any) => (
                              <div key={propNode.node_id} className="p-2.5 rounded-lg border border-white/5 bg-slate-950/40 text-xs space-y-1.5">
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-slate-200 truncate max-w-[120px]">{propNode.name}</span>
                                  <Badge className="text-[9px] px-1 py-0 bg-slate-900 border-white/5 text-slate-400 font-mono">
                                    {propNode.hops} {propNode.hops === 1 ? 'hop' : 'hops'}
                                  </Badge>
                                </div>
                                
                                <div className="grid grid-cols-2 text-[10px] text-slate-400 gap-y-1 font-mono">
                                  <div>Base Score:</div>
                                  <div className="text-right text-slate-300">{Math.round(propNode.base_score)}%</div>
                                  
                                  <div className="text-rose-400/80">Propagation Penalty:</div>
                                  <div className="text-right text-rose-400 font-semibold">-{Math.round(propNode.propagated_penalty)}%</div>
                                  
                                  <div className="font-semibold">Resulting score:</div>
                                  <div className="text-right text-primary font-extrabold">{Math.round(propNode.resulting_score)}%</div>
                                </div>

                                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden mt-1">
                                  <div 
                                    className={`h-full rounded-full ${
                                      propNode.resulting_score >= 80 ? 'bg-emerald-500' : propNode.resulting_score >= 60 ? 'bg-amber-500' : 'bg-rose-500'
                                    }`}
                                    style={{ width: `${propNode.resulting_score}%` }}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </TabsContent>

                    {/* TAB 3: IMPACT & CRITICAL PATH */}
                    <TabsContent value="impact" className="p-4 m-0 space-y-4">
                      {/* Critical Path Highlighting Toggle */}
                      <div className="p-3 rounded-lg border border-white/5 bg-slate-950/40 flex items-center justify-between text-xs">
                        <div className="space-y-0.5">
                          <span className="font-bold text-slate-200 flex items-center gap-1">
                            <Zap className="h-3.5 w-3.5 text-rose-500 animate-pulse" /> Critical Path Tracing
                          </span>
                          <p className="text-[10px] text-slate-400">Highlight worst upstream penalty route</p>
                        </div>
                        <Button
                          size="sm"
                          variant={highlightCriticalPath ? 'destructive' : 'outline'}
                          onClick={() => setHighlightCriticalPath(!highlightCriticalPath)}
                          className="h-7 text-[10px]"
                        >
                          {highlightCriticalPath ? 'Disable Path' : 'Highlight Path'}
                        </Button>
                      </div>

                      {/* Critical Path List */}
                      {highlightCriticalPath && (
                        <div className="space-y-2 animate-fadeIn">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                            Upstream Path Route
                          </span>
                          {criticalPathQuery.isLoading ? (
                            <div className="text-center py-2 text-xs text-slate-500">Tracing critical path...</div>
                          ) : !criticalPathQuery.data || (criticalPathQuery.data as any[]).length === 0 ? (
                            <div className="text-center py-2 text-xs text-slate-500">No upstream path to trace.</div>
                          ) : (
                            <div className="space-y-1">
                              {(criticalPathQuery.data as any[]).map((pNode: any, idx: number) => (
                                <div key={pNode.node_id} className="flex items-center space-x-1.5 text-xs text-slate-300">
                                  {idx > 0 && <ArrowRight className="h-3 w-3 text-rose-500 shrink-0" />}
                                  <span 
                                    className={`truncate cursor-pointer hover:underline ${
                                      pNode.node_id === selectedNodeId ? 'text-rose-400 font-bold' : 'text-slate-300 font-medium'
                                    }`}
                                    onClick={() => handleSelectNode(pNode.node_id)}
                                  >
                                    {pNode.name}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Impact Analysis list */}
                      <div className="space-y-2 border-t border-slate-800 pt-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-300">Downstream Impact Analysis</span>
                          <Badge className="text-[10px] bg-slate-900 border-white/5 text-slate-400">
                            {impactQuery.data?.length || 0} Affected
                          </Badge>
                        </div>
                        <p className="text-[10px] text-slate-400">
                          Changes to this table recursively cascade downstream to these tables.
                        </p>

                        <div className="space-y-1.5 max-h-[200px] overflow-y-auto pr-1">
                          {impactQuery.isLoading ? (
                            <div className="text-center py-4 text-xs text-slate-500">Calculating impact tree...</div>
                          ) : !impactQuery.data || impactQuery.data.length === 0 ? (
                            <div className="text-center py-4 text-xs text-slate-500">No downstream dependents.</div>
                          ) : (
                            impactQuery.data.map((impactNodeId: string) => {
                              const shortName = impactNodeId.split('.').pop() || impactNodeId
                              return (
                                <div
                                  key={impactNodeId}
                                  onClick={() => handleSelectNode(impactNodeId)}
                                  className="flex items-center justify-between p-2 rounded bg-slate-900/30 hover:bg-slate-900/60 border border-white/5 cursor-pointer text-xs group"
                                >
                                  <span className="text-slate-300 font-mono text-[10px] truncate max-w-[150px]">
                                    {shortName}
                                  </span>
                                  <ArrowUpRight className="h-3.5 w-3.5 text-slate-500 group-hover:text-primary transition-colors" />
                                </div>
                              )
                            })
                          )}
                        </div>
                      </div>
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>

              {/* Time Travel Difference Info Card */}
              {timeOffset > 0 && diffQuery.data && (
                <Card className="glass-panel border-amber-500/10 shadow-lg">
                  <CardHeader className="pb-1.5 p-3">
                    <CardTitle className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5" /> Graph Mutations (Diff)
                    </CardTitle>
                    <CardDescription className="text-[10px] text-slate-400">
                      Comparing snapshot {OFFSETS[timeOffset].label} vs active
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-3 pt-0 text-[10px] space-y-1.5 text-slate-300 font-mono">
                    <div className="flex justify-between">
                      <span>Added Nodes:</span>
                      <span className={diffQuery.data.nodes?.added?.length > 0 ? 'text-emerald-400 font-bold' : ''}>
                        {diffQuery.data.nodes?.added?.length || 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Removed Nodes:</span>
                      <span className={diffQuery.data.nodes?.removed?.length > 0 ? 'text-rose-400 font-bold' : ''}>
                        {diffQuery.data.nodes?.removed?.length || 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Added Edges:</span>
                      <span className={diffQuery.data.edges?.added?.length > 0 ? 'text-emerald-400 font-bold' : ''}>
                        {diffQuery.data.edges?.added?.length || 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Removed Edges:</span>
                      <span className={diffQuery.data.edges?.removed?.length > 0 ? 'text-rose-400 font-bold' : ''}>
                        {diffQuery.data.edges?.removed?.length || 0}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>

          </div>
        )}
      </div>
    </ErrorBoundary>
  )
}

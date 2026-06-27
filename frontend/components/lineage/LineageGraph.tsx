'use client'

import React, { memo, useCallback, useEffect, useMemo, useState } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  Node,
  Edge,
  Position,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Database, FileCode, CheckCircle, HelpCircle, Eye, ShieldAlert, Award, AlertTriangle, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';

// Custom Node Component
const CustomLineageNode = memo(({ data }: { data: any }) => {
  const { name, type, trust_score, selected } = data;
  const [localExpanded, setLocalExpanded] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const isExpanded = data.isExpanded !== undefined ? data.isExpanded : localExpanded;
  const toggleExpand = data.toggleExpand || (() => setLocalExpanded(prev => !prev));

  const getIcon = () => {
    switch (type) {
      case 'source':
        return <Database className="h-5 w-5 text-indigo-500" />;
      case 'model':
        return <FileCode className="h-5 w-5 text-sky-500" />;
      case 'seed':
        return <Award className="h-5 w-5 text-teal-500" />;
      case 'test':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'exposure':
        return <Eye className="h-5 w-5 text-purple-500" />;
      case 'warehouse_table':
        return <Database className="h-5 w-5 text-emerald-500" />;
      default:
        return <HelpCircle className="h-5 w-5 text-slate-500" />;
    }
  };

  const score = trust_score !== undefined && trust_score !== null ? trust_score : 100;
  let scoreColor = 'bg-emerald-500';
  let badgeBg = 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400';
  let borderColor = selected 
    ? 'border-indigo-600 dark:border-indigo-400 ring-2 ring-indigo-600/20 dark:ring-indigo-400/20' 
    : 'border-slate-200 dark:border-slate-800';

  if (score < 60) {
    scoreColor = 'bg-rose-500';
    badgeBg = 'bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-400';
    if (!selected) borderColor = 'border-rose-500/40 dark:border-rose-500/20';
  } else if (score < 80) {
    scoreColor = 'bg-amber-500';
    badgeBg = 'bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400';
    if (!selected) borderColor = 'border-amber-500/40 dark:border-amber-500/20';
  }

  // Parse columns data format (either dict or array)
  const columns = useMemo(() => {
    if (!data.meta) return [];
    
    const metaCols = data.meta.columns;
    if (!metaCols) return [];

    let colsList: { name: string; type: string; penalty: number }[] = [];

    if (Array.isArray(metaCols)) {
      colsList = metaCols.map(col => {
        const name = typeof col === 'string' ? col : col.name || '';
        const type = typeof col === 'string' ? 'UNKNOWN' : col.type || 'UNKNOWN';
        const penalty = data.meta.column_penalties?.[name] || 0;
        return { name, type, penalty };
      });
    } else if (typeof metaCols === 'object') {
      colsList = Object.entries(metaCols).map(([colName, colVal]) => {
        const type = typeof colVal === 'string' ? colVal : (colVal as any)?.data_type || 'UNKNOWN';
        const penalty = data.meta.column_penalties?.[colName] || 0;
        return { name: colName, type, penalty };
      });
    }

    // Sort: columns with health decay/penalties first, then alphabetical
    return colsList.sort((a, b) => {
      if (b.penalty !== a.penalty) return b.penalty - a.penalty;
      return a.name.localeCompare(b.name);
    });
  }, [data.meta]);

  return (
    <div className={`px-4 py-3 shadow-md rounded-xl border-2 bg-card text-foreground ${borderColor} transition-all duration-200 w-72`}>
      <HandleComponent type="target" position={Position.Left} />
      
      <div className="flex items-center justify-between space-x-3">
        <div className="flex items-center space-x-2.5 w-48 overflow-hidden">
          <div className="p-2 bg-muted rounded-lg">
            {getIcon()}
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-semibold text-foreground truncate w-36" title={name}>
              {name}
            </span>
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">
              {type.replace('_', ' ')}
            </span>
          </div>
        </div>

        <div className={`px-2 py-0.5 rounded-full text-xs font-bold ${badgeBg} flex items-center space-x-1 shrink-0`}>
          <span className={`w-1.5 h-1.5 rounded-full ${scoreColor}`} />
          <span>{Math.round(score)}%</span>
        </div>
      </div>

      {score < 80 && (
        <div className="mt-1.5 pt-1.5 border-t border-border flex items-center text-[10px] text-amber-600 dark:text-amber-400">
          <AlertTriangle className="h-3 w-3 mr-1" />
          <span>Lineage Propagation Penalty Applied</span>
        </div>
      )}

      {columns.length > 0 && (
        <div className="mt-2.5 pt-2 border-t border-border nodrag">
          <button
            onClick={(e) => {
              e.stopPropagation();
              toggleExpand();
            }}
            className="w-full flex items-center justify-between text-[11px] font-semibold text-muted-foreground hover:text-foreground transition-colors"
          >
            <span>Columns ({columns.length})</span>
            {isExpanded ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      )}{isExpanded && (
            <div className="mt-2 space-y-1 max-h-60 overflow-y-auto pr-1 nodrag nowheel">
              {(showAll ? columns : columns.slice(0, 10)).map((col) => (
                <div
                  key={col.name}
                  className={`flex items-center justify-between p-1 rounded text-[10px] ${
                    col.penalty > 0
                      ? 'bg-rose-50/50 dark:bg-rose-950/20 border border-rose-100/50 dark:border-rose-900/30'
                      : 'hover:bg-muted'
                  }`}
                >
                  <div className="flex flex-col truncate pr-1">
                    <span
                      className={`font-mono font-medium truncate ${
                        col.penalty > 0
                          ? 'text-rose-700 dark:text-rose-400'
                          : 'text-foreground'
                      }`}
                      title={col.name}
                    >
                      {col.name}
                    </span>
                    <span className="text-[8px] text-muted-foreground font-sans tracking-wide uppercase">
                      {col.type}
                    </span>
                  </div>

                  {col.penalty > 0 && (
                    <div className="flex items-center space-x-1 text-rose-600 dark:text-rose-400 font-bold shrink-0">
                      <AlertCircle className="h-3 w-3 shrink-0" />
                      <span>-{Math.round(col.penalty)}%</span>
                    </div>
                  )}
                </div>
              ))}

              {columns.length > 10 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowAll(!showAll);
                  }}
                  className="w-full text-center text-[10px] text-indigo-600 dark:text-indigo-400 hover:underline pt-1 font-medium"
                >
                  {showAll ? 'Show less' : `Show more (+${columns.length - 10})`}
                </button>
              )}
            </div>
          )}
          
          <HandleComponent type="source" position={Position.Right} />
        </div>
      );
    });
CustomLineageNode.displayName = 'CustomLineageNode';

// Wrapper handles to satisfy React Flow layout requirements
import { Handle } from 'reactflow';
const HandleComponent = ({ type, position }: { type: 'source' | 'target', position: Position }) => (
  <Handle
    type={type}
    position={position}
    className="w-2 h-2 bg-muted-foreground border-2 border-background !top-1/2"
  />
);

interface LineageGraphProps {
  nodesData: any[];
  edgesData: any[];
  onSelectNode: (nodeId: string) => void;
  selectedNodeId: string | null;
  criticalPathNodeIds?: string[];
}

export default function LineageGraph({
  nodesData,
  edgesData,
  onSelectNode,
  selectedNodeId,
  criticalPathNodeIds = []
}: LineageGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [expandedNodeIds, setExpandedNodeIds] = useState<Set<string>>(new Set());

  const nodeTypes = useMemo(() => ({
    lineageNode: CustomLineageNode
  }), []);

  const onNodeDoubleClick = useCallback((_: React.MouseEvent, node: Node) => {
    setExpandedNodeIds((prev) => {
      const next = new Set(prev);
      if (next.has(node.id)) {
        next.delete(node.id);
      } else {
        next.add(node.id);
      }
      return next;
    });
  }, []);

  // Topological / grid layouter to arrange nodes horizontally from source to downstream
  const layoutGraph = useCallback((nodesList: any[], edgesList: any[]) => {
    // 1. Map adjacencies
    const adjList: Dict<string, string[]> = {};
    const inDegree: Dict<string, number> = {};

    nodesList.forEach(node => {
      adjList[node.node_id] = [];
      inDegree[node.node_id] = 0;
    });

    edgesList.forEach(edge => {
      if (adjList[edge.source_node_id]) {
        adjList[edge.source_node_id].push(edge.target_node_id);
      }
      if (inDegree[edge.target_node_id] !== undefined) {
        inDegree[edge.target_node_id]++;
      }
    });

    // 2. BFS topological-like level sorting
    const levels: Dict<string, number> = {};
    const queue: string[] = [];

    nodesList.forEach(node => {
      if (inDegree[node.node_id] === 0) {
        queue.push(node.node_id);
        levels[node.node_id] = 0;
      }
    });

    while (queue.length > 0) {
      const u = queue.shift()!;
      const currLevel = levels[u] || 0;
      
      (adjList[u] || []).forEach(v => {
        levels[v] = Math.max(levels[v] || 0, currLevel + 1);
        queue.push(v);
      });
    }

    // fallback levels for disconnected nodes
    nodesList.forEach(node => {
      if (levels[node.node_id] === undefined) {
        levels[node.node_id] = 0;
      }
    });

    // Group nodes by level to assign Y coordinates
    const nodesByLevel: Dict<number, string[]> = {};
    nodesList.forEach(node => {
      const lvl = levels[node.node_id];
      if (!nodesByLevel[lvl]) {
        nodesByLevel[lvl] = [];
      }
      nodesByLevel[lvl].push(node.node_id);
    });

    // Create React Flow node representations
    const formattedNodes: Node[] = nodesList.map(node => {
      const lvl = levels[node.node_id];
      const indexInLevel = nodesByLevel[lvl].indexOf(node.node_id);
      const levelCount = nodesByLevel[lvl].length;

      // Center layout vertically per level
      const x = lvl * 380 + 50;
      const y = (indexInLevel - (levelCount - 1) / 2) * 120 + 250;

      return {
        id: node.node_id,
        type: 'lineageNode',
        position: { x, y },
        data: {
          ...node,
          selected: node.node_id === selectedNodeId,
          isExpanded: expandedNodeIds.has(node.node_id),
          toggleExpand: () => {
            setExpandedNodeIds((prev) => {
              const next = new Set(prev);
              if (next.has(node.node_id)) {
                next.delete(node.node_id);
              } else {
                next.add(node.node_id);
              }
              return next;
            });
          }
        }
      };
    });

    // Create edges representations
    const formattedEdges: Edge[] = edgesList.map(edge => {
      const isCritical = criticalPathNodeIds.includes(edge.source_node_id) && 
                         criticalPathNodeIds.includes(edge.target_node_id);

      return {
        id: `e-${edge.source_node_id}-${edge.target_node_id}`,
        source: edge.source_node_id,
        target: edge.target_node_id,
        animated: isCritical || edge.edge_type === 'depends_on',
        style: {
          stroke: isCritical ? '#f43f5e' : 'rgba(156, 163, 175, 0.4)',
          strokeWidth: isCritical ? 3 : 2
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isCritical ? '#f43f5e' : 'rgba(156, 163, 175, 0.4)'
        }
      };
    });

    return { nodes: formattedNodes, edges: formattedEdges };
  }, [selectedNodeId, criticalPathNodeIds, expandedNodeIds]);

  // Re-layout when raw nodes/edges data or selections change
  useEffect(() => {
    const { nodes: fn, edges: fe } = layoutGraph(nodesData, edgesData);
    setNodes(fn);
    setEdges(fe);
  }, [nodesData, edgesData, layoutGraph, setNodes, setEdges]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    onSelectNode(node.id);
  }, [onSelectNode]);

  return (
    <div className="w-full h-full border border-border rounded-2xl overflow-hidden bg-muted/10 relative min-h-[500px]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        onNodeDoubleClick={onNodeDoubleClick}
        fitView
        className="text-foreground"
      >
        <Controls className="bg-popover border border-border shadow rounded" />
        <MiniMap
          nodeColor={(n) => {
            const score = n.data?.trust_score ?? 100;
            if (score < 60) return '#f43f5e';
            if (score < 80) return '#f59e0b';
            return '#10b981';
          }}
          className="bg-popover border border-border shadow rounded"
          maskColor="rgba(128, 128, 128, 0.1)"
        />
        <Background gap={16} size={1} color="#94a3b8" style={{ opacity: 0.15 }} />
      </ReactFlow>
    </div>
  );
}

// Inline Dict helper
type Dict<K extends string | number, V> = { [key in K]: V };

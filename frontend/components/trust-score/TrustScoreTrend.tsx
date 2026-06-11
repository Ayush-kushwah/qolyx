'use client'

import React from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine
} from 'recharts'
import { format } from 'date-fns'
import { TrustScore } from '@/types'

interface TrustScoreTrendProps {
  data: TrustScore[]
  height?: number
}

export default function TrustScoreTrend({ data, height = 300 }: TrustScoreTrendProps) {
  // Map data to chart-friendly values
  const chartData = data.map((item) => ({
    ...item,
    formattedDate: format(new Date(item.created_at), 'MMM dd, HH:mm'),
    score: item.trust_score,
  }))

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item: TrustScore = payload[0].payload
      return (
        <div className="bg-slate-900/90 backdrop-blur-md border border-white/10 p-4 rounded-lg shadow-xl text-xs space-y-2 select-none z-50">
          <p className="font-semibold text-slate-400">{format(new Date(item.created_at), 'PPP p')}</p>
          <div className="flex items-center gap-2">
            <span className="text-slate-400">Score:</span>
            <span className="font-bold text-sm text-slate-100">{item.trust_score}</span>
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
              item.trust_score_status === 'HEALTHY' ? 'bg-healthy/10 text-healthy border border-healthy/20' :
              item.trust_score_status === 'WARNING' ? 'bg-warning/10 text-warning border border-warning/20' :
              item.trust_score_status === 'DEGRADED' ? 'bg-degraded/10 text-degraded border border-degraded/20' :
              'bg-critical/10 text-critical border border-critical/20'
            }`}>
              {item.trust_score_status}
            </span>
          </div>
          <div className="pt-1 border-t border-white/5 space-y-1">
            <p className="text-[10px] text-slate-500">PENALTY BREAKDOWN</p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-slate-400 text-[10px]">
              <span>Contract: -{item.contract_penalty}</span>
              <span>Anomaly: -{item.anomaly_penalty}</span>
              <span>dbt: -{item.dbt_penalty}</span>
              <span>Freshness: -{item.freshness_penalty}</span>
              <span>Volume: -{item.volume_penalty}</span>
            </div>
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <div className="w-full h-full min-h-[300px]">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" />
          <XAxis 
            dataKey="formattedDate" 
            stroke="#64748b" 
            fontSize={10}
            tickLine={false}
            axisLine={false}
          />
          <YAxis 
            domain={[0, 100]} 
            stroke="#64748b" 
            fontSize={10}
            tickLine={false}
            axisLine={false}
            ticks={[0, 20, 40, 60, 80, 100]}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={70} stroke="rgba(239, 68, 68, 0.3)" strokeDasharray="5 5" label={{ value: 'Incident Threshold (70)', fill: 'rgba(239, 68, 68, 0.5)', fontSize: 9, position: 'top' }} />
          <Line
            type="monotone"
            dataKey="score"
            stroke="url(#colorScore)"
            strokeWidth={3}
            dot={{ r: 4, stroke: "#6366f1", strokeWidth: 1, fill: "#0f172a" }}
            activeDot={{ r: 6, stroke: "#818cf8", strokeWidth: 2, fill: "#6366f1" }}
          />
          <defs>
            <linearGradient id="colorScore" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#818cf8" />
              <stop offset="100%" stopColor="#c084fc" />
            </linearGradient>
          </defs>
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

'use client'

import React from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell
} from 'recharts'

interface PenaltyBreakdownProps {
  contract: number
  freshness: number
  volume: number
  anomaly: number
  dbt: number
  height?: number
}

export default function PenaltyBreakdown({
  contract,
  freshness,
  volume,
  anomaly,
  dbt,
  height = 250
}: PenaltyBreakdownProps) {
  // Setup data format
  const chartData = [
    { name: 'Schema Contracts', value: contract, max: 40, fill: '#6366f1' },
    { name: 'Freshness Lag', value: freshness, max: 30, fill: '#3b82f6' },
    { name: 'Volume Drift', value: volume, max: 30, fill: '#14b8a6' },
    { name: 'ML Anomalies', value: anomaly, max: 20, fill: '#f59e0b' },
    { name: 'DBT Test Failures', value: dbt, max: 20, fill: '#e11d48' },
  ]

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-slate-900/90 backdrop-blur-md border border-white/10 p-3 rounded-lg shadow-xl text-xs space-y-1 select-none z-50">
          <p className="font-bold text-slate-100">{data.name}</p>
          <p className="text-slate-400">
            Penalty: <span className="font-bold text-rose-400">-{data.value} pts</span>
          </p>
          <p className="text-[10px] text-slate-500">Maximum possible deduction: {data.max} pts</p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="w-full h-full min-h-[250px]">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
        >
          <XAxis 
            type="number" 
            stroke="#64748b" 
            fontSize={10} 
            tickLine={false} 
            axisLine={false}
            domain={[0, 40]}
          />
          <YAxis 
            dataKey="name" 
            type="category" 
            stroke="#94a3b8" 
            fontSize={10} 
            tickLine={false} 
            axisLine={false}
            width={120}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={16}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

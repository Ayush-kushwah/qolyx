'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { 
  LayoutDashboard, 
  Activity, 
  AlertOctagon, 
  FileCheck, 
  Bell, 
  Users, 
  TrendingUp, 
  Settings, 
  ShieldCheck,
  ServerCrash
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard, category: 'Monitoring' },
  { name: 'Trust Score', href: '/trust-score', icon: TrendingUp, category: 'Monitoring' },
  { name: 'Anomalies', href: '/anomalies', icon: Activity, category: 'Monitoring' },
  { name: 'Incidents', href: '/incidents', icon: AlertOctagon, category: 'Monitoring' },
  { name: 'Data Contracts', href: '/contracts', icon: FileCheck, category: 'Configuration' },
  { name: 'Alert Configs', href: '/alerts', icon: Bell, category: 'Configuration' },
  { name: 'On-Call Rotations', href: '/rotations', icon: Users, category: 'Configuration' },
  { name: 'Escalations', href: '/escalation', icon: ServerCrash, category: 'Configuration' },
  { name: 'Settings', href: '/settings', icon: Settings, category: 'System' },
]

export default function MobileNav() {
  const pathname = usePathname()

  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === '/'
    }
    return pathname.startsWith(href)
  }

  const categories = ['Monitoring', 'Configuration', 'System']

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-950 text-slate-900 dark:text-white select-none">
      {/* Brand header */}
      <div className="flex h-16 items-center px-6 border-b border-slate-200 dark:border-slate-800">
        <Link href="/" className="flex items-center select-none w-full">
          <>
            <img 
              src="/logo.png" 
              alt="Qolyx Logo" 
              className="h-9 w-auto object-contain px-2 dark:hidden"
            />
            <img 
              src="/logo-dark.png" 
              alt="Qolyx Logo" 
              className="h-9 w-auto object-contain px-2 hidden dark:block"
            />
          </>
        </Link>
      </div>

      {/* Navigation items list */}
      <div className="flex-1 overflow-y-auto py-6 px-4 space-y-6">
        {categories.map((category) => {
          const items = navigation.filter(item => item.category === category)
          return (
            <div key={category} className="space-y-1">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-3 mb-2">
                {category}
              </h3>
              <ul className="space-y-1">
                {items.map((item) => {
                  const active = isActive(item.href)
                  const Icon = item.icon
                  return (
                    <li key={item.name}>
                      <Link href={item.href} className={cn(
                        "flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200",
                        active 
                          ? "bg-primary text-white shadow-lg shadow-primary/20" 
                          : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5"
                      )}>
                        <Icon className={cn("h-5 w-5 flex-shrink-0", active ? "text-white" : "text-slate-500 dark:text-slate-400")} />
                        <span>{item.name}</span>
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </div>
          )
        })}
      </div>
    </div>
  )
}

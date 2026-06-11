'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useUiStore } from '@/store/uiStore'
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
  ChevronLeft, 
  ChevronRight,
  ShieldCheck,
  ServerCrash,
  User,
  GitBranch
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard, category: 'Monitoring' },
  { name: 'Trust Score', href: '/trust-score', icon: TrendingUp, category: 'Monitoring' },
  { name: 'Anomalies', href: '/anomalies', icon: Activity, category: 'Monitoring' },
  { name: 'Incidents', href: '/incidents', icon: AlertOctagon, category: 'Monitoring' },
  { name: 'Lineage', href: '/lineage', icon: GitBranch, category: 'Monitoring' },
  { name: 'Data Contracts', href: '/contracts', icon: FileCheck, category: 'Configuration' },
  { name: 'Alert Configs', href: '/alerts', icon: Bell, category: 'Configuration' },
  { name: 'On-Call Rotations', href: '/rotations', icon: Users, category: 'Configuration' },
  { name: 'Escalations', href: '/escalation', icon: ServerCrash, category: 'Configuration' },
  { name: 'Profile', href: '/profile', icon: User, category: 'System' },
  { name: 'Settings', href: '/settings', icon: Settings, category: 'System' },
]

export default function Sidebar() {
  const pathname = usePathname()
  const { sidebarCollapsed, toggleSidebar } = useUiStore()

  // Helper to check active link
  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === '/'
    }
    return pathname.startsWith(href)
  }

  // Group items by category
  const categories = ['Monitoring', 'Configuration', 'System']

  return (
    <aside className={cn(
      "hidden md:flex md:flex-col border-r h-screen relative bg-white dark:bg-slate-950 transition-all duration-300 ease-in-out border-slate-200 dark:border-slate-800",
      sidebarCollapsed ? "w-20" : "w-64"
    )}>
      {/* Brand logo header */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-slate-200 dark:border-slate-800">
        <Link href="/" className="flex items-center select-none w-full">
          {sidebarCollapsed ? (
            <div className="bg-primary/10 dark:bg-primary/20 p-2 rounded-lg border border-primary/20 dark:border-primary/30 flex items-center justify-center mx-auto">
              <ShieldCheck className="h-6 w-6 text-primary" />
            </div>
          ) : (
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
          )}
        </Link>
      </div>

      {/* Navigation menu list */}
      <div className="flex-1 overflow-y-auto py-6 px-3 space-y-6">
        {categories.map((category) => {
          const items = navigation.filter(item => item.category === category)
          return (
            <div key={category} className="space-y-1">
              {!sidebarCollapsed ? (
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-3 mb-2">
                  {category}
                </h3>
              ) : (
                <div className="h-px bg-white/5 my-4" />
              )}
              
              <ul className="space-y-1">
                {items.map((item) => {
                  const active = isActive(item.href)
                  const Icon = item.icon
                  return (
                    <li key={item.name}>
                      <Link href={item.href} className={cn(
                        "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200 group relative",
                        active 
                          ? "bg-primary text-white shadow-lg shadow-primary/20" 
                          : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/50"
                      )}>
                        <Icon className={cn("h-5 w-5 flex-shrink-0", active ? "text-white" : "text-slate-500 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-white")} />
                        {!sidebarCollapsed && <span>{item.name}</span>}
                        {sidebarCollapsed && (
                          <div className="absolute left-full ml-2 px-2 py-1 bg-slate-900 border border-white/10 rounded-md text-xs font-medium text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-50 shadow-xl">
                            {item.name}
                          </div>
                        )}
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </div>
          )
        })}
      </div>

      {/* Collapse button bottom */}
      <button 
        onClick={toggleSidebar}
        className="absolute top-20 -right-3 bg-slate-100 hover:bg-slate-200 dark:bg-slate-900 dark:hover:bg-slate-800 border border-slate-200 dark:border-white/10 p-1.5 rounded-full text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-all shadow-md z-40 hidden md:block"
      >
        {sidebarCollapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
      </button>
    </aside>
  )
}

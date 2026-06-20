'use client'

import React from 'react'
import { usePathname } from 'next/navigation'
import Sidebar from './Sidebar'
import Header from './Header'

export default function LayoutContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isAuthPage = pathname === '/login' || pathname === '/register'

  if (isAuthPage) {
    return <main className="min-h-screen bg-slate-950/40">{children}</main>
  }

  return (
    <div className="flex min-h-screen overflow-hidden">
      {/* Sidebar Component */}
      <Sidebar />

      {/* Main Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header Component */}
        <Header />

        {/* Viewport */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-slate-950/20">
          {children}
        </main>
      </div>
    </div>
  )
}

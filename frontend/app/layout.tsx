import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import '@/styles/globals.css'
import { Providers } from '@/components/Providers'

import Sidebar from '@/components/layout/Sidebar'
import Header from '@/components/layout/Header'

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' })

export const metadata: Metadata = {
  title: 'Qolyx — Premium Data Reliability Platform',
  description: 'AI-native data quality enforcement, multi-dimensional anomaly detection, relational data lineage tracing, and unified trust score mapping.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} min-h-screen antialiased bg-background text-foreground`}>
        <Providers>
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
        </Providers>
      </body>
    </html>
  )
}

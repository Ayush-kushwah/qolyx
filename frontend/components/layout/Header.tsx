'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useTheme } from 'next-themes'
import { useUiStore } from '@/store/uiStore'
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuLabel, 
  DropdownMenuSeparator, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import MobileNav from './MobileNav'
import { Sun, Moon, Menu, User, LogOut } from 'lucide-react'
import { logoutUser } from '@/lib/api'

// Page titles mapping based on path
const getPageTitle = (pathname: string) => {
  if (pathname === '/') return 'System Overview'
  if (pathname.startsWith('/trust-score')) return 'Dataset Trust Scores'
  if (pathname.startsWith('/anomalies')) return 'Statistical Anomalies'
  if (pathname.startsWith('/incidents')) return 'Incident Command Center'
  if (pathname.startsWith('/contracts')) return 'Data Contracts Expectations'
  if (pathname.startsWith('/alerts')) return 'Alert Routing Rules'
  if (pathname.startsWith('/rotations')) return 'On-Call Rotations Schedule'
  if (pathname.startsWith('/escalation')) return 'Escalation Policies Severity'
  if (pathname.startsWith('/settings')) return 'Global Configurations'
  return 'Qolyx Platform'
}

export default function Header() {
  const pathname = usePathname()
  const router = useRouter()
  const { theme, setTheme } = useTheme()

  const handleSignOut = async () => {
    try {
      await logoutUser()
      router.push('/login')
      router.refresh()
    } catch (err) {
      console.error('Failed to log out:', err)
    }
  }

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 dark:border-slate-800 px-6 bg-white dark:bg-slate-950 z-30 select-none">
      {/* Page Title / Mobile Menu */}
      <div className="flex items-center gap-4">
        {/* Mobile menu trigger */}
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white">
              <Menu className="h-6 w-6" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="p-0 bg-white dark:bg-slate-950 text-slate-900 dark:text-white w-64 border-r border-slate-200 dark:border-slate-800">
            <MobileNav />
          </SheetContent>
        </Sheet>
        
        <h1 className="font-extrabold text-lg md:text-xl tracking-tight bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-400 bg-clip-text text-transparent">
          {getPageTitle(pathname)}
        </h1>
      </div>

      {/* User Actions */}
      <div className="flex items-center gap-4">
        {/* System Health Badge */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-healthy/10 border border-healthy/20 text-healthy text-xs font-semibold">
          <span className="h-1.5 w-1.5 rounded-full bg-healthy animate-pulse" />
          System Healthy
        </div>

        {/* Theme Toggle */}
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white rounded-lg hover:bg-slate-100 dark:hover:bg-white/5"
        >
          <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Toggle theme</span>
        </Button>

        {/* User Account Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-8 w-8 rounded-full border border-white/10 hover:bg-white/5">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary/20 text-primary text-xs font-bold font-sans">
                  AD
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white rounded-lg shadow-xl" align="end" forceMount>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-semibold leading-none">Administrator</p>
                <p className="text-xs leading-none text-slate-500 dark:text-slate-400">admin@qolyx.io</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-slate-100 dark:bg-white/5" />
            <Link href="/profile" className="w-full">
              <DropdownMenuItem className="hover:bg-slate-100 dark:hover:bg-white/5 cursor-pointer flex items-center gap-2 text-slate-700 dark:text-slate-200 w-full">
                <User className="h-4 w-4 text-slate-500 dark:text-slate-400" />
                <span>Profile Settings</span>
              </DropdownMenuItem>
            </Link>
            <DropdownMenuItem onClick={handleSignOut} className="hover:bg-slate-100 dark:hover:bg-white/5 cursor-pointer flex items-center gap-2 text-rose-500 hover:text-rose-400">
              <LogOut className="h-4 w-4" />
              <span>Sign out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}

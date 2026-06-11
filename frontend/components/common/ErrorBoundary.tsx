'use client'

import React, { Component, ErrorInfo, ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { AlertOctagon, RefreshCw } from 'lucide-react'

interface Props {
  children?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in boundary:', error, errorInfo)
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null })
    window.location.reload()
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center min-h-[400px] select-none">
          <div className="bg-critical/20 p-4 rounded-full border border-critical/30 mb-4">
            <AlertOctagon className="h-12 w-12 text-critical" />
          </div>
          <h2 className="text-xl font-bold mb-2">Something went wrong</h2>
          <p className="text-slate-400 text-sm max-w-md mb-6 leading-relaxed">
            An unexpected error occurred while rendering this section: <br/>
            <code className="text-rose-400 text-xs bg-slate-950 px-2 py-1 rounded block mt-2 break-all border border-white/5">
              {this.state.error?.message || 'Unknown Error'}
            </code>
          </p>
          <Button onClick={this.handleReset} className="flex items-center gap-2 shadow-lg hover:shadow-primary/20">
            <RefreshCw className="h-4 w-4" />
            Reload Page
          </Button>
        </div>
      )
    }

    return this.props.children
  }
}

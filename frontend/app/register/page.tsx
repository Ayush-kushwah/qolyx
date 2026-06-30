'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Shield, Mail, Lock, User, UserCheck, Loader2, ArrowRight } from 'lucide-react'
import { registerUser, verifyEmail } from '@/lib/api'

export default function RegisterPage() {
  const router = useRouter()
  
  // Registration form state
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Verification state
  const [showVerification, setShowVerification] = useState(false)
  const [userId, setUserId] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [isVerifying, setIsVerifying] = useState(false)
  const [verificationError, setVerificationError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    try {
      const res = await registerUser({ name, email, username, password })
      if (res?.auto_verified) {
        setSuccess(true)
        setTimeout(() => {
          router.push('/login')
        }, 2000)
      } else {
        setUserId(res?.user_id || '')
        setShowVerification(true)
      }
    } catch (err: any) {
      setError(err?.message || 'Registration failed. Username or email may be taken.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsVerifying(true)
    setVerificationError(null)

    try {
      await verifyEmail({ user_id: userId, code: otpCode })
      setSuccess(true)
      setShowVerification(false)
      setTimeout(() => {
        router.push('/login')
      }, 2000)
    } catch (err: any) {
      setVerificationError(err?.message || 'Invalid verification code. Please check your inbox.')
    } finally {
      setIsVerifying(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background text-foreground px-4 py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background design accents */}
      <div className="absolute top-1/4 left-1/4 h-80 w-80 rounded-full bg-violet-600/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 h-80 w-80 rounded-full bg-cyan-600/10 blur-[120px] pointer-events-none" />

      <div className="w-full max-w-md space-y-8 relative z-10">
        <div className="flex flex-col items-center">
          <div className="flex justify-center mb-4">
            <img
              src="/logo.png"
              alt="Qolyx Logo"
              className="h-12 w-auto object-contain dark:hidden animate-pulse-glow"
            />
            <img
              src="/logo-dark.png"
              alt="Qolyx Logo"
              className="h-12 w-auto object-contain hidden dark:block animate-pulse-glow"
            />
          </div>
          <h2 className="mt-2 text-center text-3xl font-extrabold tracking-tight text-foreground">
            {showVerification ? 'Verify Your Email' : 'Create Operator Account'}
          </h2>
          <p className="mt-2 text-center text-sm text-muted-foreground">
            {showVerification 
              ? `We sent a 6-digit verification code to ${email}`
              : 'Register to set up dynamic monitoring policies'
            }
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-8 shadow-2xl backdrop-blur-xl">
          {success ? (
            <div className="flex flex-col items-center text-center space-y-4 py-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/15 border border-emerald-500/20 text-emerald-400">
                <UserCheck className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-foreground">Registration Complete</h3>
              <p className="text-sm text-muted-foreground">Your operator account has been created and verified. Redirecting to login...</p>
            </div>
          ) : showVerification ? (
            <form className="space-y-6" onSubmit={handleVerifyOtp}>
              {verificationError && (
                <div className="rounded-lg bg-rose-500/15 border border-rose-500/20 p-4 text-sm text-rose-400">
                  {verificationError}
                </div>
              )}

              <div>
                <label htmlFor="otp" className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 text-center">
                  6-Digit Verification Code
                </label>
                <input
                  id="otp"
                  name="otp"
                  type="text"
                  required
                  maxLength={6}
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                  className="block w-full rounded-lg border border-border bg-background py-3 text-center text-2xl font-mono tracking-[0.75em] text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="000000"
                />
              </div>

              <div>
                <button
                  type="submit"
                  disabled={isVerifying || otpCode.length < 6}
                  className="group relative flex w-full justify-center rounded-lg bg-primary py-2.5 px-4 text-sm font-semibold text-white hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background transition-colors disabled:opacity-50"
                >
                  {isVerifying ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <span className="flex items-center gap-1.5">
                      Verify Code <ArrowRight className="h-4 w-4" />
                    </span>
                  )}
                </button>
              </div>
            </form>
          ) : (
            <form className="space-y-4" onSubmit={handleSubmit}>
              {error && (
                <div className="rounded-lg bg-rose-500/15 border border-rose-500/20 p-4 text-sm text-rose-400">
                  {error}
                </div>
              )}

              <div className="space-y-3">
                <div>
                  <label htmlFor="fullname" className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                    Full Name
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                      <User className="h-4 w-4 text-slate-500" />
                    </div>
                    <input
                      id="fullname"
                      name="fullname"
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="block w-full rounded-lg border border-border bg-background py-2 pl-10 pr-3 text-sm text-foreground placeholder-slate-500/80 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                      placeholder="Ayush Kushwah"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="username" className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                    Username
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                      <User className="h-4 w-4 text-slate-500" />
                    </div>
                    <input
                      id="username"
                      name="username"
                      type="text"
                      required
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="block w-full rounded-lg border border-border bg-background py-2 pl-10 pr-3 text-sm text-foreground placeholder-slate-500/80 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                      placeholder="ayushk"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="email" className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                    Email Address
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                      <Mail className="h-4 w-4 text-slate-500" />
                    </div>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="block w-full rounded-lg border border-border bg-background py-2 pl-10 pr-3 text-sm text-foreground placeholder-slate-500/80 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                      placeholder="name@company.com"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="password" className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                    Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                      <Lock className="h-4 w-4 text-slate-500" />
                    </div>
                    <input
                      id="password"
                      name="password"
                      type="password"
                      required
                      minLength={8}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="block w-full rounded-lg border border-border bg-background py-2 pl-10 pr-3 text-sm text-foreground placeholder-slate-500/80 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                      placeholder="•••••••• (Min 8 chars)"
                    />
                  </div>
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="group relative flex w-full justify-center rounded-lg bg-primary py-2.5 px-4 text-sm font-semibold text-white hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background transition-colors disabled:opacity-50"
                >
                  {isLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <span className="flex items-center gap-1.5">
                      Register Operator <ArrowRight className="h-4 w-4" />
                    </span>
                  )}
                </button>
              </div>
            </form>
          )}

          <div className="mt-6 border-t border-border pt-6 text-center text-xs text-muted-foreground">
            {showVerification ? (
              <button 
                onClick={() => setShowVerification(false)} 
                className="font-semibold text-primary hover:text-primary/80 transition-colors"
              >
                Back to Registration
              </button>
            ) : (
              <>
                Already have an account?{' '}
                <Link href="/login" className="font-semibold text-primary hover:text-primary/80 transition-colors">
                  Sign In
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

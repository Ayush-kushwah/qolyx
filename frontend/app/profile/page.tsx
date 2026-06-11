'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useProfile, useUpdateProfile, useUploadAvatar, useDeleteAvatar } from '@/hooks/useProfile'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar'
import {
  User,
  Mail,
  Shield,
  Bell,
  Palette,
  Camera,
  Trash,
  Save,
  Loader2,
  Clock,
} from 'lucide-react'
import ChangePasswordModal from '@/components/profile/ChangePasswordModal'
import ActiveSessions from '@/components/profile/ActiveSessions'
import LoginHistoryModal from '@/components/profile/LoginHistoryModal'
import DataExport from '@/components/profile/DataExport'
import DeleteAccount from '@/components/profile/DeleteAccount'

export default function ProfilePage() {
  const { data: profile, isLoading, isError } = useProfile()
  const updateProfileMutation = useUpdateProfile()
  const uploadAvatarMutation = useUploadAvatar()
  const deleteAvatarMutation = useDeleteAvatar()

  const fileInputRef = useRef<HTMLInputElement>(null)

  // Local state for Account form fields
  const [name, setName] = useState('')
  const [username, setUsername] = useState('')
  const [jobTitle, setJobTitle] = useState('')
  const [department, setDepartment] = useState('')

  // Local state for Notifications form fields
  const [notifyEmail, setNotifyEmail] = useState(true)
  const [notifySlack, setNotifySlack] = useState(true)
  const [notifyTelegram, setNotifyTelegram] = useState(false)
  const [notifySeverity, setNotifySeverity] = useState('MEDIUM')
  const [quietHoursEnabled, setQuietHoursEnabled] = useState(false)
  const [quietHoursStart, setQuietHoursStart] = useState('22:00')
  const [quietHoursEnd, setQuietHoursEnd] = useState('08:00')

  // Local state for Appearance form fields
  const [timezone, setTimezone] = useState('UTC')
  const [theme, setTheme] = useState('system')
  const [dateFormat, setDateFormat] = useState('ISO')

  useEffect(() => {
    if (profile) {
      setName(profile.name || '')
      setUsername(profile.username || '')
      setJobTitle(profile.job_title || '')
      setDepartment(profile.department || '')

      const prefs = profile.notification_preferences || {}
      setNotifyEmail(prefs.email !== false)
      setNotifySlack(prefs.slack !== false)
      setNotifyTelegram(prefs.telegram === true)
      setNotifySeverity(prefs.severity || 'MEDIUM')
      
      const qh = prefs.quiet_hours || {}
      setQuietHoursEnabled(qh.enabled === true)
      setQuietHoursStart(qh.start || '22:00')
      setQuietHoursEnd(qh.end || '08:00')

      setTimezone(profile.timezone || 'UTC')
      setTheme(profile.theme || 'system')
      setDateFormat(profile.date_format || 'ISO')
    }
  }, [profile])

  if (isLoading) {
    return (
      <div className="flex h-[70vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
      </div>
    )
  }

  if (isError || !profile) {
    return (
      <div className="p-6">
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-500 text-sm">
          Failed to load user profile configurations. Ensure database and API engine are running.
        </div>
      </div>
    )
  }

  const handleAvatarClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadAvatarMutation.mutate(file)
    }
  }

  const handleSaveAccount = (e: React.FormEvent) => {
    e.preventDefault()
    updateProfileMutation.mutate({
      name,
      username,
      job_title: jobTitle,
      department,
    })
  }

  const handleSaveNotifications = (e: React.FormEvent) => {
    e.preventDefault()
    updateProfileMutation.mutate({
      notification_preferences: {
        email: notifyEmail,
        slack: notifySlack,
        telegram: notifyTelegram,
        severity: notifySeverity,
        quiet_hours: {
          enabled: quietHoursEnabled,
          start: quietHoursStart,
          end: quietHoursEnd
        }
      }
    })
  }

  const handleSaveAppearance = (e: React.FormEvent) => {
    e.preventDefault()
    updateProfileMutation.mutate({
      timezone,
      theme,
      date_format: dateFormat,
    })
  }

  // Generate fallback avatar text
  const initials = name
    ? name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
    : 'US'

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-6 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-4">
          <div className="relative group cursor-pointer" onClick={handleAvatarClick}>
            <Avatar className="h-20 w-20 border-2 border-slate-200 dark:border-white/10 hover:opacity-85 transition-opacity">
              {profile.avatar_url ? (
                <AvatarImage src={`http://localhost:8000${profile.avatar_url}`} alt={profile.name} className="object-cover" />
              ) : (
                <AvatarFallback className="bg-primary/20 text-primary font-bold text-2xl font-sans">
                  {initials}
                </AvatarFallback>
              )}
            </Avatar>
            <div className="absolute inset-0 flex items-center justify-center bg-black/40 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
              <Camera className="h-6 w-6 text-white" />
            </div>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
              accept="image/*"
            />
          </div>
          <div>
            <h2 className="text-2xl font-extrabold tracking-tight">{profile.name}</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">@{profile.username} • {profile.email}</p>
            {profile.avatar_url && (
              <Button
                variant="link"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation()
                  deleteAvatarMutation.mutate()
                }}
                className="text-rose-500 hover:text-rose-400 p-0 h-auto text-xs mt-1"
              >
                <Trash className="h-3 w-3 mr-1" /> Remove Photo
              </Button>
            )}
          </div>
        </div>
      </div>

      <Tabs defaultValue="account" className="w-full">
        <TabsList className="grid w-full grid-cols-4 max-w-md bg-slate-100 dark:bg-slate-800">
          <TabsTrigger value="account" className="flex items-center gap-1">
            <User className="h-4 w-4" />
            <span>Account</span>
          </TabsTrigger>
          <TabsTrigger value="security" className="flex items-center gap-1">
            <Shield className="h-4 w-4" />
            <span>Security</span>
          </TabsTrigger>
          <TabsTrigger value="notifications" className="flex items-center gap-1">
            <Bell className="h-4 w-4" />
            <span>Alerts</span>
          </TabsTrigger>
          <TabsTrigger value="appearance" className="flex items-center gap-1">
            <Palette className="h-4 w-4" />
            <span>Preferences</span>
          </TabsTrigger>
        </TabsList>

        {/* Account Tab Content */}
        <TabsContent value="account" className="mt-6">
          <form onSubmit={handleSaveAccount}>
            <Card className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
              <CardHeader>
                <CardTitle className="text-lg font-bold">Profile Details</CardTitle>
                <CardDescription className="text-slate-500 dark:text-slate-400">
                  Update your personal details and contact card.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="full-name">Full Name</Label>
                    <Input
                      id="full-name"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="username-field">Username</Label>
                    <Input
                      id="username-field"
                      required
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="job-title-field">Job Title</Label>
                    <Input
                      id="job-title-field"
                      placeholder="e.g. Data Reliability Engineer"
                      value={jobTitle}
                      onChange={(e) => setJobTitle(e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="dept-field">Department</Label>
                    <Input
                      id="dept-field"
                      placeholder="e.g. Data Engineering"
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email-field">Email Address</Label>
                  <div className="relative">
                    <Input
                      id="email-field"
                      disabled
                      value={profile.email}
                      className="bg-slate-100 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800 text-slate-500 cursor-not-allowed pl-10"
                    />
                    <Mail className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
                  </div>
                  <p className="text-[10px] text-slate-400 dark:text-slate-500">Contact details can only be changed by system administrators.</p>
                </div>
              </CardContent>
              <CardFooter className="border-t border-slate-100 dark:border-slate-800 pt-4 flex justify-end">
                <Button type="submit" disabled={updateProfileMutation.isPending} className="bg-primary hover:bg-primary/95 text-white flex items-center gap-1.5">
                  {updateProfileMutation.isPending ? (
                    <span>Saving...</span>
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      <span>Save Changes</span>
                    </>
                  )}
                </Button>
              </CardFooter>
            </Card>
          </form>
        </TabsContent>

        {/* Security Tab Content */}
        <TabsContent value="security" className="mt-6 space-y-6">
          <Card className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
            <CardHeader>
              <CardTitle className="text-lg font-bold">Authentication & Credentials</CardTitle>
              <CardDescription className="text-slate-500 dark:text-slate-400">
                Manage your credentials, active logins, and security settings.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col sm:flex-row items-start sm:items-center gap-4 justify-between">
              <div>
                <h4 className="font-semibold text-sm">Account Password</h4>
                <p className="text-xs text-slate-500">Keep your account secure by rotating your password regularly.</p>
              </div>
              <div className="flex gap-2">
                <LoginHistoryModal />
                <ChangePasswordModal />
              </div>
            </CardContent>
          </Card>

          <ActiveSessions />

          <DataExport />

          <DeleteAccount />
        </TabsContent>

        {/* Notifications Tab Content */}
        <TabsContent value="notifications" className="mt-6">
          <form onSubmit={handleSaveNotifications}>
            <Card className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
              <CardHeader>
                <CardTitle className="text-lg font-bold">Alerting Channels</CardTitle>
                <CardDescription className="text-slate-500 dark:text-slate-400">
                  Configure alert routing channels and severity levels for notifications.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <h4 className="text-sm font-semibold border-b border-slate-100 dark:border-slate-800 pb-2">Active Channels</h4>
                  <div className="flex items-center justify-between">
                    <div>
                      <Label htmlFor="notif-email" className="font-semibold text-sm block">Email Alerts</Label>
                      <span className="text-xs text-slate-500">Dispatch anomaly alerts to {profile.email}</span>
                    </div>
                    <Switch id="notif-email" checked={notifyEmail} onCheckedChange={setNotifyEmail} />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <Label htmlFor="notif-slack" className="font-semibold text-sm block">Slack Webhook Alerts</Label>
                      <span className="text-xs text-slate-500">Relay alerts to global engineering Slack channels</span>
                    </div>
                    <Switch id="notif-slack" checked={notifySlack} onCheckedChange={setNotifySlack} />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <Label htmlFor="notif-telegram" className="font-semibold text-sm block">Telegram Bot Alerts</Label>
                      <span className="text-xs text-slate-500">Receive incident notifications on mobile devices</span>
                    </div>
                    <Switch id="notif-telegram" checked={notifyTelegram} onCheckedChange={setNotifyTelegram} />
                  </div>
                </div>

                <div className="space-y-4 pt-4">
                  <h4 className="text-sm font-semibold border-b border-slate-100 dark:border-slate-800 pb-2">Severity & Thresholds</h4>
                  <div className="space-y-2">
                    <Label htmlFor="notif-severity">Notify for Severity Level and Above</Label>
                    <Select value={notifySeverity} onValueChange={setNotifySeverity}>
                      <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 w-full max-w-xs">
                        <SelectValue placeholder="Select severity threshold" />
                      </SelectTrigger>
                      <SelectContent className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
                        <SelectItem value="LOW">LOW</SelectItem>
                        <SelectItem value="MEDIUM">MEDIUM</SelectItem>
                        <SelectItem value="HIGH">HIGH</SelectItem>
                        <SelectItem value="CRITICAL">CRITICAL</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-4 pt-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label htmlFor="notif-quiet-hours" className="font-semibold text-sm block">Quiet Hours</Label>
                      <span className="text-xs text-slate-500">Mute critical alerts during off-duty sleep blocks</span>
                    </div>
                    <Switch id="notif-quiet-hours" checked={quietHoursEnabled} onCheckedChange={setQuietHoursEnabled} />
                  </div>
                  {quietHoursEnabled && (
                    <div className="flex items-center gap-4 max-w-xs animate-in slide-in-from-top-1 duration-200">
                      <div className="space-y-1 w-full">
                        <Label htmlFor="quiet-start" className="text-xs text-slate-400">Start Time</Label>
                        <div className="relative">
                          <Input
                            id="quiet-start"
                            type="time"
                            value={quietHoursStart}
                            onChange={(e) => setQuietHoursStart(e.target.value)}
                            className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                          />
                          <Clock className="absolute right-3 top-3 h-4 w-4 text-slate-400 pointer-events-none" />
                        </div>
                      </div>
                      <div className="space-y-1 w-full">
                        <Label htmlFor="quiet-end" className="text-xs text-slate-400">End Time</Label>
                        <div className="relative">
                          <Input
                            id="quiet-end"
                            type="time"
                            value={quietHoursEnd}
                            onChange={(e) => setQuietHoursEnd(e.target.value)}
                            className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs"
                          />
                          <Clock className="absolute right-3 top-3 h-4 w-4 text-slate-400 pointer-events-none" />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
              <CardFooter className="border-t border-slate-100 dark:border-slate-800 pt-4 flex justify-end">
                <Button type="submit" disabled={updateProfileMutation.isPending} className="bg-primary hover:bg-primary/95 text-white flex items-center gap-1.5">
                  {updateProfileMutation.isPending ? (
                    <span>Saving...</span>
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      <span>Save Settings</span>
                    </>
                  )}
                </Button>
              </CardFooter>
            </Card>
          </form>
        </TabsContent>

        {/* Appearance Tab Content */}
        <TabsContent value="appearance" className="mt-6">
          <form onSubmit={handleSaveAppearance}>
            <Card className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
              <CardHeader>
                <CardTitle className="text-lg font-bold">Preferences</CardTitle>
                <CardDescription className="text-slate-500 dark:text-slate-400">
                  Configure visual display settings and localization values.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="timezone-select">System Timezone</Label>
                    <Select value={timezone} onValueChange={setTimezone}>
                      <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                        <SelectValue placeholder="Select timezone" />
                      </SelectTrigger>
                      <SelectContent className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
                        <SelectItem value="UTC">UTC (GMT+0)</SelectItem>
                        <SelectItem value="GMT">GMT (GMT+0)</SelectItem>
                        <SelectItem value="EST">EST (GMT-5)</SelectItem>
                        <SelectItem value="PST">PST (GMT-8)</SelectItem>
                        <SelectItem value="IST">IST (GMT+5:30)</SelectItem>
                        <SelectItem value="CET">CET (GMT+1)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="theme-select">Visual Theme</Label>
                    <Select value={theme} onValueChange={setTheme}>
                      <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                        <SelectValue placeholder="Select theme" />
                      </SelectTrigger>
                      <SelectContent className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
                        <SelectItem value="light">Light Mode</SelectItem>
                        <SelectItem value="dark">Dark Mode</SelectItem>
                        <SelectItem value="system">Follow System</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="format-select">Date Format</Label>
                    <Select value={dateFormat} onValueChange={setDateFormat}>
                      <SelectTrigger className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                        <SelectValue placeholder="Select date format" />
                      </SelectTrigger>
                      <SelectContent className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
                        <SelectItem value="ISO">ISO (YYYY-MM-DD)</SelectItem>
                        <SelectItem value="US">US (MM/DD/YYYY)</SelectItem>
                        <SelectItem value="EU">EU (DD/MM/YYYY)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
              <CardFooter className="border-t border-slate-100 dark:border-slate-800 pt-4 flex justify-end">
                <Button type="submit" disabled={updateProfileMutation.isPending} className="bg-primary hover:bg-primary/95 text-white flex items-center gap-1.5">
                  {updateProfileMutation.isPending ? (
                    <span>Saving...</span>
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      <span>Save Preferences</span>
                    </>
                  )}
                </Button>
              </CardFooter>
            </Card>
          </form>
        </TabsContent>
      </Tabs>
    </div>
  )
}

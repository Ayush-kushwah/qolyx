'use client'

import React, { useState } from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Trash2, AlertTriangle } from 'lucide-react'
import { useDeleteAccount } from '@/hooks/useProfile'

export default function DeleteAccount() {
  const [open, setOpen] = useState(false)
  const [confirmText, setConfirmText] = useState('')
  const deleteAccountMutation = useDeleteAccount()

  const handleDelete = () => {
    if (confirmText !== 'DELETE') return
    deleteAccountMutation.mutate(undefined, {
      onSuccess: () => {
        setOpen(false)
      }
    })
  }

  return (
    <Card className="border border-rose-500/20 bg-rose-500/5 dark:bg-rose-500/5 text-slate-900 dark:text-white">
      <CardHeader>
        <CardTitle className="text-lg font-bold text-rose-500 flex items-center gap-2">
          <Trash2 className="h-5 w-5" />
          <span>Terminate Account</span>
        </CardTitle>
        <CardDescription className="text-slate-500 dark:text-slate-400">
          Permanently delete your user profile account and all related login records.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md">
            This action is irreversible. All of your user profile configurations will be deleted from the database.
          </p>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button variant="destructive" className="flex items-center gap-2 whitespace-nowrap self-end sm:self-center">
                <Trash2 className="h-4 w-4" />
                <span>Delete Account</span>
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px] bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2 text-xl font-bold text-rose-500">
                  <AlertTriangle className="h-5 w-5" />
                  Are you absolutely sure?
                </DialogTitle>
                <DialogDescription className="text-slate-500 dark:text-slate-400">
                  This will permanently delete your account. To proceed, please type <strong className="text-rose-500 font-bold">DELETE</strong> in the box below.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="confirm-delete">Confirmation string</Label>
                  <Input
                    id="confirm-delete"
                    type="text"
                    required
                    placeholder="DELETE"
                    value={confirmText}
                    onChange={(e) => setConfirmText(e.target.value)}
                    className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  onClick={handleDelete}
                  disabled={confirmText !== 'DELETE' || deleteAccountMutation.isPending}
                  variant="destructive"
                  className="w-full"
                >
                  {deleteAccountMutation.isPending ? 'Terminating account...' : 'Confirm Account Termination'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </CardContent>
    </Card>
  )
}

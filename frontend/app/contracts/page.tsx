'use client'

import React, { useState } from 'react'
import { 
  useContracts, 
  useUpdateContract, 
  useDeleteContract, 
  useGenerateContract 
} from '@/hooks/useContracts'
import { Contract, ContractCreate } from '@/types'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorBoundary from '@/components/common/ErrorBoundary'
import EmptyState from '@/components/common/EmptyState'
import ContractForm from '@/components/contracts/ContractForm'

import { 
  FileSignature, 
  Plus, 
  Trash2, 
  Edit3, 
  AlertTriangle, 
  Code, 
  Loader2,
  FileCheck,
  Zap,
  Calendar
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog'

const TABLES = [
  { id: 'bronze_financial_candles', label: 'Financial Candles' },
  { id: 'bronze_fda_events', label: 'FDA Events' },
  { id: 'bronze_github_events', label: 'GitHub Events' }
]

export default function ContractsPage() {
  const { data: contracts = [], isLoading, isError, error, refetch } = useContracts()
  const updateMutation = useUpdateContract()
  const deleteMutation = useDeleteContract()
  const generateMutation = useGenerateContract()

  // Form Modal States
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [selectedContract, setSelectedContract] = useState<Contract | null>(null)
  const [formInitialValues, setFormInitialValues] = useState<Partial<ContractCreate> | null>(null)

  // Dialog States
  const [isGenDialogOpen, setIsGenDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [targetDeleteId, setTargetDeleteId] = useState<string | null>(null)
  const [isViewSchemaOpen, setIsViewSchemaOpen] = useState(false)
  const [viewingSchemaContract, setViewingSchemaContract] = useState<Contract | null>(null)

  // Table Generator Fields
  const [genTableName, setGenTableName] = useState('bronze_financial_candles')
  const [genContractName, setGenContractName] = useState('')

  // Open Form for creation
  const handleCreateNew = () => {
    setSelectedContract(null)
    setFormInitialValues(null)
    setIsFormOpen(true)
  }

  // Open Form for editing
  const handleEdit = (contract: Contract) => {
    setSelectedContract(contract)
    setFormInitialValues(null)
    setIsFormOpen(true)
  }

  // Toggle Contract is_active status directly from list card
  const handleToggleActive = (contract: Contract) => {
    updateMutation.mutate({
      id: contract.id,
      data: {
        is_active: !contract.is_active
      }
    })
  }

  // Generate draft schema from active table telemetry
  const handleGenerateProposal = (e: React.FormEvent) => {
    e.preventDefault()
    if (!genContractName.trim()) return

    generateMutation.mutate({
      tableName: genTableName,
      name: genContractName
    }, {
      onSuccess: (generatedDraft: any) => {
        setIsGenDialogOpen(false)
        setSelectedContract(null)
        setFormInitialValues({
          name: generatedDraft.name || genContractName,
          table_name: generatedDraft.table_name || genTableName,
          schema_definition: generatedDraft.schema_definition || {},
          is_active: true
        })
        
        // Timeout to open form smoothly after dialog closing animation finishes
        setTimeout(() => {
          setIsFormOpen(true)
        }, 150)
      }
    })
  }

  // Open delete confirm dialog
  const triggerDelete = (id: string) => {
    setTargetDeleteId(id)
    setIsDeleteDialogOpen(true)
  }

  // Execute deletion
  const executeDelete = () => {
    if (targetDeleteId) {
      deleteMutation.mutate(targetDeleteId, {
        onSuccess: () => {
          setIsDeleteDialogOpen(false)
          setTargetDeleteId(null)
        }
      })
    }
  }

  return (
    <ErrorBoundary>
      <div className="space-y-8 select-none">
        
        {/* Title / Action bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-400 bg-clip-text text-transparent flex items-center gap-2">
              <FileSignature className="h-7 w-7 text-primary" />
              Data Schema Contracts
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Enforce structural data contracts on telemetry streams. Violations trigger severity penalties.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={() => {
                setGenContractName('')
                setGenTableName('bronze_financial_candles')
                setIsGenDialogOpen(true)
              }}
              className="border-primary/20 bg-primary/10 hover:bg-primary/20 text-primary text-xs font-bold gap-1.5 h-9"
            >
              <Zap className="h-4 w-4" />
              Generate from Table
            </Button>
            <Button
              onClick={handleCreateNew}
              className="shadow-lg hover:shadow-primary/20 text-xs font-bold gap-1.5 h-9"
            >
              <Plus className="h-4 w-4" />
              Create Contract
            </Button>
          </div>
        </div>

        {/* Content list */}
        {isLoading ? (
          <div className="py-24">
            <LoadingSpinner text="Retrieving Active Schema Rules..." />
          </div>
        ) : isError ? (
          <EmptyState
            title="Error Loading Contracts"
            description={error instanceof Error ? error.message : 'Failed to retrieve schema definitions.'}
            icon={AlertTriangle}
            action={{
              label: 'Retry',
              onClick: () => refetch()
            }}
          />
        ) : contracts.length === 0 ? (
          <EmptyState
            title="No Data Contracts Configured"
            description="Contracts define the golden schema layout. Propose one automatically from pipeline structures to begin."
            icon={FileCheck}
            action={{
              label: 'Auto-Generate Draft',
              onClick: () => {
                setGenContractName('Telemetry Baseline Schema')
                setGenTableName('bronze_financial_candles')
                setIsGenDialogOpen(true)
              }
            }}
          />
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {contracts.map((contract) => {
              const columns = Object.entries(contract.schema_definition || {})
              const previewCols = columns.slice(0, 4)
              const remainingColsCount = Math.max(0, columns.length - 4)

              return (
                <div 
                  key={contract.id} 
                  className={`glass-panel p-5 rounded-xl border relative transition-all hover:scale-[1.01] hover:border-white/10 ${
                    contract.is_active ? 'border-white/5 bg-slate-900/10' : 'border-dashed border-white/5 opacity-60'
                  }`}
                >
                  {/* Top Bar */}
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <div className="space-y-1">
                      <h3 className="font-bold text-slate-200 text-sm leading-tight tracking-tight line-clamp-1">{contract.name}</h3>
                      <Badge variant="outline" className="bg-slate-950/40 text-[9px] font-mono text-slate-400 border-white/5 uppercase py-0.5">
                        {contract.table_name.replace(/bronze_/g, '').replace(/_/g, ' ')}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <Badge className="bg-slate-800 text-slate-300 font-bold text-[9px] hover:bg-slate-800">
                        v{contract.version}
                      </Badge>
                      <Switch
                        checked={contract.is_active}
                        onCheckedChange={() => handleToggleActive(contract)}
                        disabled={updateMutation.isPending}
                        className="scale-75"
                      />
                    </div>
                  </div>

                  {/* Created At details */}
                  <div className="text-[10px] text-slate-500 mb-3 flex items-center gap-1 font-semibold">
                    <Calendar className="h-3 w-3 text-slate-500" />
                    <span>Created:</span>
                    <span>{new Date(contract.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                  </div>

                  {/* Schema Preview */}
                  <div className="bg-slate-950/40 p-3 rounded-lg border border-white/5 mb-5 space-y-1.5 min-h-[110px]">
                    <div className="text-[9px] font-bold text-slate-500 uppercase tracking-widest flex items-center justify-between border-b border-white/5 pb-1 mb-1">
                      <span>Field Constraint</span>
                      <span>Type</span>
                    </div>

                    {previewCols.map(([name, spec]) => (
                      <div key={name} className="flex items-center justify-between font-mono text-[10px] text-slate-400">
                        <span className="truncate max-w-[140px] flex items-center gap-1">
                          {spec.is_required && <span className="h-1 w-1 rounded-full bg-rose-400 flex-shrink-0" />}
                          {name}
                          {spec.nullable && <span className="text-[8px] text-slate-600 font-sans italic">(null)</span>}
                        </span>
                        <span className="text-primary/70">{spec.data_type}</span>
                      </div>
                    ))}

                    {remainingColsCount > 0 && (
                      <div className="text-[9px] text-slate-500 font-semibold italic text-center pt-1 border-t border-white/5 mt-1 select-none">
                        + {remainingColsCount} additional columns defined
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-between border-t border-white/5 pt-3">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setViewingSchemaContract(contract)
                        setIsViewSchemaOpen(true)
                      }}
                      className="h-8 px-2 text-slate-400 hover:text-white border-white/5 hover:bg-white/5 text-xs font-bold gap-1"
                    >
                      <Code className="h-3.5 w-3.5" />
                      View Schema
                    </Button>
                    <div className="flex items-center gap-1.5">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleEdit(contract)}
                        className="h-8 px-3 text-slate-400 hover:text-white border-white/5 hover:bg-white/5 text-xs font-bold gap-1"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                        Configure
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => triggerDelete(contract.id)}
                        className="h-8 w-8 p-0 text-slate-500 hover:text-rose-400 border-white/5 hover:bg-rose-500/10"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* ==========================================
            CREATE/EDIT CONTRACT DIALOG (Zod validated)
            ========================================== */}
        <ContractForm
          open={isFormOpen}
          onOpenChange={setIsFormOpen}
          contract={selectedContract}
          initialValues={formInitialValues}
        />

        {/* ==========================================
            VIEW SCHEMA DEFINITION DIALOG
            ========================================== */}
        <Dialog open={isViewSchemaOpen} onOpenChange={setIsViewSchemaOpen}>
          <DialogContent className="bg-slate-900 border border-white/10 text-slate-200 select-none max-w-lg p-5 rounded-xl shadow-2xl backdrop-blur-xl">
            <DialogHeader className="space-y-1">
              <DialogTitle className="text-white text-base font-extrabold flex items-center gap-1.5">
                <Code className="h-5 w-5 text-primary" />
                Schema Definition: {viewingSchemaContract?.name}
              </DialogTitle>
              <DialogDescription className="text-slate-400 text-xs">
                Read-only JSON representation of the schema constraints.
              </DialogDescription>
            </DialogHeader>

            <div className="mt-3">
              <Textarea
                readOnly
                value={viewingSchemaContract ? JSON.stringify(viewingSchemaContract.schema_definition, null, 2) : ''}
                rows={14}
                className="font-mono text-xs bg-slate-950/70 border-white/10 text-emerald-400 focus-visible:ring-0 focus-visible:ring-offset-0 resize-none"
              />
            </div>

            <DialogFooter className="pt-2">
              <DialogClose asChild>
                <Button 
                  type="button" 
                  className="bg-primary hover:bg-primary/80 text-white font-semibold text-xs h-9"
                >
                  Close
                </Button>
              </DialogClose>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ==========================================
            AUTO GENERATOR DIALOG
            ========================================== */}
        <Dialog open={isGenDialogOpen} onOpenChange={setIsGenDialogOpen}>
          <DialogContent className="bg-slate-900 border border-white/10 text-slate-200 select-none max-w-sm p-5 rounded-xl shadow-2xl backdrop-blur-xl">
            <DialogHeader className="space-y-1">
              <DialogTitle className="text-white text-base font-extrabold flex items-center gap-1.5">
                <Zap className="h-5 w-5 text-primary" />
                Auto-Generate Contract
              </DialogTitle>
              <DialogDescription className="text-slate-400 text-xs">
                Inspects current metadata schemas to generate a custom proposal draft.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleGenerateProposal} className="space-y-4 pt-3">
              <div className="space-y-1.5">
                <Label htmlFor="g-table" className="text-xs font-bold text-slate-400">Target Table Data</Label>
                <Select value={genTableName} onValueChange={setGenTableName}>
                  <SelectTrigger id="g-table" className="bg-slate-950/40 border-white/5 text-slate-200 h-9 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-white/10 text-slate-200">
                    {TABLES.map(t => (
                      <SelectItem key={t.id} value={t.id} className="text-xs">
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="g-name" className="text-xs font-bold text-slate-400">Contract Draft Name</Label>
                <Input
                  id="g-name"
                  value={genContractName}
                  onChange={(e) => setGenContractName(e.target.value)}
                  placeholder="e.g. GitHub Event Contract Draft"
                  className="bg-slate-950/40 border-white/5 text-slate-200 h-9 text-xs"
                />
              </div>

              <DialogFooter className="pt-2 gap-2 sm:gap-0">
                <DialogClose asChild>
                  <Button 
                    type="button" 
                    variant="outline" 
                    className="border-white/5 text-slate-400 hover:text-white hover:bg-white/5 text-xs font-bold h-9"
                  >
                    Cancel
                  </Button>
                </DialogClose>
                <Button
                  type="submit"
                  disabled={generateMutation.isPending || !genContractName.trim()}
                  className="text-xs font-bold h-9 shadow-lg gap-1.5 min-w-[100px]"
                >
                  {generateMutation.isPending && (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  )}
                  Generate Draft
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* ==========================================
            DELETE CONTRACT CONFIRMATION DIALOG
            ========================================== */}
        <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
          <DialogContent className="bg-slate-900 border border-white/10 text-slate-200 select-none max-w-sm p-5 rounded-xl shadow-2xl backdrop-blur-xl">
            <DialogHeader className="space-y-2">
              <DialogTitle className="text-white text-base font-extrabold flex items-center gap-1.5">
                <AlertTriangle className="h-5 w-5 text-rose-500" />
                Delete Data Contract?
              </DialogTitle>
              <DialogDescription className="text-slate-400 text-xs leading-relaxed">
                This action is irreversible. All ongoing baseline validations and alerts for this schema contract will be terminated.
              </DialogDescription>
            </DialogHeader>

            <DialogFooter className="pt-4 gap-2 sm:gap-0">
              <DialogClose asChild>
                <Button 
                  variant="outline" 
                  className="border-white/5 text-slate-400 hover:text-white hover:bg-white/5 text-xs font-bold h-9"
                >
                  Keep Contract
                </Button>
              </DialogClose>
              <Button
                onClick={executeDelete}
                disabled={deleteMutation.isPending}
                className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold h-9 shadow-lg gap-1.5 min-w-[90px]"
              >
                {deleteMutation.isPending && (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                )}
                Confirm Delete
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

      </div>
    </ErrorBoundary>
  )
}

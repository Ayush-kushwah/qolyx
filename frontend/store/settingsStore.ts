import { create } from 'zustand'
import { PipelineFrequencySettings } from '@/types'
import { toast } from 'sonner'
import * as api from '@/lib/api'

interface SettingsState {
  pipelineSettings: Record<string, PipelineFrequencySettings>
  isLoading: boolean
  fetchSettings: () => Promise<void>
  setPipelineRunFrequency: (pipeline: string, minutes: number) => void
  setAlertFrequency: (pipeline: string, minutes: number) => void
  setAnomalyImmediateAlert: (pipeline: string, enabled: boolean) => void
  setSensitivity: (pipeline: string, sensitivity: 'LOW' | 'MEDIUM' | 'HIGH') => void
  setSeverityOverride: (pipeline: string, severity: string, minutes: number | undefined) => void
  validateFrequencies: () => Record<string, string>
  saveSettings: () => Promise<boolean>
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  pipelineSettings: {},
  isLoading: false,

  fetchSettings: async () => {
    set({ isLoading: true })
    try {
      const settings = await api.fetchPipelineSettings()
      set({ pipelineSettings: settings })
    } catch (err: any) {
      toast.error(err.message || 'Failed to load pipeline configurations.')
    } finally {
      set({ isLoading: false })
    }
  },
  
  setPipelineRunFrequency: (pipeline, minutes) => set((state) => ({
    pipelineSettings: {
      ...state.pipelineSettings,
      [pipeline]: {
        ...state.pipelineSettings[pipeline],
        run_frequency_minutes: minutes
      }
    }
  })),

  setAlertFrequency: (pipeline, minutes) => set((state) => ({
    pipelineSettings: {
      ...state.pipelineSettings,
      [pipeline]: {
        ...state.pipelineSettings[pipeline],
        alert_frequency_minutes: minutes
      }
    }
  })),

  setAnomalyImmediateAlert: (pipeline, enabled) => set((state) => ({
    pipelineSettings: {
      ...state.pipelineSettings,
      [pipeline]: {
        ...state.pipelineSettings[pipeline],
        anomaly_immediate_alert: enabled
      }
    }
  })),

  setSensitivity: (pipeline, sensitivity) => set((state) => ({
    pipelineSettings: {
      ...state.pipelineSettings,
      [pipeline]: {
        ...state.pipelineSettings[pipeline],
        sensitivity: sensitivity
      }
    }
  })),

  setSeverityOverride: (pipeline, severity, minutes) => set((state) => {
    const currentOverrides = state.pipelineSettings[pipeline]?.severity_overrides || {}
    const newOverrides = { ...currentOverrides }
    if (minutes === undefined) {
      delete newOverrides[severity]
    } else {
      newOverrides[severity] = minutes
    }
    return {
      pipelineSettings: {
        ...state.pipelineSettings,
        [pipeline]: {
          ...state.pipelineSettings[pipeline],
          severity_overrides: newOverrides
        }
      }
    }
  }),

  validateFrequencies: () => {
    const { pipelineSettings } = get()
    const errors: Record<string, string> = {}
    
    for (const [key, settings] of Object.entries(pipelineSettings)) {
      if (settings.run_frequency_minutes < 1) {
        errors[`${key}_run`] = 'Pipeline frequency must be at least 1 minute'
      }
      if (settings.alert_frequency_minutes < settings.run_frequency_minutes) {
        errors[`${key}_alert`] = 'Alert frequency cannot be less than pipeline run frequency'
      }
    }
    return errors
  },

  saveSettings: async () => {
    const errors = get().validateFrequencies()
    if (Object.keys(errors).length > 0) {
      toast.error('Validation failed. Please resolve frequency conflicts.')
      return false
    }
    
    set({ isLoading: true })
    try {
      const updated = await api.updatePipelineSettings(get().pipelineSettings)
      set({ pipelineSettings: updated })
      toast.success('Pipeline configurations successfully saved.')
      return true
    } catch (err: any) {
      toast.error(err.message || 'Failed to save pipeline settings.')
      return false
    } finally {
      set({ isLoading: false })
    }
  }
}))

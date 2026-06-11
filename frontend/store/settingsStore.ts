import { create } from 'zustand'
import { PipelineFrequencySettings } from '@/types'
import { toast } from 'sonner'

interface SettingsState {
  pipelineSettings: Record<'finnhub' | 'fda' | 'github', PipelineFrequencySettings>
  setPipelineRunFrequency: (pipeline: 'finnhub' | 'fda' | 'github', minutes: number) => void
  setAlertFrequency: (pipeline: 'finnhub' | 'fda' | 'github', minutes: number) => void
  setAnomalyImmediateAlert: (pipeline: 'finnhub' | 'fda' | 'github', enabled: boolean) => void
  setSeverityOverride: (pipeline: 'finnhub' | 'fda' | 'github', severity: string, minutes: number | undefined) => void
  validateFrequencies: () => Record<string, string>
  saveSettings: () => Promise<boolean>
}

const defaultPipelineSettings = (pipeline: 'finnhub' | 'fda' | 'github'): PipelineFrequencySettings => ({
  pipeline_name: pipeline,
  run_frequency_minutes: 15,
  alert_frequency_minutes: 30,
  anomaly_immediate_alert: true,
  severity_overrides: {
    CRITICAL: 1,
    HIGH: 5,
    MEDIUM: 15,
    LOW: 60
  }
})

export const useSettingsStore = create<SettingsState>((set, get) => ({
  pipelineSettings: {
    finnhub: defaultPipelineSettings('finnhub'),
    fda: defaultPipelineSettings('fda'),
    github: defaultPipelineSettings('github')
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

  setSeverityOverride: (pipeline, severity, minutes) => set((state) => {
    const currentOverrides = state.pipelineSettings[pipeline].severity_overrides || {}
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
    
    // Simulate API call to save settings
    await new Promise((resolve) => setTimeout(resolve, 1000))
    toast.success('Settings saved locally (backend integration coming in Phase 8.5)')
    return true
  }
}))

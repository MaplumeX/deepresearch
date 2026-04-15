import { create } from 'zustand'

export type OutputLanguage = 'zh-CN' | 'en'

export interface ResearchSettings {
  outputLanguage: OutputLanguage
  maxIterations: number
  maxParallelTasks: number
}

interface SettingsState extends ResearchSettings {
  updateSettings: (patch: Partial<ResearchSettings>) => void
}

const STORAGE_KEY = 'research-settings'

const defaults: ResearchSettings = {
  outputLanguage: 'zh-CN',
  maxIterations: 2,
  maxParallelTasks: 3,
}

function getInitialSettings(): ResearchSettings {
  if (typeof window === 'undefined') {
    return defaults
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? (JSON.parse(raw) as Partial<ResearchSettings>) : {}
    return {
      outputLanguage: parsed.outputLanguage ?? defaults.outputLanguage,
      maxIterations: clampInt(parsed.maxIterations, defaults.maxIterations, 1, 5),
      maxParallelTasks: clampInt(parsed.maxParallelTasks, defaults.maxParallelTasks, 1, 5),
    }
  } catch {
    return defaults
  }
}

function clampInt(value: unknown, fallback: number, min: number, max: number): number {
  const num = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(num)) return fallback
  return Math.max(min, Math.min(max, num))
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  ...getInitialSettings(),

  updateSettings: (patch) => {
    const next: ResearchSettings = {
      outputLanguage: patch.outputLanguage ?? get().outputLanguage,
      maxIterations: clampInt(patch.maxIterations ?? get().maxIterations, get().maxIterations, 1, 5),
      maxParallelTasks: clampInt(patch.maxParallelTasks ?? get().maxParallelTasks, get().maxParallelTasks, 1, 5),
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    set(next)
  },
}))

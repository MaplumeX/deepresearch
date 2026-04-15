import { create } from 'zustand'

type Theme = 'light' | 'dark'

interface UiState {
  theme: Theme
  sidebarCollapsed: boolean
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
}

const STORAGE_KEY_THEME = 'theme'
const STORAGE_KEY_SIDEBAR = 'sidebar-collapsed'

function getInitialTheme(): Theme {
  if (typeof window === 'undefined') {
    return 'light'
  }
  const stored = window.localStorage.getItem(STORAGE_KEY_THEME)
  if (stored === 'light' || stored === 'dark') {
    return stored
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function getInitialSidebarCollapsed(): boolean {
  if (typeof window === 'undefined') {
    return false
  }
  const stored = window.localStorage.getItem(STORAGE_KEY_SIDEBAR)
  return stored === 'true'
}

function applyTheme(theme: Theme) {
  const root = document.documentElement
  if (theme === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

export const useUiStore = create<UiState>((set, get) => ({
  theme: getInitialTheme(),
  sidebarCollapsed: getInitialSidebarCollapsed(),

  setTheme: (theme) => {
    window.localStorage.setItem(STORAGE_KEY_THEME, theme)
    applyTheme(theme)
    set({ theme })
  },

  toggleTheme: () => {
    const next = get().theme === 'light' ? 'dark' : 'light'
    get().setTheme(next)
  },

  toggleSidebar: () => {
    const next = !get().sidebarCollapsed
    window.localStorage.setItem(STORAGE_KEY_SIDEBAR, String(next))
    set({ sidebarCollapsed: next })
  },

  setSidebarCollapsed: (collapsed) => {
    window.localStorage.setItem(STORAGE_KEY_SIDEBAR, String(collapsed))
    set({ sidebarCollapsed: collapsed })
  },
}))

export function initUiStore() {
  applyTheme(getInitialTheme())
}

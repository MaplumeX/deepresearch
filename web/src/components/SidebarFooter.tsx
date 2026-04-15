import { useState } from 'react'
import { Moon, Settings, Sun } from 'lucide-react'
import { Button } from './ui/button'
import { ResearchSettingsDialog } from './ResearchSettingsDialog'
import { useSettingsStore } from '@/store/useSettingsStore'

type Theme = 'light' | 'dark'

interface SidebarFooterProps {
  theme: Theme
  onToggleTheme: () => void
}

export function SidebarFooter({ theme, onToggleTheme }: SidebarFooterProps) {
  const [settingsOpen, setSettingsOpen] = useState(false)
  const settings = useSettingsStore()

  return (
    <div className="p-3 border-t border-border flex flex-col gap-2">
      <ResearchSettingsDialog
        open={settingsOpen}
        title="默认研究设置"
        confirmLabel="保存"
        initialValues={settings}
        onClose={() => setSettingsOpen(false)}
        onConfirm={(next) => {
          settings.updateSettings(next)
          setSettingsOpen(false)
        }}
      />
      <Button
        variant="ghost"
        onClick={() => setSettingsOpen(true)}
        className="w-full justify-start gap-2 h-10 px-2 font-normal hover:bg-black/5 dark:hover:bg-white/5"
      >
        <Settings className="h-4 w-4 opacity-70" />
        <span className="text-sm">设置</span>
      </Button>
      <Button
        variant="ghost"
        onClick={onToggleTheme}
        className="w-full justify-start gap-2 h-10 px-2 font-normal hover:bg-black/5 dark:hover:bg-white/5"
      >
        {theme === 'dark' ? (
          <>
            <Sun className="h-4 w-4 opacity-70" />
            <span className="text-sm">Light mode</span>
          </>
        ) : (
          <>
            <Moon className="h-4 w-4 opacity-70" />
            <span className="text-sm">Dark mode</span>
          </>
        )}
      </Button>
      <div className="flex items-center gap-3 cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 px-2 py-2 rounded-xl transition-colors">
        <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-cyan-500 to-indigo-500 flex items-center justify-center text-white font-semibold text-sm shadow-inner ring-2 ring-background border border-border/50">
          U
        </div>
        <div className="flex-1 truncate text-sm font-medium">
          Deep Research
        </div>
      </div>
    </div>
  )
}

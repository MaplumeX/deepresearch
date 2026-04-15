import { MessageSquarePlus, Moon, PanelLeft, Sun } from 'lucide-react'
import { Button } from './ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip'

type Theme = 'light' | 'dark'

interface SidebarRailProps {
  onToggleSidebar: () => void
  onNewChat: () => void
  theme: Theme
  onToggleTheme: () => void
}

export function SidebarRail({ onToggleSidebar, onNewChat, theme, onToggleTheme }: SidebarRailProps) {
  return (
    <TooltipProvider delayDuration={100}>
      <div className="flex flex-col h-full py-3 px-2">
        <div className="flex flex-col items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={onToggleSidebar}
                className="h-10 w-10 hover:bg-black/5 dark:hover:bg-white/5"
                aria-label="Expand sidebar"
              >
                <PanelLeft className="h-5 w-5 opacity-70" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">Expand sidebar</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={onNewChat}
                className="h-10 w-10 hover:bg-black/5 dark:hover:bg-white/5"
                aria-label="New chat"
              >
                <MessageSquarePlus className="h-5 w-5 opacity-70" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">New chat</TooltipContent>
          </Tooltip>
        </div>

        <div className="flex-1" />

        <div className="flex flex-col items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={onToggleTheme}
                className="h-10 w-10 hover:bg-black/5 dark:hover:bg-white/5"
                aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {theme === 'dark' ? (
                  <Sun className="h-5 w-5 opacity-70" />
                ) : (
                  <Moon className="h-5 w-5 opacity-70" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              {theme === 'dark' ? 'Light mode' : 'Dark mode'}
            </TooltipContent>
          </Tooltip>

          <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-cyan-500 to-indigo-500 flex items-center justify-center text-white font-semibold text-sm shadow-inner ring-2 ring-background border border-border/50">
            U
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}

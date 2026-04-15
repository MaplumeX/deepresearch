import { PanelLeftClose, Plus } from 'lucide-react'
import { Button } from './ui/button'

interface SidebarHeaderProps {
  onToggleSidebar: () => void
  onNewChat: () => void
}

export function SidebarHeader({ onToggleSidebar, onNewChat }: SidebarHeaderProps) {
  return (
    <div className="p-3 flex items-center justify-between gap-2">
      <Button
        variant="ghost"
        size="icon"
        onClick={onToggleSidebar}
        className="h-10 w-10 shrink-0 hover:bg-black/5 dark:hover:bg-white/5"
        aria-label="Collapse sidebar"
      >
        <PanelLeftClose className="h-5 w-5 opacity-70" />
      </Button>
      <Button
        onClick={onNewChat}
        className="flex-1 justify-start gap-2 h-10 select-none bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm transition-all duration-200 active:scale-[0.98]"
      >
        <Plus className="h-4 w-4" />
        New chat
      </Button>
    </div>
  )
}

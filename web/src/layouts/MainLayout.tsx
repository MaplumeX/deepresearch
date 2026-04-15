import React from 'react'
import { PanelLeft } from 'lucide-react'
import { Sidebar } from '@/components/Sidebar'
import { Button } from '@/components/ui/button'
import { useUiStore } from '@/store/useUiStore'

export function MainLayout({ children }: { children: React.ReactNode }) {
  const { sidebarCollapsed, toggleSidebar } = useUiStore()

  return (
    <div className="flex h-screen overflow-hidden bg-background font-sans">
      <Sidebar />
      <main className="flex-1 flex flex-col h-full relative transition-all duration-300">
        {sidebarCollapsed && (
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="absolute top-3 left-3 z-10 h-10 w-10 shrink-0 hover:bg-black/5 dark:hover:bg-white/5"
          >
            <PanelLeft className="h-5 w-5 opacity-70" />
          </Button>
        )}
        {children}
      </main>
    </div>
  )
}

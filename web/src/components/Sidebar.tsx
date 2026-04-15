import { useEffect } from 'react'
import { SidebarHeader } from './SidebarHeader'
import { SidebarRail } from './SidebarRail'
import { SidebarFooter } from './SidebarFooter'
import { ConversationList } from './ConversationList'
import { useChatStore } from '@/store/useChatStore'
import { useUiStore } from '@/store/useUiStore'
import { cn } from '@/lib/utils'

export function Sidebar() {
  const {
    conversations,
    loadConversations,
    activeConversationId,
    loadConversation,
    startNewChat,
    pinConversation,
    deleteConversation,
  } = useChatStore()
  const { sidebarCollapsed, toggleSidebar, theme, toggleTheme } = useUiStore()

  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  return (
    <aside
      className={cn(
        'h-screen flex-shrink-0 bg-muted/30 border-r border-border flex flex-col transition-all duration-300 ease-in-out overflow-hidden',
        sidebarCollapsed ? 'w-16' : 'w-[260px]',
      )}
    >
      {sidebarCollapsed ? (
        <SidebarRail
          onToggleSidebar={toggleSidebar}
          onNewChat={startNewChat}
          theme={theme}
          onToggleTheme={toggleTheme}
        />
      ) : (
        <>
          <SidebarHeader onToggleSidebar={toggleSidebar} onNewChat={startNewChat} />
          <ConversationList
            conversations={conversations}
            activeConversationId={activeConversationId}
            onSelect={loadConversation}
            onPin={pinConversation}
            onDelete={deleteConversation}
          />
          <SidebarFooter theme={theme} onToggleTheme={toggleTheme} />
        </>
      )}
    </aside>
  )
}

import { useEffect, useRef, useState } from 'react'
import { MessageSquare, MoreVertical, PanelLeftClose, Pin, Plus, Sun, Moon, Trash2 } from 'lucide-react'
import { Button } from './ui/button'
import { ScrollArea } from './ui/scroll-area'
import { useChatStore } from '@/store/useChatStore'
import { useUiStore } from '@/store/useUiStore'

export function Sidebar() {
  const { conversations, loadConversations, activeConversationId, loadConversation, startNewChat, pinConversation, deleteConversation } = useChatStore()
  const { sidebarCollapsed, toggleSidebar, theme, toggleTheme } = useUiStore()
  const [openMenuId, setOpenMenuId] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpenMenuId(null)
      }
    }
    if (openMenuId) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [openMenuId])

  if (sidebarCollapsed) {
    return null
  }

  return (
    <aside className="w-[260px] flex-shrink-0 bg-muted/30 border-r border-border flex flex-col transition-all duration-300">
      <div className="p-3 flex items-center justify-between">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="h-10 w-10 shrink-0 hover:bg-black/5 dark:hover:bg-white/5"
        >
          <PanelLeftClose className="h-5 w-5 opacity-70" />
        </Button>
      </div>

      <div className="px-3 pb-3">
        <Button
          onClick={startNewChat}
          className="w-full justify-start gap-2 h-10 select-none bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm transition-all duration-200 active:scale-[0.98]"
        >
          <Plus className="h-4 w-4" />
          New chat
        </Button>
      </div>

      <ScrollArea className="flex-1 px-3">
        <div className="flex flex-col gap-1 pb-4">
          <p className="text-xs font-semibold text-muted-foreground px-2 py-2 mt-2">Recent</p>
          {conversations.map(conv => (
            <div key={conv.conversation_id} className="relative group">
              <Button
                onClick={() => loadConversation(conv.conversation_id)}
                variant={activeConversationId === conv.conversation_id ? "secondary" : "ghost"}
                className="justify-start gap-2 font-normal h-auto min-h-10 px-2 py-2 w-full text-left transition-colors"
              >
                <MessageSquare className="h-4 w-4 shrink-0 opacity-70" />
                <span className="min-w-0 flex-1 truncate">{conv.title || 'Untitled Session'}</span>
                {conv.mode === 'research' && (
                  <span className="shrink-0 rounded-full border border-border/70 bg-background px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                    Research
                  </span>
                )}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation()
                  setOpenMenuId(openMenuId === conv.conversation_id ? null : conv.conversation_id)
                }}
                className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
                aria-label="More options"
              >
                <MoreVertical className="h-4 w-4 opacity-70" />
              </Button>
              {openMenuId === conv.conversation_id && (
                <div
                  ref={menuRef}
                  className="absolute right-2 top-8 z-50 w-32 rounded-md border border-border bg-popover shadow-md p-1"
                >
                  <button
                    onClick={() => {
                      pinConversation(conv.conversation_id)
                      setOpenMenuId(null)
                    }}
                    className="w-full flex items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
                  >
                    <Pin className="h-4 w-4" />
                    置顶
                  </button>
                  <button
                    onClick={() => {
                      deleteConversation(conv.conversation_id)
                      setOpenMenuId(null)
                    }}
                    className="w-full flex items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-destructive hover:bg-destructive/10 transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                    删除
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>

      <div className="p-3 border-t border-border flex flex-col gap-2">
        <Button
          variant="ghost"
          onClick={toggleTheme}
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
    </aside>
  )
}

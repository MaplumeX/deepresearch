import { useEffect } from 'react'
import { MessageSquare, Plus, PanelLeftClose } from 'lucide-react'
import { Button } from './ui/button'
import { ScrollArea } from './ui/scroll-area'
import { useChatStore } from '@/store/useChatStore'

export function Sidebar() {
  const { conversations, loadConversations, activeConversationId, loadConversation, startNewChat } = useChatStore()
  
  useEffect(() => {
    loadConversations()
  }, [loadConversations])
  
  return (
    <aside className="w-[260px] flex-shrink-0 bg-muted/30 border-r border-border flex flex-col transition-all duration-300">
      <div className="p-3 flex items-center justify-between">
        <Button variant="ghost" size="icon" className="h-10 w-10 shrink-0 hover:bg-black/5 dark:hover:bg-white/5">
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
            <Button 
               key={conv.conversation_id}
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
          ))}
        </div>
      </ScrollArea>

      <div className="p-3 border-t border-border flex items-center gap-3 cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 mx-2 my-2 rounded-xl transition-colors">
        <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-cyan-500 to-indigo-500 flex items-center justify-center text-white font-semibold text-sm shadow-inner ring-2 ring-background border border-border/50">
          U
        </div>
        <div className="flex-1 truncate text-sm font-medium">
          Deep Research
        </div>
      </div>
    </aside>
  )
}

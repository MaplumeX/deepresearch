import { useEffect, useRef } from 'react'
import { ScrollArea } from './ui/scroll-area'
import { Bot } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useChatStore } from '@/store/useChatStore'

export function ChatArea() {
  const { activeConversationParams, streamingAssistantPreview, isGenerating } = useChatStore()
  
  const scrollRef = useRef<HTMLDivElement>(null)
  
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [activeConversationParams?.messages, streamingAssistantPreview])

  const messages = activeConversationParams?.messages || []

  return (
    <ScrollArea className="flex-1 px-4 md:px-0 scroll-smooth">
      <div className="max-w-3xl mx-auto flex flex-col gap-8 pb-48 pt-8">
        
        {messages.length === 0 && !isGenerating && (
          <div className="flex-1 flex flex-col items-center justify-center h-48 opacity-50 mt-20">
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-6">
               <Bot className="h-8 w-8 text-foreground" />
            </div>
            <h2 className="text-xl font-medium">How can I help you today?</h2>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.message_id} className={cn("flex gap-4 w-full group", msg.role === 'user' ? "justify-end" : "justify-start")}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 mt-0.5 shrink-0 rounded-full border border-border/50 bg-primary/10 flex items-center justify-center shadow-sm">
                <Bot className="h-5 w-5 text-foreground opacity-80" />
              </div>
            )}
            
            <div className={cn(
              "flex flex-col gap-2 max-w-[85%] text-[15px] px-5 py-3.5 shadow-sm transition-all relative overflow-hidden",
              msg.role === 'user' 
                ? "bg-muted rounded-2xl rounded-tr-sm text-foreground hover:bg-muted/80 break-words whitespace-pre-wrap" 
                : "bg-transparent rounded-2xl leading-relaxed text-foreground"
            )}>
              {/* Skip rendering the placeholder empty bubble if there's streaming override attached right after */}
              {msg.role === 'assistant' && !msg.content ? null : (
                <span className={cn("leading-relaxed", msg.role !== 'user' && "whitespace-pre-wrap")}>
                  {msg.content}
                </span>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 mt-0.5 shrink-0 rounded-full bg-gradient-to-tr from-cyan-500 to-indigo-500 flex items-center justify-center text-white font-medium text-sm shadow-sm ring-2 ring-background border border-border/50">
                U
              </div>
            )}
          </div>
        ))}

        {isGenerating && !streamingAssistantPreview && (
          <div className="flex gap-4 w-full group justify-start animate-in fade-in slide-in-from-bottom-2 duration-500">
            <div className="w-8 h-8 mt-0.5 shrink-0 rounded-full border border-border/50 bg-primary/10 flex items-center justify-center shadow-sm">
              <Bot className="h-5 w-5 text-foreground opacity-80" />
            </div>
            <div className="flex flex-col justify-center items-center h-10 px-5 bg-transparent">
              <span className="flex space-x-1.5">
                <div className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce"></div>
              </span>
            </div>
          </div>
        )}
        
        {isGenerating && streamingAssistantPreview && (
          <div className="flex gap-4 w-full group justify-start animate-in fade-in duration-300">
            <div className="w-8 h-8 mt-0.5 shrink-0 rounded-full border border-border/50 bg-primary/10 flex items-center justify-center shadow-sm">
              <Bot className="h-5 w-5 text-foreground opacity-80" />
            </div>
            
            <div className="flex flex-col gap-2 max-w-[85%] text-[15px] px-5 py-3.5 shadow-[0_0_20px_rgba(0,0,0,0.02)] transition-all relative overflow-hidden bg-transparent rounded-2xl leading-relaxed text-foreground">
              <span className="whitespace-pre-wrap leading-relaxed">
                 {streamingAssistantPreview}
                 <span className="inline-block w-2 h-[1em] ml-1 bg-foreground animate-pulse align-middle opacity-50 relative -top-[2px]"></span>
              </span>
            </div>
          </div>
        )}

        <div ref={scrollRef} className="h-1 shrink-0" />
      </div>
    </ScrollArea>
  )
}

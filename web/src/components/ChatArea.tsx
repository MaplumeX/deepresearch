import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ScrollArea } from './ui/scroll-area'
import { Bot, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useChatStore } from '@/store/useChatStore'

function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => <h1 className="text-xl font-semibold mt-4 mb-2">{children}</h1>,
        h2: ({ children }) => <h2 className="text-lg font-semibold mt-4 mb-2">{children}</h2>,
        h3: ({ children }) => <h3 className="text-base font-semibold mt-3 mb-1">{children}</h3>,
        p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        code: ({ children, className }) => {
          const isInline = !className
          return isInline ? (
            <code className="px-1.5 py-0.5 rounded bg-muted text-sm font-mono text-foreground">
              {children}
            </code>
          ) : (
            <pre className="p-3 rounded-lg bg-muted overflow-x-auto my-2">
              <code className={cn("text-sm font-mono block", className)}>{children}</code>
            </pre>
          )
        },
        pre: ({ children }) => <>{children}</>,
        a: ({ children, href }) => (
          <a href={href} target="_blank" rel="noreferrer" className="text-primary underline underline-offset-2 hover:text-primary/80">
            {children}
          </a>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-muted-foreground/30 pl-3 italic text-muted-foreground my-2">
            {children}
          </blockquote>
        ),
        table: ({ children }) => (
          <div className="overflow-x-auto my-2">
            <table className="w-full text-sm border-collapse border border-border">
              {children}
            </table>
          </div>
        ),
        thead: ({ children }) => <thead className="bg-muted">{children}</thead>,
        th: ({ children }) => (
          <th className="border border-border px-2 py-1 text-left font-medium">{children}</th>
        ),
        td: ({ children }) => (
          <td className="border border-border px-2 py-1">{children}</td>
        ),
        hr: () => <hr className="my-3 border-border" />,
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

export function ChatArea() {
  const {
    activeConversation,
    draftMode,
    streamingAssistantPreview,
    isGenerating,
    error,
    clearError,
  } = useChatStore()

  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [activeConversation?.messages, streamingAssistantPreview])

  const allMessages = activeConversation?.messages || []
  const lastMessage = allMessages[allMessages.length - 1]
  const shouldHideLastPlaceholder = isGenerating
    && lastMessage
    && lastMessage.role === 'assistant'
    && !lastMessage.content.trim()
  const messages = shouldHideLastPlaceholder ? allMessages.slice(0, -1) : allMessages
  const currentMode = activeConversation?.mode ?? draftMode
  const emptyTitle = currentMode === 'research' ? 'Deep research is ready' : 'How can I help you today?'
  const emptyDescription = currentMode === 'research'
    ? 'Send a question to create a research session with planning, retrieval, and synthesis.'
    : 'Start a normal conversation. Deep Research stays off until you explicitly enable it.'

  return (
    <ScrollArea className="flex-1 px-4 md:px-0 scroll-smooth">
      <div className="max-w-3xl mx-auto flex flex-col gap-8 pb-48 pt-8">

        {messages.length === 0 && !isGenerating && (
          <div className="flex-1 flex flex-col items-center justify-center h-48 opacity-50 mt-20">
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-6">
               <Bot className="h-8 w-8 text-foreground" />
            </div>
            <h2 className="text-xl font-medium">{emptyTitle}</h2>
            <p className="mt-3 max-w-md text-center text-sm leading-6 text-muted-foreground">
              {emptyDescription}
            </p>
          </div>
        )}

        {error && (
          <div className="flex justify-center">
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-destructive/10 text-destructive text-sm">
              <span>{error}</span>
              <button onClick={clearError} className="hover:opacity-70">
                <X className="h-4 w-4" />
              </button>
            </div>
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
              {msg.role === 'assistant' && !msg.content ? null : (
                msg.role === 'user' ? (
                  <span className="leading-relaxed">{msg.content}</span>
                ) : (
                  <div className="leading-relaxed">
                    <MarkdownContent content={msg.content} />
                  </div>
                )
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
              <div className="leading-relaxed">
                <MarkdownContent content={streamingAssistantPreview} />
                <span className="inline-block w-2 h-[1em] ml-1 bg-foreground animate-pulse align-middle opacity-50 relative -top-[2px]"></span>
              </div>
            </div>
          </div>
        )}

        <div ref={scrollRef} className="h-1 shrink-0" />
      </div>
    </ScrollArea>
  )
}

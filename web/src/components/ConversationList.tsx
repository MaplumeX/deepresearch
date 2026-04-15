import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { ScrollArea } from './ui/scroll-area'
import { Input } from './ui/input'
import { Separator } from './ui/separator'
import { ConversationItem } from './ConversationItem'
import type { ConversationSummary } from '@/types/research'

interface ConversationListProps {
  conversations: ConversationSummary[]
  activeConversationId: string | null
  onSelect: (id: string) => void
  onPin: (id: string) => void
  onDelete: (id: string) => void
}

export function ConversationList({
  conversations,
  activeConversationId,
  onSelect,
  onPin,
  onDelete,
}: ConversationListProps) {
  const [searchQuery, setSearchQuery] = useState('')

  const filteredConversations = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    if (!query) return conversations
    return conversations.filter((conv) =>
      (conv.title || 'Untitled Session').toLowerCase().includes(query),
    )
  }, [conversations, searchQuery])

  const pinned = useMemo(
    () => filteredConversations.filter((conv) => !!conv.is_pinned),
    [filteredConversations],
  )

  const recent = useMemo(
    () => filteredConversations.filter((conv) => !conv.is_pinned),
    [filteredConversations],
  )

  const hasConversations = conversations.length > 0
  const hasResults = filteredConversations.length > 0

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="px-3 pb-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search chats..."
            className="pl-9 h-9 bg-muted/50 border-transparent focus-visible:bg-background focus-visible:border-input"
          />
        </div>
      </div>

      <ScrollArea className="min-w-0 flex-1 px-3">
        {!hasConversations && (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-3">
              <span className="text-xl text-muted-foreground">💬</span>
            </div>
            <p className="text-sm text-muted-foreground">No conversations yet</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              Start a new chat to begin
            </p>
          </div>
        )}

        {hasConversations && !hasResults && (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <p className="text-sm text-muted-foreground">No matching chats</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              Try a different search term
            </p>
          </div>
        )}

        {hasResults && (
          <div className="flex min-w-0 flex-col gap-1 pb-4">
            {pinned.length > 0 && (
              <>
                <p className="text-xs font-semibold text-muted-foreground px-2 py-2 mt-1">
                  Pinned
                </p>
                {pinned.map((conv) => (
                  <ConversationItem
                    key={conv.conversation_id}
                    conversation={conv}
                    isActive={activeConversationId === conv.conversation_id}
                    onClick={() => onSelect(conv.conversation_id)}
                    onPin={() => onPin(conv.conversation_id)}
                    onDelete={() => onDelete(conv.conversation_id)}
                  />
                ))}
              </>
            )}

            {pinned.length > 0 && recent.length > 0 && (
              <Separator className="my-2 bg-border/50" />
            )}

            {recent.length > 0 && (
              <>
                <p className="text-xs font-semibold text-muted-foreground px-2 py-2 mt-1">
                  Recent
                </p>
                {recent.map((conv) => (
                  <ConversationItem
                    key={conv.conversation_id}
                    conversation={conv}
                    isActive={activeConversationId === conv.conversation_id}
                    onClick={() => onSelect(conv.conversation_id)}
                    onPin={() => onPin(conv.conversation_id)}
                    onDelete={() => onDelete(conv.conversation_id)}
                  />
                ))}
              </>
            )}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}

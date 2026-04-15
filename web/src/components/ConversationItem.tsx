import { Loader2, MessageSquare, MoreVertical, Pin, PinOff, Trash2 } from 'lucide-react'
import { Button } from './ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu'
import type { ConversationSummary } from '@/types/research'

interface ConversationItemProps {
  conversation: ConversationSummary
  isActive: boolean
  onClick: () => void
  onPin: () => void
  onDelete: () => void
}

export function ConversationItem({
  conversation,
  isActive,
  onClick,
  onPin,
  onDelete,
}: ConversationItemProps) {
  const isResearch = conversation.mode === 'research'
  const isRunning = conversation.latest_run_status === 'running' || conversation.latest_run_status === 'queued'
  const isPinned = !!conversation.is_pinned

  return (
    <div className="relative group">
      <Button
        onClick={onClick}
        variant={isActive ? 'secondary' : 'ghost'}
        className="justify-start gap-2 font-normal h-auto min-h-10 px-2 py-2 w-full text-left transition-colors relative overflow-hidden"
      >
        {isResearch && (
          <span className="absolute left-0 top-0 bottom-0 w-[3px] bg-indigo-500" />
        )}
        <MessageSquare className="h-4 w-4 shrink-0 opacity-70" />
        <span className="min-w-0 flex-1 truncate">{conversation.title || 'Untitled Session'}</span>
        {isResearch && (
          <span className="shrink-0 rounded-full border border-border/70 bg-background px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            Research
          </span>
        )}
        {isRunning && (
          <Loader2 className="h-4 w-4 shrink-0 animate-spin text-muted-foreground" />
        )}
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
            aria-label="More options"
            onClick={(e) => e.stopPropagation()}
          >
            <MoreVertical className="h-4 w-4 opacity-70" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-40">
          <DropdownMenuItem onClick={onPin} className="gap-2">
            {isPinned ? (
              <>
                <PinOff className="h-4 w-4" />
                取消置顶
              </>
            ) : (
              <>
                <Pin className="h-4 w-4" />
                置顶
              </>
            )}
          </DropdownMenuItem>
          <DropdownMenuItem onClick={onDelete} variant="destructive" className="gap-2">
            <Trash2 className="h-4 w-4" />
            删除
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}

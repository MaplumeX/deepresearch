import { Loader2, MessageSquare, MoreVertical, Pin, PinOff, Trash2 } from 'lucide-react'
import { Button, buttonVariants } from './ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu'
import { cn } from '@/lib/utils'
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
    <div className="relative group min-w-0 max-w-full">
      <div
        onClick={onClick}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            onClick()
          }
        }}
        role="button"
        tabIndex={0}
        className={cn(
          buttonVariants({ variant: isActive ? 'secondary' : 'ghost' }),
          'relative flex h-auto min-h-10 w-full min-w-0 max-w-full cursor-pointer justify-start gap-2 overflow-hidden px-2 py-2 text-left font-normal transition-colors'
        )}
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

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 opacity-0 group-hover:opacity-100 focus:opacity-100 data-[state=open]:opacity-100 transition-opacity ml-1 shrink-0"
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
    </div>
  )
}

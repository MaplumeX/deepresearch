import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import type { SourceCard } from '@/types/research'

export function CiteBadge({
  sourceId,
  displayText,
  source,
}: {
  sourceId: string
  displayText: string
  source?: SourceCard
}) {
  return (
    <TooltipProvider delayDuration={100}>
      <Tooltip>
        <TooltipTrigger asChild>
          <sup className="cursor-pointer rounded bg-primary/10 px-1 py-0 text-[11px] font-medium text-primary hover:bg-primary/20">
            {displayText}
          </sup>
        </TooltipTrigger>
        <TooltipContent
          side="top"
          className="max-w-xs bg-popover text-popover-foreground"
        >
          <div className="space-y-1.5">
            <p className="font-medium leading-snug">{source?.title ?? sourceId}</p>
            {source?.url && (
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="block truncate text-xs text-primary underline"
              >
                {source.url}
              </a>
            )}
            {source?.snippet && (
              <p className="text-xs text-muted-foreground line-clamp-3">
                {source.snippet}
              </p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

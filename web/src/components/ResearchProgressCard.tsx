import { useState } from 'react'
import { Activity, ChevronDown, ChevronUp, Clock3, ListChecks } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  buildProgressViewModel,
  formatEventTime,
} from '@/lib/research-progress'
import type {
  ResearchProgressPayload,
  ResearchRunHistoryEvent,
  RunDetail,
} from '@/types/research'

function toneClasses(tone: 'active' | 'success' | 'warning' | 'danger'): string {
  switch (tone) {
    case 'success':
      return 'border-emerald-500/30 bg-emerald-500/5'
    case 'warning':
      return 'border-amber-500/30 bg-amber-500/5'
    case 'danger':
      return 'border-destructive/30 bg-destructive/5'
    default:
      return 'border-border bg-card/70'
  }
}

function statusClasses(tone: 'active' | 'success' | 'warning' | 'danger'): string {
  switch (tone) {
    case 'success':
      return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
    case 'warning':
      return 'bg-amber-500/10 text-amber-700 dark:text-amber-300'
    case 'danger':
      return 'bg-destructive/10 text-destructive'
    default:
      return 'bg-primary/10 text-primary'
  }
}

export function ResearchProgressCard({
  run,
  liveProgress,
  liveEvents = [],
  isLive = false,
}: {
  run: RunDetail
  liveProgress?: ResearchProgressPayload | null
  liveEvents?: ResearchRunHistoryEvent[]
  isLive?: boolean
}) {
  const model = buildProgressViewModel(run, { liveProgress, liveEvents })
  const [expanded, setExpanded] = useState(isLive)

  return (
    <div className={cn('rounded-2xl border px-4 py-4 shadow-sm', toneClasses(model.tone))}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-background/80 shadow-sm">
              <Activity className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground">
                {isLive ? 'Deep Research 正在执行' : 'Deep Research 执行记录'}
              </div>
              <div className="text-sm text-muted-foreground">
                {model.phaseLabel}
              </div>
            </div>
          </div>

          {model.summary && (
            <p className="max-w-2xl text-sm leading-6 text-foreground/90">
              {model.summary}
            </p>
          )}

          {(model.taskLine || model.iterationLine) && (
            <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
              {model.taskLine && (
                <span className="inline-flex items-center gap-1 rounded-full bg-background/80 px-2.5 py-1">
                  <ListChecks className="h-3.5 w-3.5" />
                  {model.taskLine}
                </span>
              )}
              {model.iterationLine && (
                <span className="inline-flex items-center gap-1 rounded-full bg-background/80 px-2.5 py-1">
                  <Clock3 className="h-3.5 w-3.5" />
                  {model.iterationLine}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold">
          <span className={cn('rounded-full px-3 py-1', statusClasses(model.tone))}>
            {model.statusLabel}
          </span>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4">
        {model.steps.map((step) => (
          <div
            key={step.label}
            className={cn(
              'rounded-xl border px-3 py-2 text-sm',
              step.state === 'complete' && 'border-emerald-500/20 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300',
              step.state === 'current' && 'border-primary/30 bg-primary/10 text-foreground',
              step.state === 'pending' && 'border-border/70 bg-background/70 text-muted-foreground',
            )}
          >
            {step.label}
          </div>
        ))}
      </div>

      {model.metrics.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {model.metrics.map((metric) => (
            <div
              key={metric.label}
              className="rounded-full border border-border/70 bg-background/80 px-3 py-1 text-xs text-muted-foreground"
            >
              <span className="font-medium text-foreground">{metric.value}</span>
              <span className="ml-1">{metric.label}</span>
            </div>
          ))}
        </div>
      )}

      {model.events.length > 0 && (
        <div className="mt-4 border-t border-border/60 pt-3">
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            {expanded ? '收起事件明细' : `展开事件明细 (${model.events.length})`}
          </button>

          {expanded && (
            <div className="mt-3 space-y-2">
              {model.events.map((event, index) => (
                <div
                  key={`${event.event_type}-${event.timestamp}-${index}`}
                  className="rounded-xl border border-border/60 bg-background/70 px-3 py-2"
                >
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>{formatEventTime(event.timestamp)}</span>
                    <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-foreground/80">
                      {event.progress?.phase_label ?? event.event_type}
                    </span>
                  </div>
                  {event.message && (
                    <p className="mt-1 text-sm leading-6 text-foreground/90">
                      {event.message}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

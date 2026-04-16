import { useState } from 'react'
import { ChevronDown, ChevronRight, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  buildProgressViewModel,
  formatEventTime,
  formatHistoryEventLabel,
  getProgressPayload,
  PHASE_LABELS,
  PHASE_ORDER,
} from '@/lib/research-progress'
import type {
  ResearchProgressPayload,
  ResearchProgressPhase,
  ResearchRunHistoryEvent,
  RunDetail,
} from '@/types/research'

type PhaseState = 'complete' | 'current' | 'pending'

function getPhaseState(
  phase: ResearchProgressPhase,
  current: ResearchProgressPhase,
): PhaseState {
  if (phase === current) return 'current'
  const idx = PHASE_ORDER.indexOf(phase)
  const curIdx = PHASE_ORDER.indexOf(current)
  if (current === 'failed') {
    if (phase === 'completed') return 'pending'
    if (idx < curIdx) return 'complete'
    return 'pending'
  }
  if (idx < curIdx) return 'complete'
  return 'pending'
}

function Dot({ state, isFailed }: { state: PhaseState; isFailed?: boolean }) {
  return (
    <div
      className={cn(
        'relative z-10 mt-1.5 h-2 w-2 rounded-full shrink-0',
        state === 'complete' && 'bg-muted-foreground',
        state === 'current' && !isFailed && 'bg-primary ring-2 ring-primary/20',
        state === 'current' && isFailed && 'bg-destructive ring-2 ring-destructive/20',
        state === 'pending' && 'border border-muted-foreground/40 bg-transparent',
      )}
    >
      {state === 'current' && (
        <span
          className={cn(
            'absolute inset-0 rounded-full animate-ping opacity-40',
            isFailed ? 'bg-destructive' : 'bg-primary',
          )}
        />
      )}
    </div>
  )
}

function TaskDetail({ task }: { task: NonNullable<ResearchProgressPayload['task']> }) {
  return (
    <div className="mt-1.5 rounded-md bg-muted/60 px-2.5 py-1.5 text-xs text-muted-foreground">
      <div className="font-medium text-foreground/80">
        任务 {task.index}/{task.total}
        {task.title ? ` · ${task.title}` : null}
      </div>
      {task.worker_step && (
        <div className="mt-0.5">
          {task.worker_step === 'rewrite_queries' && '改写查询'}
          {task.worker_step === 'search_and_rank' && '检索排序'}
          {task.worker_step === 'acquire_and_filter' && '抓取筛选'}
          {task.worker_step === 'extract_and_score' && '提取评分'}
          {task.worker_step === 'emit_results' && '输出结果'}
        </div>
      )}
    </div>
  )
}

function ResearchTimeline({
  phase,
  task,
  events,
}: {
  phase: ResearchProgressPhase
  task: ResearchProgressPayload['task']
  events: ResearchRunHistoryEvent[]
}) {
  const currentPhase = phase

  // Build a quick lookup of the latest event message per phase
  const messageByPhase = new Map<ResearchProgressPhase, string>()
  for (const event of events) {
    if (event.progress?.phase && event.message) {
      messageByPhase.set(event.progress.phase, event.message)
    }
  }

  return (
    <div className="relative pl-1">
      {/* vertical connecting line */}
      <div className="absolute left-[7px] top-2.5 bottom-2.5 w-px bg-border" />
      <div className="space-y-1">
        {PHASE_ORDER.map((phase) => {
          // 把 completed 和 failed 合并为单一终态节点
          if (phase === 'completed') {
            const terminalPhase = currentPhase === 'failed' ? 'failed' : 'completed'
            const state = getPhaseState(terminalPhase, currentPhase)
            const isFailed = terminalPhase === 'failed'
            const phaseMessage = messageByPhase.get(terminalPhase)

            return (
              <div key="terminal" className="relative flex items-start gap-3">
                <Dot state={state} isFailed={isFailed} />
                <div className="flex-1 min-w-0">
                  <div
                    className={cn(
                      'text-sm leading-5',
                      state === 'current'
                        ? 'font-medium text-foreground'
                        : state === 'pending'
                          ? 'text-muted-foreground/50'
                          : 'text-muted-foreground',
                    )}
                  >
                    {PHASE_LABELS[terminalPhase]}
                  </div>
                  {phaseMessage && state !== 'pending' && (
                    <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
                      {phaseMessage}
                    </p>
                  )}
                </div>
              </div>
            )
          }
          if (phase === 'failed') return null

          const state = getPhaseState(phase, currentPhase)
          const phaseMessage = messageByPhase.get(phase)
          const isExecuting = phase === 'executing_tasks' && state === 'current'

          return (
            <div key={phase} className="relative flex items-start gap-3">
              <Dot state={state} />
              <div className="flex-1 min-w-0">
                <div
                  className={cn(
                    'text-sm leading-5',
                    state === 'current'
                      ? 'font-medium text-foreground'
                      : state === 'pending'
                        ? 'text-muted-foreground/50'
                        : 'text-muted-foreground',
                  )}
                >
                  {PHASE_LABELS[phase]}
                </div>
                {phaseMessage && state !== 'pending' && (
                  <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
                    {phaseMessage}
                  </p>
                )}
                {isExecuting && task && <TaskDetail task={task} />}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ResearchMetrics({
  metrics,
}: {
  metrics: { label: string; value: string }[]
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {metrics.map((m) => (
        <span
          key={m.label}
          className="inline-flex items-center rounded-md border border-border/60 bg-background/80 px-2 py-0.5 text-xs text-muted-foreground"
        >
          <span className="font-medium text-foreground">{m.value}</span>
          <span className="ml-1">{m.label}</span>
        </span>
      ))}
    </div>
  )
}

function ResearchInsightPanel({
  label,
  content,
}: {
  label: string
  content: string
}) {
  return (
    <div className="rounded-lg border border-border/60 bg-background/70 px-3 py-2">
      <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground/80">
        {label}
      </div>
      <div className="mt-1 text-sm leading-5 text-foreground">
        {content}
      </div>
    </div>
  )
}

function ResearchGapHighlights({
  items,
}: {
  items: { key: string; title: string; meta: string; tone: 'warning' | 'danger' }[]
}) {
  if (items.length === 0) return null
  return (
    <div className="space-y-2">
      <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground/80">
        关键缺口
      </div>
      <div className="space-y-1.5">
        {items.map((item) => (
          <div
            key={item.key}
            className={cn(
              'rounded-lg border px-3 py-2',
              item.tone === 'danger'
                ? 'border-destructive/20 bg-destructive/[0.04]'
                : 'border-amber-500/20 bg-amber-500/[0.04]',
            )}
          >
            <div className="text-sm font-medium text-foreground">{item.title}</div>
            <div className="mt-1 text-xs text-muted-foreground">{item.meta}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ResearchRetryHighlights({
  items,
}: {
  items: { key: string; title: string; detail: string }[]
}) {
  if (items.length === 0) return null
  return (
    <div className="space-y-2">
      <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground/80">
        待重试任务
      </div>
      <div className="space-y-1.5">
        {items.map((item) => (
          <div key={item.key} className="rounded-lg border border-border/60 bg-background/70 px-3 py-2">
            <div className="text-sm font-medium text-foreground">{item.title}</div>
            <div className="mt-1 text-xs text-muted-foreground">{item.detail}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ResearchEventLog({ events }: { events: ResearchRunHistoryEvent[] }) {
  if (events.length === 0) return null
  return (
    <div className="mt-2 space-y-1 border-t border-border/40 pt-2">
      {events.map((event, index) => (
        <div
          key={`${event.event_type}-${event.timestamp}-${index}`}
          className="flex gap-2 text-xs text-muted-foreground"
        >
          <span className="tabular-nums shrink-0 text-muted-foreground/60">
            {formatEventTime(event.timestamp)}
          </span>
          <span className="line-clamp-2">
            {formatHistoryEventLabel(event)}
          </span>
        </div>
      ))}
    </div>
  )
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
  const progress = getProgressPayload(run, liveProgress ?? null, liveEvents)
  const [expanded, setExpanded] = useState(isLive)

  const headerText = isLive
    ? `Deep Research · ${model.phaseLabel}`
    : `Deep Research · ${model.statusLabel}`

  return (
    <div
      className={cn(
        'rounded-xl border text-[15px] overflow-hidden transition-colors',
        model.tone === 'success' && 'border-emerald-500/20 bg-emerald-500/[0.03]',
        model.tone === 'warning' && 'border-amber-500/20 bg-amber-500/[0.03]',
        model.tone === 'danger' && 'border-destructive/20 bg-destructive/[0.03]',
        model.tone === 'active' && 'border-border/60 bg-muted/30',
      )}
    >
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 px-3.5 py-2.5 text-left hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
        )}
        <Sparkles
          className={cn(
            'h-4 w-4 shrink-0',
            model.tone === 'success' && 'text-emerald-600 dark:text-emerald-400',
            model.tone === 'warning' && 'text-amber-600 dark:text-amber-400',
            model.tone === 'danger' && 'text-destructive',
            model.tone === 'active' && 'text-muted-foreground',
          )}
        />
        <span className="flex-1 text-sm text-muted-foreground truncate">
          {headerText}
        </span>
        {isLive && (
          <span className="relative flex h-2 w-2">
            <span
              className={cn(
                'absolute inline-flex h-full w-full animate-ping rounded-full opacity-40',
                model.tone === 'danger' ? 'bg-destructive' : 'bg-primary',
              )}
            />
            <span
              className={cn(
                'relative inline-flex h-2 w-2 rounded-full',
                model.tone === 'danger' ? 'bg-destructive' : 'bg-primary',
              )}
            />
          </span>
        )}
      </button>

      {expanded && (
        <div className="px-3.5 pb-3.5 pt-1 space-y-3">
          <ResearchTimeline phase={progress.phase} task={progress.task} events={model.events} />

          {model.metrics.length > 0 && (
            <ResearchMetrics metrics={model.metrics} />
          )}

          {model.actionLabel && model.summary && (
            <ResearchInsightPanel
              label={model.actionLabel}
              content={model.summary}
            />
          )}

          <ResearchGapHighlights items={model.gapHighlights} />

          <ResearchRetryHighlights items={model.retryHighlights} />

          <ResearchEventLog events={model.events} />
        </div>
      )}
    </div>
  )
}

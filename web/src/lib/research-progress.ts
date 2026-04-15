import type {
  ResearchProgressCounts,
  ResearchProgressPayload,
  ResearchProgressPhase,
  ResearchRunHistoryEvent,
  ResearchWorkerStep,
  RunDetail,
  RunStatus,
  SSEEvent,
} from '@/types/research'

type ProgressTone = 'active' | 'success' | 'warning' | 'danger'
type ProgressStepState = 'complete' | 'current' | 'pending'

export type ResearchProgressStep = {
  label: string
  state: ProgressStepState
}

export type ResearchMetric = {
  label: string
  value: string
}

export type ResearchProgressViewModel = {
  phase: ResearchProgressPhase
  phaseLabel: string
  tone: ProgressTone
  statusLabel: string
  summary: string | null
  taskLine: string | null
  iterationLine: string | null
  metrics: ResearchMetric[]
  steps: ResearchProgressStep[]
  events: ResearchRunHistoryEvent[]
}

export const PHASE_LABELS: Record<ResearchProgressPhase, string> = {
  queued: '已入队',
  clarifying_scope: '澄清研究范围',
  planning: '规划研究任务',
  executing_tasks: '执行研究任务',
  merging_evidence: '合并证据',
  checking_gaps: '检查研究缺口',
  replanning: '准备重新规划',
  synthesizing: '生成报告草稿',
  auditing: '校验引用与结构',
  awaiting_review: '等待人工复核',
  finalizing: '整理最终结果',
  completed: '已完成',
  failed: '执行失败',
}

const STATUS_LABELS: Record<RunStatus, string> = {
  queued: '排队中',
  running: '运行中',
  interrupted: '待复核',
  completed: '已完成',
  failed: '失败',
}

export const PHASE_ORDER: ResearchProgressPhase[] = [
  'queued',
  'clarifying_scope',
  'planning',
  'executing_tasks',
  'merging_evidence',
  'checking_gaps',
  'replanning',
  'synthesizing',
  'auditing',
  'awaiting_review',
  'finalizing',
  'completed',
  'failed',
]

const STEP_GROUPS: Array<{ label: string; phases: ResearchProgressPhase[] }> = [
  { label: '准备', phases: ['queued', 'clarifying_scope', 'planning', 'replanning'] },
  { label: '执行', phases: ['executing_tasks', 'merging_evidence', 'checking_gaps'] },
  { label: '成文', phases: ['synthesizing', 'auditing'] },
  { label: '结束', phases: ['awaiting_review', 'finalizing', 'completed', 'failed'] },
]

export function isResearchSSEEvent(event: SSEEvent): boolean {
  return typeof event.run_id === 'string' && event.type.startsWith('run.')
}

export function toHistoryEvent(event: SSEEvent): ResearchRunHistoryEvent | null {
  if (!isResearchSSEEvent(event)) {
    return null
  }
  const progress = event.data.progress ?? fallbackProgress(event.status as RunStatus)
  return {
    event_type: event.type as ResearchRunHistoryEvent['event_type'],
    status: event.status as RunStatus,
    timestamp: event.timestamp,
    message: event.data.message ?? null,
    progress,
  }
}

export function getRunHistory(run: RunDetail, liveEvents: ResearchRunHistoryEvent[] = []): ResearchRunHistoryEvent[] {
  if (liveEvents.length > 0) {
    return liveEvents
  }
  return run.progress_events
}

export function getProgressPayload(
  run: RunDetail,
  liveProgress: ResearchProgressPayload | null = null,
  liveEvents: ResearchRunHistoryEvent[] = [],
): ResearchProgressPayload {
  if (liveProgress) {
    return liveProgress
  }
  const latest = getLatestHistoryEvent(run, liveEvents)
  if (latest?.progress) {
    return latest.progress
  }
  return fallbackProgress(run.status, run.request.max_iterations ?? null)
}

export function buildProgressViewModel(
  run: RunDetail,
  options: {
    liveProgress?: ResearchProgressPayload | null
    liveEvents?: ResearchRunHistoryEvent[]
  } = {},
): ResearchProgressViewModel {
  const events = getRunHistory(run, options.liveEvents)
  const progress = getProgressPayload(run, options.liveProgress ?? null, options.liveEvents ?? [])
  const latestEvent = events[events.length - 1] ?? null
  return {
    phase: progress.phase,
    phaseLabel: PHASE_LABELS[progress.phase] ?? progress.phase_label,
    tone: getTone(progress.phase),
    statusLabel: STATUS_LABELS[run.status],
    summary: latestEvent?.message ?? defaultSummary(progress.phase),
    taskLine: buildTaskLine(progress),
    iterationLine: buildIterationLine(progress),
    metrics: buildMetrics(progress.counts),
    steps: buildSteps(progress.phase),
    events,
  }
}

export function formatEventTime(timestamp: string): string {
  const value = new Date(timestamp)
  if (Number.isNaN(value.getTime())) {
    return timestamp
  }
  return value.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function getLatestHistoryEvent(
  run: RunDetail,
  liveEvents: ResearchRunHistoryEvent[],
): ResearchRunHistoryEvent | null {
  const events = getRunHistory(run, liveEvents)
  return events.length > 0 ? events[events.length - 1] : null
}

function fallbackProgress(
  status: RunStatus,
  maxIterations: number | null = null,
): ResearchProgressPayload {
  const phaseByStatus: Record<RunStatus, ResearchProgressPhase> = {
    queued: 'queued',
    running: 'executing_tasks',
    interrupted: 'awaiting_review',
    completed: 'completed',
    failed: 'failed',
  }
  const phase = phaseByStatus[status]
  return {
    phase,
    phase_label: PHASE_LABELS[phase],
    iteration: null,
    max_iterations: maxIterations,
    task: null,
    counts: emptyCounts(),
    review: {
      required: status === 'interrupted',
      kind: status === 'interrupted' ? 'human_review' : null,
    },
  }
}

function emptyCounts(): ResearchProgressCounts {
  return {
    planned_tasks: null,
    completed_tasks: null,
    search_hits: null,
    acquired_contents: null,
    kept_sources: null,
    evidence_count: null,
    warnings: null,
  }
}

function buildTaskLine(progress: ResearchProgressPayload): string | null {
  if (!progress.task) {
    return null
  }
  const stepText = progress.task.worker_step ? ` · ${workerStepLabel(progress.task.worker_step)}` : ''
  return `任务 ${progress.task.index}/${progress.task.total}：${progress.task.title}${stepText}`
}

function buildIterationLine(progress: ResearchProgressPayload): string | null {
  if (!progress.iteration || !progress.max_iterations) {
    return null
  }
  return `第 ${progress.iteration} / ${progress.max_iterations} 轮`
}

function buildMetrics(counts: ResearchProgressCounts): ResearchMetric[] {
  const metrics: ResearchMetric[] = []
  pushMetric(metrics, '任务', counts.planned_tasks, counts.completed_tasks, ' / ')
  pushMetric(metrics, '命中', counts.search_hits)
  pushMetric(metrics, '抓取', counts.acquired_contents)
  pushMetric(metrics, '来源', counts.kept_sources)
  pushMetric(metrics, '证据', counts.evidence_count)
  pushMetric(metrics, '警告', counts.warnings)
  return metrics
}

function pushMetric(
  metrics: ResearchMetric[],
  label: string,
  value: number | null,
  secondary?: number | null,
  separator = '',
): void {
  if (value == null && secondary == null) {
    return
  }
  const text = value == null
    ? `${secondary ?? ''}`
    : secondary == null
      ? `${value}`
      : `${secondary}${separator}${value}`
  metrics.push({ label, value: text })
}

function buildSteps(phase: ResearchProgressPhase): ResearchProgressStep[] {
  const currentIndex = phaseIndex(phase)
  return STEP_GROUPS.map((group) => {
    const groupIndices = group.phases.map((item) => phaseIndex(item))
    const maxIndex = Math.max(...groupIndices)
    const minIndex = Math.min(...groupIndices)
    let state: ProgressStepState = 'pending'
    if (currentIndex > maxIndex) {
      state = 'complete'
    } else if (currentIndex >= minIndex && currentIndex <= maxIndex) {
      state = 'current'
    }
    if (phase === 'failed' && group.label === '结束') {
      state = 'current'
    }
    return { label: group.label, state }
  })
}

function phaseIndex(phase: ResearchProgressPhase): number {
  return PHASE_ORDER.indexOf(phase)
}

function getTone(phase: ResearchProgressPhase): ProgressTone {
  if (phase === 'completed') {
    return 'success'
  }
  if (phase === 'failed') {
    return 'danger'
  }
  if (phase === 'awaiting_review') {
    return 'warning'
  }
  return 'active'
}

function defaultSummary(phase: ResearchProgressPhase): string {
  switch (phase) {
    case 'queued':
      return '研究任务已创建，等待开始。'
    case 'clarifying_scope':
      return '正在理解问题并补全研究范围。'
    case 'planning':
      return '正在拆解研究任务。'
    case 'executing_tasks':
      return '正在检索来源、抓取内容并提取证据。'
    case 'merging_evidence':
      return '正在合并各任务返回的证据。'
    case 'checking_gaps':
      return '正在检查证据缺口与质量。'
    case 'replanning':
      return '当前证据不足，准备进入下一轮规划。'
    case 'synthesizing':
      return '正在组织并生成报告草稿。'
    case 'auditing':
      return '正在校验引用和报告结构。'
    case 'awaiting_review':
      return '需要人工复核后才能完成。'
    case 'finalizing':
      return '正在整理最终结果。'
    case 'completed':
      return '研究流程已完成。'
    case 'failed':
      return '研究流程执行失败。'
  }
}

function workerStepLabel(step: ResearchWorkerStep): string {
  switch (step) {
    case 'rewrite_queries':
      return '改写查询'
    case 'search_and_rank':
      return '检索排序'
    case 'acquire_and_filter':
      return '抓取筛选'
    case 'extract_and_score':
      return '提取评分'
    case 'emit_results':
      return '输出结果'
  }
}

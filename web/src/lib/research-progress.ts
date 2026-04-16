import type {
  ResearchProgressCounts,
  ResearchProgressGap,
  ResearchProgressPayload,
  ResearchProgressPhase,
  ResearchRetryTaskProgress,
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

export type ResearchGapHighlight = {
  key: string
  title: string
  meta: string
  tone: 'warning' | 'danger'
}

export type ResearchRetryHighlight = {
  key: string
  title: string
  detail: string
}

export type ResearchProgressViewModel = {
  phase: ResearchProgressPhase
  phaseLabel: string
  tone: ProgressTone
  statusLabel: string
  summary: string | null
  actionLabel: string | null
  actionDetail: string | null
  taskLine: string | null
  iterationLine: string | null
  metrics: ResearchMetric[]
  gapHighlights: ResearchGapHighlight[]
  retryHighlights: ResearchRetryHighlight[]
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
    summary: progress.action?.detail ?? latestEvent?.message ?? defaultSummary(progress.phase),
    actionLabel: progress.action?.label ?? null,
    actionDetail: progress.action?.detail ?? null,
    taskLine: buildTaskLine(progress),
    iterationLine: buildIterationLine(progress),
    metrics: buildMetrics(progress.counts),
    gapHighlights: buildGapHighlights(progress.gaps),
    retryHighlights: buildRetryHighlights(progress.retry_tasks),
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

export function formatProgressNarrative(progress: ResearchProgressPayload): string | null {
  const leadGap = progress.gaps[0]
  if (progress.action?.kind === 'targeted_retry') {
    const retryTitles = progress.retry_tasks.slice(0, 2).map((task) => task.title)
    if (retryTitles.length > 0) {
      return `系统正在优先局部重试：${retryTitles.join('、')}${leadGap ? `。当前焦点是“${leadGap.title}”。` : '。'}`
    }
    if (leadGap) {
      return `系统正在优先局部重试，先补“${leadGap.title}”。`
    }
  }
  if (progress.action?.kind === 'replan') {
    if (leadGap) {
      return `当前缺口无法只靠局部重试修复，准备围绕“${leadGap.title}”进入下一轮规划。`
    }
    return progress.action.detail ?? '当前证据不足，准备进入下一轮规划。'
  }
  if (progress.action?.kind === 'review') {
    return progress.action.detail ?? '系统已暂停自动推进，等待人工复核。'
  }
  if (progress.task) {
    return `当前正在处理任务“${progress.task.title}”。`
  }
  return null
}

export function formatHistoryEventLabel(event: ResearchRunHistoryEvent): string {
  if (event.progress) {
    const progress = event.progress
    if (progress.action?.kind === 'targeted_retry' && progress.retry_tasks.length > 0) {
      return `优先局部重试：${progress.retry_tasks.slice(0, 2).map((task) => task.title).join('、')}`
    }
    if (progress.action?.kind === 'replan') {
      return progress.gaps[0]
        ? `进入下一轮规划：${progress.gaps[0].title}`
        : (progress.action.detail ?? progress.action.label)
    }
    if (progress.action?.kind === 'review') {
      return progress.action.detail ?? progress.action.label
    }
  }
  return event.message || event.progress?.phase_label || event.event_type
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
    action: status === 'interrupted'
      ? {
          kind: 'review',
          label: '等待人工复核',
          detail: '系统已暂停自动推进，等待人工确认或编辑报告后再继续。',
        }
      : null,
    gaps: [],
    retry_tasks: [],
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

function buildGapHighlights(gaps: ResearchProgressGap[]): ResearchGapHighlight[] {
  return gaps.map((gap) => ({
    key: `${gap.task_id}-${gap.title}`,
    title: gap.title,
    meta: [gapScopeLabel(gap), gapSeverityLabel(gap), gap.retry_action ? retryActionLabel(gap.retry_action) : null]
      .filter(Boolean)
      .join(' · '),
    tone: gap.severity === 'high' ? 'danger' : 'warning',
  }))
}

function buildRetryHighlights(retryTasks: ResearchRetryTaskProgress[]): ResearchRetryHighlight[] {
  return retryTasks.map((task) => ({
    key: task.task_id,
    title: task.title,
    detail: [
      task.retry_action ? retryActionLabel(task.retry_action) : '继续执行',
      `已重试 ${task.retry_count} 次`,
      task.query_budget != null ? `查询预算 ${task.query_budget}` : null,
      task.fetch_budget != null ? `抓取预算 ${task.fetch_budget}` : null,
    ]
      .filter(Boolean)
      .join(' · '),
  }))
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

function gapScopeLabel(gap: ResearchProgressGap): string {
  if (gap.scope === 'global') {
    return '全局覆盖'
  }
  switch (gap.gap_type) {
    case 'retrieval_failure':
      return '检索缺口'
    case 'low_source_diversity':
      return '来源不足'
    case 'coverage_gap':
      return '覆盖缺口'
    case 'missing_evidence':
      return '证据缺失'
    case 'weak_evidence':
      return '证据偏弱'
  }
}

function gapSeverityLabel(gap: ResearchProgressGap): string {
  switch (gap.severity) {
    case 'high':
      return '高优先级'
    case 'medium':
      return '中优先级'
    case 'low':
      return '低优先级'
  }
}

function retryActionLabel(action: NonNullable<ResearchProgressGap['retry_action']>): string {
  switch (action) {
    case 'expand_fetch':
      return '扩抓取'
    case 'expand_queries':
      return '扩查询'
    case 'replan':
      return '重规划'
  }
}

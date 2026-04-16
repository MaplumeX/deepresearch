export type ConversationMode = 'chat' | 'research'
export type RunStatus = 'queued' | 'running' | 'interrupted' | 'completed' | 'failed'
export type ChatTurnStatus = 'queued' | 'running' | 'completed' | 'failed'
export type RunEventType =
  | 'run.created'
  | 'run.status_changed'
  | 'run.progress'
  | 'run.interrupted'
  | 'run.completed'
  | 'run.failed'
  | 'run.resumed'
export type ChatEventType =
  | 'chat.turn.created'
  | 'chat.turn.status_changed'
  | 'chat.turn.progress'
  | 'chat.turn.completed'
  | 'chat.turn.failed'
export type ResearchProgressPhase =
  | 'queued'
  | 'clarifying_scope'
  | 'planning'
  | 'executing_tasks'
  | 'merging_evidence'
  | 'checking_gaps'
  | 'replanning'
  | 'synthesizing'
  | 'auditing'
  | 'awaiting_review'
  | 'finalizing'
  | 'completed'
  | 'failed'
export type ResearchWorkerStep =
  | 'rewrite_queries'
  | 'search_and_rank'
  | 'acquire_and_filter'
  | 'extract_and_score'
  | 'emit_results'

export type ConversationMessage = {
  message_id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  provider_message_id?: string | null
  run_id: string | null
  parent_message_id: string | null
  created_at: string
  updated_at: string
}

export type ConversationSummary = {
  conversation_id: string
  mode: ConversationMode
  title: string
  latest_message_preview: string
  latest_run_status: RunStatus | null
  created_at: string
  updated_at: string
  is_pinned?: boolean
}

export type ResearchRequestPayload = {
  question: string
  scope?: string | null
  output_language?: 'zh-CN' | 'en'
  max_iterations?: number
  max_parallel_tasks?: number
}

export type ResearchProgressCounts = {
  planned_tasks: number | null
  completed_tasks: number | null
  search_hits: number | null
  acquired_contents: number | null
  kept_sources: number | null
  evidence_count: number | null
  warnings: number | null
}

export type ResearchTaskProgress = {
  task_id: string
  title: string
  index: number
  total: number
  status: 'pending' | 'running' | 'done' | 'failed'
  worker_step: ResearchWorkerStep | null
}

export type ResearchReviewProgress = {
  required: boolean
  kind: 'human_review' | null
}

export type ResearchProgressPayload = {
  phase: ResearchProgressPhase
  phase_label: string
  iteration: number | null
  max_iterations: number | null
  task: ResearchTaskProgress | null
  counts: ResearchProgressCounts
  review: ResearchReviewProgress
}

export type SourceCard = {
  source_id: string
  title: string
  url: string
  snippet: string
  providers: string[]
  acquisition_method: string | null
  fetched_at: string
  is_cited: boolean
}

export type CitationIndexEntry = SourceCard & {
  cited_in_sections: string[]
  occurrence_count: number
  relevance_score: number | null
  confidence: number | null
}

export type ReportSection = {
  section_id: string
  heading: string
  body_markdown: string
  cited_source_ids: string[]
}

export type StructuredReport = {
  title: string
  summary: string
  markdown: string
  sections: ReportSection[]
  cited_source_ids: string[]
  citation_index: CitationIndexEntry[]
  source_cards: SourceCard[]
}

export type ResearchRunHistoryEvent = {
  event_type: RunEventType
  status: RunStatus
  timestamp: string
  message: string | null
  progress: ResearchProgressPayload | null
}

export type RunResult = {
  final_report?: string
  draft_report?: string
  final_structured_report?: StructuredReport
  draft_structured_report?: StructuredReport
}

export type RunDetail = {
  run_id: string
  conversation_id: string
  origin_message_id: string
  assistant_message_id: string
  parent_run_id: string | null
  status: RunStatus
  request: ResearchRequestPayload
  result: RunResult | null
  warnings: string[]
  error_message: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
  progress_events: ResearchRunHistoryEvent[]
}

export type ConversationDetail = {
  conversation_id: string
  mode: ConversationMode
  title: string
  latest_message_preview: string
  latest_run_status: RunStatus | null
  created_at: string
  updated_at: string
  messages: ConversationMessage[]
  runs: RunDetail[]
}

export type ChatTurnDetail = {
  turn_id: string
  conversation_id: string
  origin_message_id: string
  assistant_message_id: string
  status: ChatTurnStatus
  request: {
    question: string
  }
  error_message: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
}

export type SSEEventData = {
  message?: string
  progress?: ResearchProgressPayload
  resume_payload?: {
    approved?: boolean
    edited_report?: string | null
  }
  run?: Omit<RunDetail, 'progress_events'>
  turn?: ChatTurnDetail
  conversation?: ConversationSummary
  assistant_message?: ConversationMessage
}

export type SSEEvent = {
  type: RunEventType | ChatEventType | string
  status: RunStatus | ChatTurnStatus | string
  timestamp: string
  run_id?: string
  turn_id?: string
  data: SSEEventData
}

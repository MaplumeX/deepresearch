export type ConversationMessage = {
  message_id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  run_id: string | null
  parent_message_id: string | null
  created_at: string
  updated_at: string
}

export type ConversationSummary = {
  conversation_id: string
  title: string
  latest_message_preview: string
  latest_run_status: 'queued' | 'running' | 'interrupted' | 'completed' | 'failed' | null
  created_at: string
  updated_at: string
}

export type RunDetail = {
  run_id: string
  conversation_id: string
  origin_message_id: string
  assistant_message_id: string
  parent_run_id: string | null
  status: 'queued' | 'running' | 'interrupted' | 'completed' | 'failed'
  // using any for request/result as exact schema may vary or we can use JSON object
  request: unknown
  result: unknown | null
  warnings: string[]
  error_message: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
}

export type ConversationDetail = {
  conversation_id: string
  title: string
  latest_message_preview: string
  latest_run_status: 'queued' | 'running' | 'interrupted' | 'completed' | 'failed' | null
  created_at: string
  updated_at: string
  messages: ConversationMessage[]
  runs: RunDetail[]
}

export type SSEEvent = {
  type: string
  run_id: string
  status: string
  timestamp: string
  data: {
    message?: string
    run?: RunDetail
    conversation?: ConversationSummary
    assistant_message?: ConversationMessage
  }
}

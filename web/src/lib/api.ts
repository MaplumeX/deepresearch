import type {
  ChatTurnDetail,
  ConversationDetail,
  ConversationMode,
  ConversationSummary,
  RunDetail,
  SSEEvent,
} from '@/types/research'

async function parseJson<T>(res: Response): Promise<T> {
  const data = await res.json()
  if (!res.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : 'Request failed'
    throw new Error(detail)
  }
  return data as T
}

export async function fetchConversations(): Promise<ConversationSummary[]> {
  const res = await fetch('/api/conversations')
  const data = await parseJson<{ conversations: ConversationSummary[] }>(res)
  return data.conversations
}

export async function fetchConversation(id: string): Promise<ConversationDetail> {
  const res = await fetch(`/api/conversations/${id}`)
  const data = await parseJson<{ conversation: ConversationDetail }>(res)
  return data.conversation
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await fetch(`/api/conversations/${id}`, { method: 'DELETE' })
  await parseJson<unknown>(res)
}

export async function pinConversation(id: string): Promise<void> {
  const res = await fetch(`/api/conversations/${id}/pin`, { method: 'POST' })
  await parseJson<unknown>(res)
}

export async function startConversation(
  question: string,
  mode: ConversationMode,
): Promise<{ conversation: ConversationDetail; run: RunDetail | null; turn: ChatTurnDetail | null }> {
  const body: Record<string, unknown> = { question, mode }
  if (mode === 'research') {
    body.output_language = 'zh-CN'
    body.max_iterations = 2
    body.max_parallel_tasks = 3
  }
  const res = await fetch('/api/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJson<{ conversation: ConversationDetail; run: RunDetail | null; turn: ChatTurnDetail | null }>(res)
}

export async function continueConversation(
  conversationId: string,
  question: string,
  mode: ConversationMode,
  parentRunId?: string,
): Promise<{ conversation: ConversationDetail; run: RunDetail | null; turn: ChatTurnDetail | null }> {
  const body: Record<string, unknown> = { question }
  if (mode === 'research' && parentRunId) {
    body.parent_run_id = parentRunId
  }
  const res = await fetch(`/api/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJson<{ conversation: ConversationDetail; run: RunDetail | null; turn: ChatTurnDetail | null }>(res)
}

export function subscribeToRunEvents(
  runId: string,
  onEvent: (ev: SSEEvent) => void,
  onError: (err: unknown) => void,
): () => void {
  return subscribeToEvents(`/api/research/runs/${runId}/events`, onEvent, onError)
}

export function subscribeToChatTurnEvents(
  turnId: string,
  onEvent: (ev: SSEEvent) => void,
  onError: (err: unknown) => void,
): () => void {
  return subscribeToEvents(`/api/chat/turns/${turnId}/events`, onEvent, onError)
}

const SSE_EVENT_TYPES = [
  'run.created',
  'run.status_changed',
  'run.progress',
  'run.interrupted',
  'run.completed',
  'run.failed',
  'run.resumed',
  'chat.turn.created',
  'chat.turn.status_changed',
  'chat.turn.progress',
  'chat.turn.completed',
  'chat.turn.failed',
] as const

function subscribeToEvents(
  url: string,
  onEvent: (ev: SSEEvent) => void,
  onError: (err: unknown) => void,
): () => void {
  const eventSource = new EventSource(url)
  let closedByClient = false
  let sawTerminalEvent = false

  const handleEvent = (event: MessageEvent<string>) => {
    try {
      const parsed = JSON.parse(event.data) as SSEEvent
      onEvent(parsed)
      if (
        [
          'run.completed',
          'run.failed',
          'run.interrupted',
          'chat.turn.completed',
          'chat.turn.failed',
        ].includes(parsed.type)
      ) {
        sawTerminalEvent = true
        closedByClient = true
        eventSource.close()
      }
    } catch (err) {
      console.error('Failed to parse SSE event', err)
    }
  }

  for (const eventType of SSE_EVENT_TYPES) {
    eventSource.addEventListener(eventType, handleEvent as EventListener)
  }

  // Keep a fallback for unnamed SSE events.
  eventSource.onmessage = handleEvent

  eventSource.onerror = (err) => {
    if (closedByClient || sawTerminalEvent || eventSource.readyState === EventSource.CLOSED) {
      return
    }
    onError(err)
    if (eventSource.readyState !== EventSource.CLOSED) {
      closedByClient = true
      eventSource.close()
    }
  }

  return () => {
    closedByClient = true
    eventSource.close()
  }
}

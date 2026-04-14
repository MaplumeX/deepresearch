import type { ConversationDetail, ConversationSummary, RunDetail, SSEEvent } from '@/types/research'

export async function fetchConversations(): Promise<ConversationSummary[]> {
  const res = await fetch('/api/research/conversations')
  const data = await res.json()
  return data.conversations
}

export async function fetchConversation(id: string): Promise<ConversationDetail> {
  const res = await fetch(`/api/research/conversations/${id}`)
  const data = await res.json()
  return data.conversation
}

export async function startConversation(question: string): Promise<[ConversationDetail, RunDetail]> {
  const res = await fetch('/api/research/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      output_language: "zh-CN",
      max_iterations: 2,
      max_parallel_tasks: 3
    })
  })
  const data = await res.json()
  return [data.conversation, data.run]
}

export async function continueConversation(conversationId: string, question: string, parentRunId?: string): Promise<[ConversationDetail, RunDetail]> {
  const body: Record<string, unknown> = {
    question,
    output_language: "zh-CN",
    max_iterations: 2,
    max_parallel_tasks: 3
  }
  if (parentRunId) {
    body.parent_run_id = parentRunId
  }
  const res = await fetch(`/api/research/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  const data = await res.json()
  return [data.conversation, data.run]
}

export function subscribeToRunEvents(runId: string, onEvent: (ev: SSEEvent) => void, onError: (err: unknown) => void): () => void {
  const eventSource = new EventSource(`/api/research/runs/${runId}/events`)
  
  eventSource.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data)
      onEvent(parsed)
      if (['run.completed', 'run.failed', 'run.interrupted'].includes(parsed.type)) {
        eventSource.close()
      }
    } catch (err) {
      console.error('Failed to parse SSE event', err)
    }
  }

  eventSource.onerror = (err) => {
    onError(err)
    if (eventSource.readyState === EventSource.CLOSED) {
      // closed
    } else {
      eventSource.close()
    }
  }

  return () => {
    eventSource.close()
  }
}

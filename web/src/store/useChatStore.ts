import { create } from 'zustand'
import type {
  ChatTurnDetail,
  ConversationDetail,
  ConversationMessage,
  ConversationMode,
  ConversationSummary,
  RunDetail,
  SSEEvent,
} from '@/types/research'
import {
  continueConversation,
  fetchConversation,
  fetchConversations,
  startConversation,
  subscribeToChatTurnEvents,
  subscribeToRunEvents,
} from '@/lib/api'

type ActiveStream = {
  cleanup: () => void
  streamId: string
}

interface ChatState {
  conversations: ConversationSummary[]
  activeConversationId: string | null
  activeConversation: ConversationDetail | null
  draftMode: ConversationMode
  isGenerating: boolean
  streamingRunId: string | null
  streamingAssistantPreview: string
  error: string | null
  activeStream: ActiveStream | null
  loadConversations: () => Promise<void>
  loadConversation: (id: string) => Promise<void>
  sendMessage: (question: string) => Promise<void>
  startNewChat: () => void
  activateResearchDraft: () => void
  deactivateResearchDraft: () => void
  exitResearchConversation: () => void
  clearError: () => void
}

function isTerminalEvent(event: SSEEvent): boolean {
  return [
    'run.completed',
    'run.failed',
    'run.interrupted',
    'chat.turn.completed',
    'chat.turn.failed',
  ].includes(event.type)
}

function getConversationMode(
  activeConversation: ConversationDetail | null,
  draftMode: ConversationMode,
): ConversationMode {
  return activeConversation?.mode ?? draftMode
}

function createOptimisticConversation(
  question: string,
  mode: ConversationMode,
  optimisticUserMsg: ConversationMessage,
): ConversationDetail {
  const now = new Date().toISOString()
  return {
    conversation_id: 'temp',
    mode,
    title: mode === 'research' ? 'New Research' : 'New Chat',
    latest_message_preview: question,
    latest_run_status: mode === 'research' ? 'queued' : null,
    created_at: now,
    updated_at: now,
    messages: [optimisticUserMsg],
    runs: [],
  }
}

export const useChatStore = create<ChatState>((set, get) => {
  const clearActiveStream = () => {
    const activeStream = get().activeStream
    if (activeStream) {
      activeStream.cleanup()
    }
    set({ activeStream: null, streamingRunId: null })
  }

  const resetToNewChat = () => {
    clearActiveStream()
    set({
      activeConversationId: null,
      activeConversation: null,
      draftMode: 'chat',
      streamingAssistantPreview: '',
      isGenerating: false,
      error: null,
    })
  }

  const attachStream = (
    mode: ConversationMode,
    streamId: string,
    conversationId: string,
  ) => {
    clearActiveStream()
    const subscribe = mode === 'research' ? subscribeToRunEvents : subscribeToChatTurnEvents
    const cleanup = subscribe(
      streamId,
      (event) => {
        if (event.data?.assistant_message?.content) {
          set({ streamingAssistantPreview: event.data.assistant_message.content })
        }

        if (isTerminalEvent(event)) {
          clearActiveStream()
          set({ isGenerating: false })
          void get().loadConversation(conversationId)
          void get().loadConversations()
        }
      },
      (err) => {
        const message = err instanceof Error ? err.message : 'Connection error'
        clearActiveStream()
        console.error('SSE Error:', err)
        set({ isGenerating: false, error: message })
      },
    )

    set({
      activeStream: { cleanup, streamId },
      streamingRunId: streamId,
    })
  }

  return {
    conversations: [],
    activeConversationId: null,
    activeConversation: null,
    draftMode: 'chat',
    isGenerating: false,
    streamingRunId: null,
    streamingAssistantPreview: '',
    error: null,
    activeStream: null,

    clearError: () => set({ error: null }),

    startNewChat: () => {
      resetToNewChat()
    },

    activateResearchDraft: () => set({ draftMode: 'research', error: null }),

    deactivateResearchDraft: () => set({ draftMode: 'chat', error: null }),

    exitResearchConversation: () => {
      resetToNewChat()
    },

    loadConversations: async () => {
      try {
        const data = await fetchConversations()
        set({ conversations: data, error: null })
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load conversations'
        console.error('Failed to load convs:', err)
        set({ error: message })
      }
    },

    loadConversation: async (id) => {
      try {
        if (get().activeConversationId !== id) {
          clearActiveStream()
          set({ isGenerating: false, streamingAssistantPreview: '' })
        }
        const data = await fetchConversation(id)
        set({
          activeConversationId: id,
          activeConversation: data,
          draftMode: 'chat',
          streamingAssistantPreview: '',
          error: null,
        })
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load conversation'
        console.error('Failed to load conv:', err)
        set({ error: message })
      }
    },

    sendMessage: async (question: string) => {
      const {
        activeConversation,
        activeConversationId,
        draftMode,
      } = get()
      const mode = getConversationMode(activeConversation, draftMode)
      const now = new Date().toISOString()
      const previousConversation = activeConversation
      const optimisticUserMsg: ConversationMessage = {
        message_id: `temp-${Date.now()}`,
        conversation_id: activeConversationId || 'temp',
        role: 'user',
        content: question,
        run_id: null,
        parent_message_id: null,
        created_at: now,
        updated_at: now,
      }

      clearActiveStream()
      set({ isGenerating: true, streamingAssistantPreview: '', error: null })

      try {
        let detail: ConversationDetail
        let run: RunDetail | null = null
        let turn: ChatTurnDetail | null = null

        if (!activeConversationId) {
          set({
            activeConversation: createOptimisticConversation(question, mode, optimisticUserMsg),
          })

          const result = await startConversation(question, mode)
          detail = result.conversation
          run = result.run
          turn = result.turn

          set({ activeConversationId: detail.conversation_id })
          await get().loadConversations()
        } else {
          const currentConversation = activeConversation ?? createOptimisticConversation(question, mode, optimisticUserMsg)
          set({
            activeConversation: {
              ...currentConversation,
              latest_message_preview: question,
              updated_at: now,
              messages: [...currentConversation.messages, optimisticUserMsg],
            },
          })

          const result = await continueConversation(activeConversationId, question, mode)
          detail = result.conversation
          run = result.run
          turn = result.turn
        }

        set({ activeConversation: detail })

        if (run) {
          attachStream('research', run.run_id, detail.conversation_id)
          return
        }
        if (turn) {
          attachStream('chat', turn.turn_id, detail.conversation_id)
          return
        }

        throw new Error('Missing stream target')
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to send message'
        console.error('Failed to send:', err)
        set({
          activeConversation: previousConversation,
          activeConversationId: previousConversation?.conversation_id ?? null,
          isGenerating: false,
          error: message,
          streamingAssistantPreview: '',
        })
      }
    },
  }
})

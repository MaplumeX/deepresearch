import { create } from 'zustand'
import type { ConversationSummary, ConversationDetail, ConversationMessage, RunDetail } from '@/types/research'
import { fetchConversations, fetchConversation, startConversation, continueConversation, subscribeToRunEvents } from '@/lib/api'

interface ChatState {
  conversations: ConversationSummary[]
  activeConversationId: string | null
  activeConversationParams: ConversationDetail | null

  isGenerating: boolean
  streamingRunId: string | null
  streamingAssistantPreview: string
  error: string | null

  loadConversations: () => Promise<void>
  loadConversation: (id: string) => Promise<void>
  sendMessage: (question: string) => Promise<void>
  startNewChat: () => void
  clearError: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  activeConversationParams: null,
  
  isGenerating: false,
  streamingRunId: null,
  streamingAssistantPreview: "",
  error: null,

  clearError: () => set({ error: null }),

  startNewChat: () => set({
    activeConversationId: null,
    activeConversationParams: null,
    streamingAssistantPreview: '',
    isGenerating: false,
    error: null
  }),

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
      const data = await fetchConversation(id)
      set({ activeConversationId: id, activeConversationParams: data, streamingAssistantPreview: "", error: null })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load conversation'
      console.error('Failed to load conv:', err)
      set({ error: message })
    }
  },

  sendMessage: async (question: string) => {
    const { activeConversationId, activeConversationParams } = get()
    set({ isGenerating: true, streamingAssistantPreview: "", error: null })

    try {
      let detail: ConversationDetail
      let run: RunDetail
      // Optimistic append of user message
      const optimisticUserMsg: ConversationMessage = {
        message_id: 'temp-' + Date.now(),
        conversation_id: activeConversationId || 'temp',
        role: 'user',
        content: question,
        run_id: null,
        parent_message_id: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      if (!activeConversationId) {
        set({ activeConversationParams: {
          conversation_id: 'temp',
          title: 'New Chat',
          latest_message_preview: question,
          latest_run_status: 'queued',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          messages: [optimisticUserMsg],
          runs: []
        }})
        const [d, r] = await startConversation(question)
        detail = d
        run = r
        set({ activeConversationId: detail.conversation_id })
        await get().loadConversations()
      } else {
        const currentMessages = activeConversationParams?.messages || []
        set({ activeConversationParams: {
          ...activeConversationParams!,
          messages: [...currentMessages, optimisticUserMsg]
        }})

        const [d, r] = await continueConversation(activeConversationId, question)
        detail = d
        run = r
      }

      set({ activeConversationParams: detail, streamingRunId: run.run_id })

      subscribeToRunEvents(run.run_id, (ev) => {
        if (ev.data?.assistant_message?.content) {
           set({ streamingAssistantPreview: ev.data.assistant_message.content })
        }

        if (ev.type === 'run.completed' || ev.type === 'run.failed' || ev.type === 'run.interrupted') {
           set({ isGenerating: false, streamingRunId: null })
           if (detail.conversation_id) {
             get().loadConversation(detail.conversation_id)
             get().loadConversations()
           }
        }
      }, (err) => {
         const message = err instanceof Error ? err.message : 'Connection error'
         console.error('SSE Error:', err)
         set({ isGenerating: false, streamingRunId: null, error: message })
      })

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to send message'
      console.error('Failed to send:', err)
      set({ isGenerating: false, error: message })
    }
  }
}))

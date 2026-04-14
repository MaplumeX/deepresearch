# State Management

> How state is managed in this project.

---

## Overview

We use **Zustand** as our primary state management solution to handle both global conversation state and Server-Sent Events (SSE) streaming updates efficiently without complex cache patching overhead. 

---

## State Categories

- **Local state**: Transient form edits (e.g. `ChatInput` textarea value) and local UI variants.
- **URL state**: Not actively used in the current SPA design, conversation ID is managed globally inside the active store context.
- **Server state / Realtime state**: Conversation list, active conversation messages, and real-time SSE streaming are managed collectively inside the Zustand store (`useChatStore`).

---

## When to Use Global State

- All backend data (conversations list, active conversation details, current streaming previews) are centrally managed in `useChatStore`.
- Use local `useState` only for purely UI-bound interactions like input tracking or temporary UI toggling.
- Avoid building multiple client-side caches; the discrete Zustand store acts as the single source of truth for the active session.

---

## Server State & Realtime (Zustand + SSE)

- The Zustand store exposes explicit methods (`loadConversations`, `loadConversation`, `sendMessage`) that internally consume network utilities from `src/lib/api.ts`.
- SSE events are tied directly to the conversation mutation methods. When `sendMessage` executes, it immediately connects an `EventSource` to patch the store's `streamingAssistantPreview` reactive state.
- Upon SSE reaching terminal limits (`completed`, `failed`, `interrupted`), the SSE subscription is locally closed, and the store dispatches a definitive reload of the conversation detail to lock in the final markdown.

---

## Common Mistakes

- **Memory Leaks / Stuck state**: Forgetting to unsubscribe from SSE when unmounting or switching streams - currently handled automatically within the `sendMessage` scope closure.
- **Unwrapping Errors**: FastAPI endpoints typically wrap domain objects in response models (e.g., `{"conversations": [...]}` instead of `[...]`). Direct mapping over the raw JSON without extracting the inner array will crash the UI. `src/lib/api.ts` always unpacks these responses first.

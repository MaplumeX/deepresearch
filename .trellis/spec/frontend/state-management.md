# State Management

> How state is managed in this project.

---

## Overview

We use **Zustand** as our primary state management solution to handle both global conversation state and Server-Sent Events (SSE) streaming updates efficiently without complex cache patching overhead. 

---

## State Categories

- **Local state**: Transient form edits (e.g. `ChatInput` textarea value) and local UI variants.
- **URL state**: Not actively used in the current SPA design, conversation ID is managed globally inside the active store context.
- **Server state / Realtime state**: Conversation list, active conversation messages, persisted run progress history, and real-time SSE streaming are managed collectively inside the Zustand store (`useChatStore`).

## Conversation Mode Semantics

- `chat` is the default draft mode for a new conversation.
- `research` is an explicit draft mode toggled from the composer button, not a separate route.
- Once a conversation is created, `conversation.mode` becomes the source of truth and must not be mutated in-place from the frontend.
- Existing `research` conversations keep the Deep Research button selected. Clicking the selected button opens a confirmation dialog and, on confirm, returns to the new-chat draft state.
- Existing `chat` conversations hide the Deep Research button. Users must return to the new-chat state before enabling research for the next session.

---

## When to Use Global State

- All backend data (conversations list, active conversation details, current streaming previews) are centrally managed in `useChatStore`.
- Use local `useState` only for purely UI-bound interactions like input tracking or temporary UI toggling.
- Avoid building multiple client-side caches; the discrete Zustand store acts as the single source of truth for the active session.

---

## Server State & Realtime (Zustand + SSE)

- The Zustand store exposes explicit methods (`loadConversations`, `loadConversation`, `sendMessage`) that internally consume network utilities from `src/lib/api.ts`.
- Conversation creation and follow-up both go through the unified `/api/conversations` boundary. `sendMessage` decides the request payload from the active conversation mode or draft mode, not from separate per-mode page routes.
- SSE endpoints remain mode-specific because the runtime objects are different: research uses `/api/research/runs/{run_id}/events`, chat uses `/api/chat/turns/{turn_id}/events`.
- Only one active stream may exist at a time. Switching conversations or returning to the new-chat state must close the previous stream before updating local state.
- Upon SSE reaching terminal limits (`completed`, `failed`, `interrupted`), the SSE subscription is locally closed, and the store dispatches a definitive reload of the conversation detail to lock in the final assistant message.
- Research-mode live state is split into two layers:
  - persisted `conversation.runs[*].progress_events` for static replay when reopening history
  - ephemeral `streamingProgress` / `streamingRunEvents` for the currently active SSE stream before the terminal reload lands
- Research progress cards are run-scoped UI blocks rendered from `message.run_id`; do not flatten progress into ad-hoc per-message local state.

---

## UI Global State

- UI-specific global state (theme, sidebar collapse, etc.) is stored in a dedicated Zustand store (`src/store/useUiStore.ts`) to keep it separate from conversation/server state.
- UI state that should survive refreshes is persisted to `localStorage`.
- Theme initialization runs **before** React mounts (in `src/main.tsx`) to prevent a flash of the wrong theme.

## Common Mistakes

- **Memory Leaks / Stuck state**: Forgetting to unsubscribe from SSE when unmounting or switching streams - currently handled automatically within the `sendMessage` scope closure.
- **Unwrapping Errors**: FastAPI endpoints typically wrap domain objects in response models (e.g., `{"conversations": [...]}` instead of `[...]`). Direct mapping over the raw JSON without extracting the inner array will crash the UI. `src/lib/api.ts` always unpacks these responses first.
- **Mode Drift**: Treating the composer button as a live mode switch for an existing conversation will corrupt API routing and user expectations. The button only changes draft mode before the first send; after that, the backend conversation mode wins.
- **Theme Flash**: Initializing the theme class inside a React effect causes a visible flash on refresh. Always apply the theme class to `document.documentElement` before `createRoot(...).render()`.

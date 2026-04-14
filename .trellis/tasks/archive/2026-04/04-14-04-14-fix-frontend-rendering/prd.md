# Fix Frontend Rendering and UX Issues

## Goal
Fix critical frontend rendering bugs and UX issues in the ChatGPT-style research web interface.

## Issues Identified

### 1. Markdown Not Rendered (Critical)
- **Problem**: Assistant messages contain markdown (headings, lists, code blocks, links, tables) but `ChatArea.tsx` renders them as plain text via `whitespace-pre-wrap`.
- **Impact**: Reports are unreadable. Code blocks appear as plain text. Lists have no formatting. Links are not clickable.
- **Fix**: Integrate `react-markdown` + `remark-gfm` with Tailwind-styled prose output.

### 2. New Chat Missing from Sidebar During Run
- **Problem**: When a user starts a new conversation, `loadConversations()` is not called after the API returns the real conversation ID. The sidebar only refreshes when the research run completes.
- **Impact**: User sees "New Chat" in the main area but the sidebar conversation list does not include it.
- **Fix**: Call `loadConversations()` immediately after receiving the conversation detail from `startConversation()`.

### 3. No Error Feedback in UI
- **Problem**: API/network errors in `useChatStore` are only `console.error`. Users see no feedback when a message fails to send or a conversation fails to load.
- **Impact**: Users think the app is frozen when requests fail.
- **Fix**: Add a lightweight error state to the chat store and display error toasts/banners in the UI.

### 4. Streaming Preview Resets on Empty Events
- **Problem**: The SSE handler updates `streamingAssistantPreview` with `ev.data.assistant_message.content`. Early events include the assistant message but with empty content, which overwrites any accumulated preview.
- **Impact**: Brief flickers or empty preview during streaming.
- **Fix**: Only update `streamingAssistantPreview` when `content` is non-empty, or rely on `run.completed` reload.

### 5. Leftover Demo CSS
- **Problem**: `App.css` contains unused Vite demo styles (`.hero`, `#next-steps`, etc.).
- **Fix**: Remove unused `App.css` styles or delete the file entirely since it is not imported.

## Acceptance Criteria
- [x] Assistant messages render markdown correctly (headings, lists, code blocks, inline code, links, blockquotes, tables).
- [x] Code blocks have syntax highlighting background and copy-friendly styling.
- [x] New conversation appears in sidebar immediately after first message is sent.
- [x] Users see a visible error message when send/load operations fail.
- [x] Streaming preview is stable (no empty-content resets).
- [x] Build and lint pass.

## Technical Notes
- Add dependencies: `react-markdown`, `remark-gfm`.
- Style markdown with Tailwind classes (prose-like but custom to match current dark/light theme).
- Keep changes minimal; do not refactor architecture beyond what is needed to fix these issues.

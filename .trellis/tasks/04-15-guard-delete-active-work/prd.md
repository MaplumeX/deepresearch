# Guard Conversation Delete For Active Work

## Goal
Prevent conversation deletion from removing rows that are still referenced by in-flight research runs or chat turns.

## Requirements
- Reject `DELETE /api/conversations/{conversation_id}` when the conversation still has `research_runs` in `queued` or `running`.
- Reject `DELETE /api/conversations/{conversation_id}` when the conversation still has `chat_turns` in `queued` or `running`.
- Keep the existing successful delete behavior for idle conversations.

## Acceptance Criteria
- [ ] Deleting a conversation with an active research run returns `409`.
- [ ] Deleting a conversation with an active chat turn returns `409`.
- [ ] Deleting an idle conversation still returns `200` and removes the conversation.

## Technical Notes
- Add the active-work check at the API entry point so background managers never lose their backing rows mid-flight.
- Keep the implementation minimal: detect and reject first, do not introduce cancellation behavior in this change.

import type {
  ConversationMessage,
  ResearchConversationDetail,
  ResearchConversationSummary,
  ResearchRun,
} from "../types/research";


export function toConversationSummary(
  conversation: ResearchConversationDetail | ResearchConversationSummary,
): ResearchConversationSummary {
  if ("messages" in conversation) {
    const { messages: _, runs: __, ...summary } = conversation;
    return summary;
  }
  return conversation;
}

export function upsertConversationSummary(
  conversations: ResearchConversationSummary[] | undefined,
  nextConversation: ResearchConversationDetail | ResearchConversationSummary,
): ResearchConversationSummary[] {
  const summary = toConversationSummary(nextConversation);
  const current = conversations ?? [];
  const filtered = current.filter((item) => item.conversation_id !== summary.conversation_id);
  return [summary, ...filtered].sort((left, right) => right.updated_at.localeCompare(left.updated_at));
}

export function upsertConversationRun(
  conversation: ResearchConversationDetail,
  nextRun: ResearchRun,
): ResearchConversationDetail {
  const runs = [...conversation.runs.filter((run) => run.run_id !== nextRun.run_id), nextRun].sort((left, right) =>
    left.created_at.localeCompare(right.created_at),
  );
  const latestRun = runs[runs.length - 1] ?? null;
  return {
    ...conversation,
    latest_run_status: latestRun?.status ?? conversation.latest_run_status,
    updated_at: latestRun?.updated_at ?? conversation.updated_at,
    runs,
  };
}

export function upsertConversationMessage(
  conversation: ResearchConversationDetail,
  nextMessage: ConversationMessage,
): ResearchConversationDetail {
  const messages = [...conversation.messages.filter((message) => message.message_id !== nextMessage.message_id), nextMessage].sort(
    (left, right) => left.created_at.localeCompare(right.created_at),
  );
  const preview = findLatestPreview(messages) ?? conversation.title;
  return {
    ...conversation,
    latest_message_preview: preview,
    updated_at: nextMessage.updated_at,
    messages,
  };
}

export function latestConversationRun(conversation: ResearchConversationDetail | undefined): ResearchRun | null {
  if (!conversation || conversation.runs.length === 0) {
    return null;
  }
  return conversation.runs[conversation.runs.length - 1] ?? null;
}

function findLatestPreview(messages: ConversationMessage[]): string | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const content = messages[index]?.content.trim();
    if (content) {
      return content.slice(0, 140);
    }
  }
  return null;
}

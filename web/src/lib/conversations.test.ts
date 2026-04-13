import { describe, expect, it } from "vitest";

import {
  latestConversationRun,
  upsertConversationMessage,
  upsertConversationRun,
  upsertConversationSummary,
} from "./conversations";
import type { ConversationMessage, ResearchConversationDetail, ResearchRun } from "../types/research";


const baseRun: ResearchRun = {
  run_id: "run-1",
  conversation_id: "conversation-1",
  origin_message_id: "message-1",
  assistant_message_id: "message-2",
  parent_run_id: null,
  status: "completed",
  request: {
    question: "Question",
    output_language: "zh-CN",
    max_iterations: 2,
    max_parallel_tasks: 3,
  },
  result: {
    final_report: "# Final",
  },
  warnings: [],
  error_message: null,
  created_at: "2026-04-13T08:00:00+00:00",
  updated_at: "2026-04-13T08:10:00+00:00",
  completed_at: "2026-04-13T08:10:00+00:00",
};

const assistantMessage: ConversationMessage = {
  message_id: "message-2",
  conversation_id: "conversation-1",
  role: "assistant",
  content: "# Final",
  run_id: "run-1",
  parent_message_id: "message-1",
  created_at: "2026-04-13T08:00:00+00:00",
  updated_at: "2026-04-13T08:10:00+00:00",
};

const baseConversation: ResearchConversationDetail = {
  conversation_id: "conversation-1",
  title: "Question",
  latest_message_preview: "# Final",
  latest_run_status: "completed",
  created_at: "2026-04-13T08:00:00+00:00",
  updated_at: "2026-04-13T08:10:00+00:00",
  messages: [
    {
      message_id: "message-1",
      conversation_id: "conversation-1",
      role: "user",
      content: "Question",
      run_id: "run-1",
      parent_message_id: null,
      created_at: "2026-04-13T08:00:00+00:00",
      updated_at: "2026-04-13T08:00:00+00:00",
    },
    assistantMessage,
  ],
  runs: [baseRun],
};

describe("conversation utilities", () => {
  it("upserts summaries by updated_at", () => {
    const updated = upsertConversationSummary(
      [baseConversation],
      {
        ...baseConversation,
        conversation_id: "conversation-2",
        title: "Second",
        latest_message_preview: "Second",
        updated_at: "2026-04-13T09:00:00+00:00",
      },
    );

    expect(updated[0].conversation_id).toBe("conversation-2");
  });

  it("updates run and assistant message in conversation cache", () => {
    const nextRun: ResearchRun = {
      ...baseRun,
      status: "running",
      updated_at: "2026-04-13T08:12:00+00:00",
      completed_at: null,
    };
    const nextMessage: ConversationMessage = {
      ...assistantMessage,
      content: "",
      updated_at: "2026-04-13T08:12:00+00:00",
    };

    const withRun = upsertConversationRun(baseConversation, nextRun);
    const withMessage = upsertConversationMessage(withRun, nextMessage);

    expect(withMessage.runs[0].status).toBe("running");
    expect(withMessage.messages[1].content).toBe("");
    expect(withMessage.updated_at).toBe("2026-04-13T08:12:00+00:00");
  });

  it("returns the latest run", () => {
    expect(latestConversationRun(baseConversation)?.run_id).toBe("run-1");
  });
});

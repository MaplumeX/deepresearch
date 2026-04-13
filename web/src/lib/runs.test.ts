import { describe, expect, it } from "vitest";

import { eventMessage, isTerminalStatus, upsertRunSummary } from "./runs";
import type { ResearchRun, ResearchRunEvent } from "../types/research";

const baseRun: ResearchRun = {
  run_id: "run-1",
  conversation_id: "conversation-1",
  origin_message_id: "message-1",
  assistant_message_id: "message-2",
  parent_run_id: null,
  status: "running",
  request: {
    question: "Question",
    output_language: "zh-CN",
    max_iterations: 2,
    max_parallel_tasks: 3,
  },
  result: null,
  warnings: [],
  error_message: null,
  created_at: "2026-04-13T08:00:00+00:00",
  updated_at: "2026-04-13T08:10:00+00:00",
  completed_at: null,
};

describe("run utilities", () => {
  it("upserts latest summary to the front", () => {
    const runs = upsertRunSummary([], baseRun);
    const updated = upsertRunSummary(runs, {
      ...baseRun,
      status: "completed",
      updated_at: "2026-04-13T08:20:00+00:00",
    });

    expect(updated).toHaveLength(1);
    expect(updated[0].status).toBe("completed");
    expect(updated[0].updated_at).toBe("2026-04-13T08:20:00+00:00");
  });

  it("detects terminal status", () => {
    expect(isTerminalStatus("completed")).toBe(true);
    expect(isTerminalStatus("failed")).toBe(true);
    expect(isTerminalStatus("running")).toBe(false);
  });

  it("builds human-readable event messages", () => {
    const event: ResearchRunEvent = {
      type: "run.progress",
      run_id: "run-1",
      status: "running",
      timestamp: "2026-04-13T08:15:00+00:00",
      data: {
        message: "Research execution started.",
      },
    };

    expect(eventMessage(event)).toBe("Research execution started.");
  });
});

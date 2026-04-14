import type { ResearchRun, ResearchRunEvent, ResearchRunSummary, RunStatus } from "../types/research";

const terminalStatuses: RunStatus[] = ["completed", "failed"];

export function toRunSummary(run: ResearchRun): ResearchRunSummary {
  return {
    run_id: run.run_id,
    conversation_id: run.conversation_id,
    origin_message_id: run.origin_message_id,
    assistant_message_id: run.assistant_message_id,
    parent_run_id: run.parent_run_id,
    status: run.status,
    request: run.request,
    error_message: run.error_message,
    created_at: run.created_at,
    updated_at: run.updated_at,
    completed_at: run.completed_at,
  };
}

export function upsertRunSummary(
  runs: ResearchRunSummary[] | undefined,
  nextRun: ResearchRun,
): ResearchRunSummary[] {
  const summary = toRunSummary(nextRun);
  const current = runs ?? [];
  const filtered = current.filter((item) => item.run_id !== summary.run_id);
  return [summary, ...filtered].sort((left, right) => right.updated_at.localeCompare(left.updated_at));
}

export function isTerminalStatus(status: RunStatus): boolean {
  return terminalStatuses.includes(status);
}

export function eventMessage(event: ResearchRunEvent): string {
  if (event.data.message) {
    return event.data.message;
  }

  switch (event.type) {
    case "run.created":
      return "Run 已创建";
    case "run.status_changed":
      return `状态更新为 ${event.status}`;
    case "run.interrupted":
      return "等待人工审核";
    case "run.completed":
      return "研究已完成";
    case "run.failed":
      return "研究执行失败";
    case "run.resumed":
      return "人工审核已提交，继续执行";
    default:
      return "收到实时更新";
  }
}

import ReactMarkdown from "react-markdown";

import { formatDateTime } from "../lib/format";
import { StatusPill } from "./StatusPill";
import { ReviewPanel } from "./ReviewPanel";
import type {
  ResearchConversationDetail,
  ResearchRun,
  ResumeRequest,
} from "../types/research";


interface EventLogEntry {
  id: string;
  message: string;
  timestamp: string;
}

interface ConversationThreadProps {
  conversation: ResearchConversationDetail;
  activeRunId: string | null;
  events: EventLogEntry[];
  streamState: "idle" | "connecting" | "open" | "error";
  isSubmittingReview: boolean;
  onSubmitReview: (runId: string, payload: ResumeRequest) => void;
}

export function ConversationThread({
  conversation,
  activeRunId,
  events,
  streamState,
  isSubmittingReview,
  onSubmitReview,
}: ConversationThreadProps) {
  const runsById = new Map(conversation.runs.map((run) => [run.run_id, run]));

  return (
    <div className="thread-timeline">
      {conversation.messages.map((message) => {
        const run = message.run_id ? runsById.get(message.run_id) ?? null : null;
        const isActiveRun = Boolean(run && activeRunId === run.run_id);

        if (message.role === "user") {
          return (
            <article key={message.message_id} className="thread-entry thread-entry-user">
              <div className="thread-entry-body">
                <header className="thread-entry-header">
                  <span>你</span>
                  <time>{formatDateTime(message.created_at)}</time>
                </header>
                <div className="thread-entry-content">
                  <p className="user-message-text">{message.content}</p>
                  {run?.request.scope ? <p className="user-message-scope">范围：{run.request.scope}</p> : null}
                </div>
              </div>
            </article>
          );
        }

        return (
          <article key={message.message_id} className="thread-entry thread-entry-assistant">
            <div className="thread-entry-body">
              <header className="thread-entry-header">
                <span>Deep Research</span>
                <div className="thread-entry-status">
                  {run ? <StatusPill status={run.status} /> : null}
                  <time>{formatDateTime(message.updated_at)}</time>
                </div>
              </header>

              <div className="thread-entry-content">
                {renderAssistantContent(message.content, run)}

                {run?.warnings.length ? (
                  <section className="thread-warning-block">
                    <h3>警告</h3>
                    <ul>
                      {run.warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  </section>
                ) : null}

                {isActiveRun ? (
                  <section className="thread-activity" aria-live="polite">
                    <div className="thread-activity-header">
                      <strong>实时进展</strong>
                      <span>{streamStateLabel(streamState)}</span>
                    </div>
                    {events.length === 0 ? (
                      <p className="thread-activity-empty">等待新的事件推送。</p>
                    ) : (
                      <ol className="thread-activity-list">
                        {events.map((event) => (
                          <li key={event.id}>
                            <strong>{event.message}</strong>
                            <span>{formatDateTime(event.timestamp)}</span>
                          </li>
                        ))}
                      </ol>
                    )}
                  </section>
                ) : null}

                {run?.status === "interrupted" ? (
                  <ReviewPanel
                    draftReport={message.content}
                    isSubmitting={isSubmittingReview}
                    onSubmit={(editedReport) =>
                      onSubmitReview(run.run_id, {
                        approved: true,
                        edited_report: editedReport,
                      })
                    }
                  />
                ) : null}
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function renderAssistantContent(content: string, run: ResearchRun | null) {
  if (run?.status === "failed") {
    return <div className="thread-error-block">{run.error_message ?? "研究执行失败。"}</div>;
  }
  if (!content.trim()) {
    return <p className="thread-placeholder">{placeholderForStatus(run?.status)}</p>;
  }
  return (
    <div className="thread-markdown">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}

function placeholderForStatus(status?: ResearchRun["status"]) {
  if (status === "queued") {
    return "研究任务已经创建，等待执行。";
  }
  if (status === "running") {
    return "正在整理资料并生成研究结果。";
  }
  if (status === "interrupted") {
    return "研究已暂停，等待人工审核。";
  }
  return "等待内容。";
}

function streamStateLabel(streamState: "idle" | "connecting" | "open" | "error") {
  const labels = {
    idle: "已停止",
    connecting: "连接中",
    open: "实时同步中",
    error: "连接异常",
  };
  return labels[streamState];
}

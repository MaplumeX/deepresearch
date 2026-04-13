import { Link, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";

import { formatDateTime } from "../lib/format";
import { useRunEvents } from "../hooks/useRunEvents";
import { useResumeRunMutation, useRunQuery } from "../hooks/useResearchRuns";
import { isTerminalStatus } from "../lib/runs";
import { ReviewPanel } from "../components/ReviewPanel";
import { StatusPill } from "../components/StatusPill";

export function RunDetailPage() {
  const { runId = "" } = useParams();
  const runQuery = useRunQuery(runId);
  const resumeMutation = useResumeRunMutation(runId);
  const run = runQuery.data;
  const { events, streamState } = useRunEvents({
    runId,
    status: run?.status ?? "queued",
  });

  if (runQuery.isLoading) {
    return <div className="panel empty-panel">正在加载 run 详情...</div>;
  }

  if (runQuery.isError || !run) {
    return <div className="panel error-panel">无法加载 run 详情。</div>;
  }

  const draftReport = readResultField(run.result, "draft_report");
  const finalReport = readResultField(run.result, "final_report");
  const report = finalReport || draftReport || "当前还没有可展示的报告内容。";
  const warnings = run.warnings ?? [];

  return (
    <div className="page-stack">
      <div className="detail-header">
        <div>
          <Link to="/runs" className="inline-link">
            返回历史记录
          </Link>
          <h2>{run.request.question}</h2>
        </div>
        <StatusPill status={run.status} />
      </div>

      <section className="detail-meta-grid">
        <div className="panel meta-panel">
          <dl className="meta-list">
            <div>
              <dt>创建时间</dt>
              <dd>{formatDateTime(run.created_at)}</dd>
            </div>
            <div>
              <dt>更新时间</dt>
              <dd>{formatDateTime(run.updated_at)}</dd>
            </div>
            <div>
              <dt>输出语言</dt>
              <dd>{run.request.output_language}</dd>
            </div>
            <div>
              <dt>实时连接</dt>
              <dd>{isTerminalStatus(run.status) ? "已结束" : streamLabel(streamState)}</dd>
            </div>
          </dl>
        </div>
        <div className="panel meta-panel">
          <dl className="meta-list">
            <div>
              <dt>迭代轮次</dt>
              <dd>{run.request.max_iterations}</dd>
            </div>
            <div>
              <dt>并行任务</dt>
              <dd>{run.request.max_parallel_tasks}</dd>
            </div>
            <div>
              <dt>范围说明</dt>
              <dd>{run.request.scope || "未设置"}</dd>
            </div>
            <div>
              <dt>完成时间</dt>
              <dd>{formatDateTime(run.completed_at)}</dd>
            </div>
          </dl>
        </div>
      </section>

      {run.error_message ? <div className="panel error-panel">{run.error_message}</div> : null}
      {resumeMutation.isError ? <div className="panel error-panel">提交人工审核失败，请重试。</div> : null}

      {warnings.length > 0 ? (
        <section className="panel warning-panel">
          <div className="section-header">
            <h2>警告</h2>
          </div>
          <ul className="plain-list">
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {run.status === "interrupted" ? (
        <ReviewPanel
          draftReport={draftReport}
          isSubmitting={resumeMutation.isPending}
          onSubmit={(editedReport) =>
            resumeMutation.mutate({
              approved: true,
              edited_report: editedReport,
            })
          }
        />
      ) : null}

      <section className="detail-content-grid">
        <article className="panel report-panel">
          <div className="section-header">
            <h2>研究报告</h2>
          </div>
          <div className="report-markdown">
            <ReactMarkdown>{report}</ReactMarkdown>
          </div>
        </article>
        <aside className="panel activity-panel">
          <div className="section-header">
            <h2>实时活动</h2>
            <p>SSE 会把状态变化和关键阶段追加到这里。</p>
          </div>
          <ul className="event-list">
            {events.length === 0 ? (
              <li className="event-list-empty">等待新的事件推送。</li>
            ) : (
              events.map((event) => (
                <li key={event.id}>
                  <strong>{event.message}</strong>
                  <span>{formatDateTime(event.timestamp)}</span>
                </li>
              ))
            )}
          </ul>
        </aside>
      </section>
    </div>
  );
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function readResultField(result: Record<string, unknown> | null, key: string): string {
  if (!result) {
    return "";
  }
  return asString(result[key]);
}

function streamLabel(streamState: "idle" | "connecting" | "open" | "error") {
  const labels = {
    idle: "未连接",
    connecting: "连接中",
    open: "已连接",
    error: "连接异常",
  };
  return labels[streamState];
}

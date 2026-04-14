import { Link, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";

import { formatDateTime } from "../lib/format";
import { useRunEvents } from "../hooks/useRunEvents";
import { useResumeRunMutation, useRunQuery } from "../hooks/useResearchRuns";
import { isTerminalStatus } from "../lib/runs";
import { ReviewPanel } from "../components/ReviewPanel";
import { StructuredReportView } from "../components/StructuredReportView";
import { StatusPill } from "../components/StatusPill";
import { readReportField, readStructuredReport } from "../lib/report";

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

  const draftReport = readReportField(run.result, "draft_report");
  const finalReport = readReportField(run.result, "final_report");
  const structuredReport = readStructuredReport(run.result);
  const report = finalReport || draftReport || "当前还没有可展示的报告内容。";
  const warnings = run.warnings ?? [];

  return (
    <div className="workspace-page detail-page">
      <header className="workspace-heading detail-heading">
        <div className="detail-heading-body">
          <Link to="/" className="inline-link">
            发起新研究
          </Link>
          <h1>{run.request.question}</h1>
          <p>{describeRunState(run.status, streamState)}</p>
        </div>
        <StatusPill status={run.status} />
      </header>

      {run.error_message ? <div className="panel error-panel">{run.error_message}</div> : null}
      {resumeMutation.isError ? <div className="panel error-panel">提交人工审核失败，请重试。</div> : null}

      <div className="detail-workspace">
        <section className="thread-column">
          <article className="thread-card thread-card-question">
            <div className="thread-card-header">
              <h2>研究问题</h2>
              <span className="thread-meta">{formatDateTime(run.created_at)}</span>
            </div>
            <p className="thread-question">{run.request.question}</p>
            {run.request.scope ? (
              <div className="thread-context">
                <h3>范围说明</h3>
                <p>{run.request.scope}</p>
              </div>
            ) : null}
          </article>

          {warnings.length > 0 ? (
            <section className="thread-card warning-panel">
              <div className="thread-card-header">
                <h2>警告</h2>
              </div>
              <ul className="plain-list">
                {warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </section>
          ) : null}

          <article className="thread-card thread-card-report">
            <div className="thread-card-header">
              <h2>研究报告</h2>
              <span className="thread-meta">{reportVersionLabel(finalReport, draftReport)}</span>
            </div>
            {structuredReport ? (
              <StructuredReportView report={structuredReport} />
            ) : (
              <div className="report-markdown fallback-report">
                <ReactMarkdown>{report}</ReactMarkdown>
              </div>
            )}
          </article>

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
        </section>

        <aside className="detail-sidebar">
          <section className="side-panel">
            <div className="side-panel-header">
              <h2>运行信息</h2>
            </div>
            <dl className="meta-stack">
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
          </section>

          <section className="side-panel">
            <div className="side-panel-header">
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
          </section>
        </aside>
      </div>
    </div>
  );
}

function reportVersionLabel(finalReport: string, draftReport: string): string {
  if (finalReport) {
    return "最终稿";
  }
  if (draftReport) {
    return "草稿";
  }
  return "等待内容";
}

function describeRunState(
  status: "queued" | "running" | "interrupted" | "completed" | "failed",
  streamState: "idle" | "connecting" | "open" | "error",
) {
  if (status === "queued") {
    return "任务已经创建，系统正在排队并准备启动。";
  }
  if (status === "running") {
    return `研究正在执行中，实时连接${streamLabel(streamState)}。`;
  }
  if (status === "interrupted") {
    return "研究已暂停，等待人工审核后继续。";
  }
  if (status === "completed") {
    return "研究已完成，可以直接查看最终报告。";
  }
  return "研究执行失败，请检查错误信息和实时活动。";
}

function streamLabel(streamState: "idle" | "connecting" | "open" | "error") {
  const labels = {
    idle: "已结束",
    connecting: "连接中",
    open: "正常",
    error: "异常",
  };
  return labels[streamState];
}

import { Link, useLocation } from "react-router-dom";

import { formatDateTime } from "../lib/format";
import { StatusPill } from "./StatusPill";
import type { ResearchRunSummary } from "../types/research";

interface RunSummaryTableProps {
  runs: ResearchRunSummary[];
  emptyText: string;
  variant?: "page" | "sidebar";
}

export function RunSummaryTable({ runs, emptyText, variant = "page" }: RunSummaryTableProps) {
  const location = useLocation();

  if (runs.length === 0) {
    return <div className={variant === "sidebar" ? "history-empty" : "panel empty-panel"}>{emptyText}</div>;
  }

  return (
    <div className={variant === "sidebar" ? "history-list history-list-sidebar" : "history-list"}>
      {runs.map((run) => {
        const href = `/runs/${run.run_id}`;
        const isActive = location.pathname === href;

        return (
          <Link
            key={run.run_id}
            to={href}
            aria-current={isActive ? "page" : undefined}
            className={[
              "history-item",
              variant === "sidebar" ? "history-item-sidebar" : "history-item-page",
              isActive ? "is-active" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <div className="history-item-row">
              <strong className="history-item-question">{run.request.question}</strong>
              <StatusPill status={run.status} />
            </div>
            <div className="history-item-meta">
              <span>{run.request.output_language}</span>
              <span>迭代 {run.request.max_iterations}</span>
              <span>并行 {run.request.max_parallel_tasks}</span>
            </div>
            <div className="history-item-footer">
              <span>{formatDateTime(run.updated_at)}</span>
              {variant === "page" ? <span>查看详情</span> : null}
            </div>
          </Link>
        );
      })}
    </div>
  );
}

import { Link } from "react-router-dom";

import { formatDateTime } from "../lib/format";
import { StatusPill } from "./StatusPill";
import type { ResearchRunSummary } from "../types/research";

interface RunSummaryTableProps {
  runs: ResearchRunSummary[];
  emptyText: string;
}

export function RunSummaryTable({ runs, emptyText }: RunSummaryTableProps) {
  if (runs.length === 0) {
    return <div className="panel empty-panel">{emptyText}</div>;
  }

  return (
    <div className="panel table-panel">
      <table className="run-table">
        <thead>
          <tr>
            <th>问题</th>
            <th>状态</th>
            <th>更新时间</th>
            <th aria-label="查看详情" />
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.run_id}>
              <td>
                <strong>{run.request.question}</strong>
                <div className="table-meta">
                  {run.request.output_language} · 迭代 {run.request.max_iterations} · 并行 {run.request.max_parallel_tasks}
                </div>
              </td>
              <td>
                <StatusPill status={run.status} />
              </td>
              <td>{formatDateTime(run.updated_at)}</td>
              <td className="table-action">
                <Link to={`/runs/${run.run_id}`}>查看</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

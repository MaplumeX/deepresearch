import { RunSummaryTable } from "../components/RunSummaryTable";
import { useRunsQuery } from "../hooks/useResearchRuns";

export function RunsPage() {
  const runsQuery = useRunsQuery();

  return (
    <section className="workspace-page">
      <header className="workspace-heading">
        <div>
          <h1>历史记录</h1>
          <p>按最近更新时间倒序展示所有 research run。</p>
        </div>
      </header>
      {runsQuery.isLoading ? <div className="panel empty-panel">正在加载历史记录...</div> : null}
      {runsQuery.isError ? <div className="panel error-panel">历史记录加载失败。</div> : null}
      {!runsQuery.isLoading && !runsQuery.isError ? (
        <RunSummaryTable runs={runsQuery.data ?? []} emptyText="还没有 run 记录。" />
      ) : null}
    </section>
  );
}

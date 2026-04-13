import { RunSummaryTable } from "../components/RunSummaryTable";
import { useRunsQuery } from "../hooks/useResearchRuns";


export function RunsPage() {
  const runsQuery = useRunsQuery();

  return (
    <section className="workspace-screen workspace-screen-runs">
      <header className="screen-header">
        <h1>所有运行</h1>
        <p>按最近更新时间查看所有 research run。旧链接会自动跳转到对应会话。</p>
      </header>

      {runsQuery.isLoading ? <div className="panel-state">正在加载运行记录...</div> : null}
      {runsQuery.isError ? <div className="inline-error">运行记录加载失败。</div> : null}
      {!runsQuery.isLoading && !runsQuery.isError ? (
        <RunSummaryTable runs={runsQuery.data ?? []} emptyText="还没有 run 记录。" />
      ) : null}
    </section>
  );
}

import { useNavigate } from "react-router-dom";

import { RunForm } from "../components/RunForm";
import { RunSummaryTable } from "../components/RunSummaryTable";
import { useCreateRunMutation, useRunsQuery } from "../hooks/useResearchRuns";

export function HomePage() {
  const navigate = useNavigate();
  const createRunMutation = useCreateRunMutation();
  const runsQuery = useRunsQuery();

  return (
    <div className="page-grid">
      <RunForm
        isSubmitting={createRunMutation.isPending}
        onSubmit={(payload) =>
          createRunMutation.mutate(payload, {
            onSuccess: (run) => navigate(`/runs/${run.run_id}`),
          })
        }
      />
      <section className="page-stack">
        <div className="section-header">
          <h2>最近记录</h2>
          <p>这里显示最近创建或更新的 run，方便从首页直接回到详情页。</p>
        </div>
        {createRunMutation.isError ? <div className="panel error-panel">创建 run 失败，请稍后重试。</div> : null}
        {runsQuery.isError ? <div className="panel error-panel">最近记录加载失败。</div> : null}
        {runsQuery.isLoading ? (
          <div className="panel empty-panel">正在加载最近记录...</div>
        ) : (
          <RunSummaryTable runs={(runsQuery.data ?? []).slice(0, 5)} emptyText="还没有研究记录。" />
        )}
      </section>
    </div>
  );
}

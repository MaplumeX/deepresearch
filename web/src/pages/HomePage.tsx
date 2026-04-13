import { useNavigate } from "react-router-dom";

import { RunForm } from "../components/RunForm";
import { useCreateRunMutation } from "../hooks/useResearchRuns";

export function HomePage() {
  const navigate = useNavigate();
  const createRunMutation = useCreateRunMutation();

  return (
    <div className="workspace-page workspace-home">
      <section className="home-stage">
        <div className="home-stage-body">
          <header className="workspace-heading home-heading">
            <div>
              <h1>开始新的研究</h1>
              <p>输入问题并创建 run。系统会直接进入研究工作区，并通过 SSE 持续刷新执行状态。</p>
            </div>
          </header>

          {createRunMutation.isError ? <div className="panel error-panel">创建 run 失败，请稍后重试。</div> : null}

          <RunForm
            isSubmitting={createRunMutation.isPending}
            onSubmit={(payload) =>
              createRunMutation.mutate(payload, {
                onSuccess: (run) => navigate(`/runs/${run.run_id}`),
              })
            }
          />

          <section className="panel home-notes">
            <h2>当前工作流</h2>
            <ul className="plain-list">
              <li>创建成功后会自动跳转到该次研究的工作区。</li>
              <li>实时活动和报告会在详情页持续更新。</li>
              <li>历史记录始终保留在左侧边栏，方便快速切换。</li>
            </ul>
          </section>
        </div>
      </section>
    </div>
  );
}

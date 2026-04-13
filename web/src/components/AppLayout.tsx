import { NavLink, Outlet } from "react-router-dom";

import { useRunsQuery } from "../hooks/useResearchRuns";
import { RunSummaryTable } from "./RunSummaryTable";

export function AppLayout() {
  const runsQuery = useRunsQuery();
  const recentRuns = (runsQuery.data ?? []).slice(0, 8);

  return (
    <div className="workspace-shell">
      <aside className="workspace-sidebar" aria-label="研究导航">
        <div className="sidebar-branding">
          <NavLink to="/" end className="sidebar-brand">
            Deep Research
          </NavLink>
          <p className="sidebar-note">研究工作台</p>
        </div>

        <nav className="sidebar-nav" aria-label="主导航">
          <NavLink to="/" end className={({ isActive }) => navClassName(isActive)}>
            新建研究
          </NavLink>
          <NavLink to="/runs" end className={({ isActive }) => navClassName(isActive)}>
            历史记录
          </NavLink>
        </nav>

        <section className="sidebar-section">
          <div className="sidebar-section-header">
            <h2>最近记录</h2>
          </div>
          {runsQuery.isLoading ? <div className="sidebar-feedback">正在加载历史记录...</div> : null}
          {runsQuery.isError ? <div className="sidebar-feedback sidebar-feedback-error">历史记录加载失败。</div> : null}
          {!runsQuery.isLoading && !runsQuery.isError ? (
            <RunSummaryTable runs={recentRuns} emptyText="暂无研究记录。" variant="sidebar" />
          ) : null}
        </section>
      </aside>

      <div className="workspace-main">
        <main className="workspace-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function navClassName(isActive: boolean) {
  return isActive ? "sidebar-link is-active" : "sidebar-link";
}

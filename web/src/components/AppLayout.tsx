import { NavLink, Outlet } from "react-router-dom";

import { useConversationsQuery } from "../hooks/useConversations";
import { ConversationList } from "./ConversationList";


export function AppLayout() {
  const conversationsQuery = useConversationsQuery();

  return (
    <div className="app-shell">
      <aside className="app-sidebar" aria-label="会话导航">
        <div className="sidebar-branding">
          <NavLink to="/" end className="sidebar-brand">
            Deep Research
          </NavLink>
          <p>会话式研究工作台</p>
        </div>

        <nav className="sidebar-actions" aria-label="主导航">
          <NavLink to="/" end className={({ isActive }) => navClassName(isActive)}>
            新建会话
          </NavLink>
          <NavLink to="/runs" end className={({ isActive }) => navClassName(isActive)}>
            所有运行
          </NavLink>
        </nav>

        <section className="sidebar-section">
          <div className="sidebar-section-header">
            <h2>最近会话</h2>
          </div>
          {conversationsQuery.isLoading ? <div className="sidebar-feedback">正在加载会话...</div> : null}
          {conversationsQuery.isError ? <div className="sidebar-feedback sidebar-feedback-error">会话加载失败。</div> : null}
          {!conversationsQuery.isLoading && !conversationsQuery.isError ? (
            <ConversationList conversations={conversationsQuery.data ?? []} emptyText="还没有研究会话。" />
          ) : null}
        </section>
      </aside>

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

function navClassName(isActive: boolean) {
  return isActive ? "sidebar-link is-active" : "sidebar-link";
}

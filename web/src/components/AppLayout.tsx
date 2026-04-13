import { NavLink, Outlet } from "react-router-dom";

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <h1 className="topbar-title">Deep Research 运行台</h1>
        <nav className="topbar-nav" aria-label="主导航">
          <NavLink to="/" end className={({ isActive }) => navClassName(isActive)}>
            新建研究
          </NavLink>
          <NavLink to="/runs" className={({ isActive }) => navClassName(isActive)}>
            历史记录
          </NavLink>
        </nav>
      </header>
      <main className="page-shell">
        <Outlet />
      </main>
    </div>
  );
}

function navClassName(isActive: boolean) {
  return isActive ? "topbar-link is-active" : "topbar-link";
}

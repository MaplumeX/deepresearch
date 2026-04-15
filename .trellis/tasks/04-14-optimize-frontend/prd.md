# 优化前端页面

## Goal
提升前端用户体验，添加深色/浅色主题切换和 Sidebar 可折叠功能。

## Requirements

### 1. 深色/浅色主题切换
- 在页面中添加主题切换按钮（优先放在 Sidebar 底部或顶部）
- 支持 `light`、`dark` 两种模式
- 默认跟随系统偏好，用户切换后持久化到 `localStorage`
- 使用 Tailwind 的 `dark` class 策略（已在 tailwind.config.js 中配置）
- 切换时无闪烁，主题变量正确应用到全页面

### 2. Sidebar 可折叠
- 点击 Sidebar 顶部的 `PanelLeftClose` 按钮可以收起 Sidebar
- Sidebar 收起后，在主内容区左上角显示一个悬浮/固定的展开按钮（或汉堡菜单按钮）
- 展开按钮点击后恢复 Sidebar
- 过渡动画平滑（`transition-all duration-300`）
- 折叠状态持久化到 `localStorage`（可选，视实现复杂度决定）
- 折叠后宽度变为 0，不残留可见内容

## Acceptance Criteria
- [ ] 页面出现主题切换按钮，点击可在 light/dark 间切换
- [ ] 刷新页面后仍保持用户上次选择的主题
- [ ] 系统主题变更时，若用户未手动设置则自动跟随（初始化时）
- [ ] 点击 Sidebar 收起按钮后 Sidebar 平滑收起
- [ ] 收起后显示展开按钮，点击可恢复 Sidebar
- [ ] `npm run lint` 通过
- [ ] 现有功能（聊天、研究会话切换等）不受影响

## Technical Notes
- 当前 tailwind 已配置 `darkMode: ["class"]`，CSS 变量已定义 `.dark`
- 项目使用 `zustand` 作为状态管理，主题/折叠状态可用 zustand + localStorage 或纯 React hook
- 已有 `lucide-react` 图标库可用（Sun / Moon / PanelLeftClose / PanelLeft 等）
- 工作区有 6 个未提交更改，需注意不破坏其功能

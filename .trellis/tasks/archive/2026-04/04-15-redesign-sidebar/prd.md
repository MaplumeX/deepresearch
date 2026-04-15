# 重构前端侧边栏（方案 B）

## Goal
重新设计前端侧边栏，提升信息架构清晰度、交互体验和视觉一致性，使其符合现代 AI 聊天应用的交互惯例。

## Requirements

### 1. 动画与折叠行为
- 侧边栏展开/收起必须有平滑的 CSS 过渡动画（`transform` 或 `width` 动画）
- 折叠后不再直接 `return null`，而是渲染为一个窄边栏（icon-only rail），保留 "New chat" 和主题切换的入口图标
- 主内容区域（`main`）需同步平滑过渡

### 2. 会话分区与置顶
- 在 `ConversationSummary` 类型中增加 `is_pinned: boolean` 字段
- 后端 API 返回的会话列表需支持 `is_pinned`（如后端尚未支持，先在前端用本地状态兼容）
- 侧边栏会话列表分为两个区域：
  - **Pinned**（置顶会话，固定在最上方，空时隐藏该区域标题）
  - **Recent**（其余会话，按时间倒序）
- 置顶/取消置顶操作通过 `DropdownMenu` 的菜单项触发

### 3. 搜索过滤
- 在会话列表顶部增加搜索输入框，支持按会话标题实时过滤
- 过滤时对 Pinned 和 Recent 两个区域同时生效
- 空结果时显示友好提示

### 4. 状态增强
- Research 模式会话使用左侧色条或不同图标进行明显标识
- 如果 `latest_run_status` 为 `running` 或 `queued`，在会话项右侧显示一个 loading spinner 或脉冲状态点

### 5. 组件化拆分
- `Sidebar` 作为容器组件
- 拆分为：`SidebarHeader`、`SidebarRail`、`ConversationList`、`ConversationItem`、`SidebarFooter`
- 将现有手写菜单替换为 `shadcn/ui` 的 `DropdownMenu`

### 6. 空状态
- 当没有任何会话时，显示空状态占位图和引导文案

## Acceptance Criteria
- [ ] 侧边栏展开/收起有平滑过渡动画
- [ ] 折叠后显示窄边栏 rail，保留核心操作入口
- [ ] 会话列表按 Pinned / Recent 分区展示
- [ ] 支持置顶/取消置顶操作
- [ ] 支持按标题搜索过滤会话
- [ ] Research 会话有明显视觉标识，运行中会话有状态指示
- [ ] 空状态友好提示
- [ ] 使用 `DropdownMenu` 替代手写菜单
- [ ] 组件拆分合理，代码可读性提升
- [ ] `npm run lint` 和 `npm run typecheck` 通过

## Technical Notes
- 状态管理：继续使用 `useUiStore` 控制折叠状态，使用 `useChatStore` 管理会话数据
- 样式：使用 Tailwind CSS 工具类，保持与现有 Shadcn/UI 风格一致
- 动画：优先使用 `transform` 和 `transition`，避免触发重排的性能问题
- 类型：如后端 API 暂未返回 `is_pinned`，先在前端兼容（默认为 `false`）

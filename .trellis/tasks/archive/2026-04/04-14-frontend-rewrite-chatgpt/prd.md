# 04-14-frontend-rewrite-chatgpt

## Goal
完全重写当前前端，仿照 ChatGPT 的 UI/UX 体验，放弃复用现有的前端组件，使用全新、极简且高级的设计方案。

## Requirements
* 清空并重建 `web/` 目录。
* 技术栈：Vite + React + TailwindCSS v3 + shadcn-ui + TypeScript。
* 核心布局体系（ChatGPT风格）：
  * 侧边栏（ Sidebar ）：展示历史记录，支持深色交互，支持折叠展开。
  * 聊天区（ Main Chat Area ）：消息流水展示，具备动态气泡。
  * 输入区（ Input Area ）：处于底部悬浮状态，支持多行文本，以及优质的发光/边框微交互。
* 全新开发，坚决不复用旧版遗留的任何业务组件。

## Acceptance Criteria
* [ ] 成功搭建 Vite + React 代码结构。
* [ ] 集成 Tailwind v3 以及 shadcn/ui。
* [ ] 完成侧边栏和主对话界面的基础响应式 UI。
* [ ] 主流深/浅色模式基础架构落版。

## Definition of Done
* Lint / TypeCheck 完全通过。
* 项目可本地 `npm run dev` 启动，视觉效果符合现代（Premium）规范。

## Technical Approach
清除现有 `web` 目录内容后，重新用 Vite 初始化。然后配置基于 TailwindCSS v3 的环境。
通过 `npx shadcn-ui@latest init` 配置系统，组装 Sidebar 等 Layout 控制器。

## Decision (ADR-lite)
**Context**: 确定前端的基础框架与其样式支撑底座。
**Decision**: 选用 Vite + React + TailwindCSS v3 + shadcn/ui。
**Consequences**: 确保了最为稳固的生态和开发速度。我们能够毫无风险地引入任何复杂的由 shadcn 官方或各种 UI 专家调优过的精美组件库素材。

## Out of Scope
* 进行实际的后端 API 对接（本任务聚焦在 UI 搭设阶段，Mock 数据跑通样式即可）。

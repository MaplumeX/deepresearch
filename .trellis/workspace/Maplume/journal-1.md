# Journal - Maplume (Part 1)

> AI development session journal
> Started: 2026-04-13

---



## Session 1: Scaffold Python deep research agent runtime

**Date**: 2026-04-13
**Task**: Scaffold Python deep research agent runtime
**Branch**: `master`

### Summary

Built the initial Python LangGraph/LangChain deep research backend scaffold with OpenAI-compatible model configuration, API endpoints, tests, and backend code-spec updates.

### Main Changes

| Area | Details |
|------|---------|
| Backend Scaffold | Added `app/` package with config, domain models, LangGraph state, nodes, services, tools, runtime, and FastAPI entrypoints |
| Runtime Flow | Implemented planning, dispatch, research worker, merge, gap check, synthesis, audit, review, and finalize stages |
| Model Access | Added OpenAI-compatible configuration via `LLM_BASE_URL` and `LLM_API_KEY`, with fallback aliases for OpenAI env names |
| Tooling | Added search, fetch, and extraction boundaries for the research worker scaffold |
| Verification | Added unit tests for citations, dedupe, gap detection, planning fallback, and config resolution |
| Documentation | Added `.env.example`, startup instructions in `README.md`, and executable backend spec docs |

**Validation**:
- `python3 -m compileall app tests`
- `python3 -m unittest discover -s tests/unit` (`OK`, 2 skipped)

**Notes**:
- Task archived after code commit because the scaffold scope and acceptance criteria were completed.
- Manual smoke test and dependency installation remain future follow-up work.


### Git Commits

| Hash | Message |
|------|---------|
| `5433f8e` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 2: 前端 UI 优化：主题切换与 Sidebar 折叠

**Date**: 2026-04-15
**Task**: 前端 UI 优化：主题切换与 Sidebar 折叠
**Branch**: `master`

### Summary

新增深色/浅色主题切换和 Sidebar 可折叠功能。使用 Zustand 管理 UI 状态并持久化到 localStorage，主题在 React 渲染前初始化以避免闪烁。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `d0a1df7` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 3: 修复运行中会话删除保护

**Date**: 2026-04-15
**Task**: 修复运行中会话删除保护
**Branch**: `master`

### Summary

为删除会话补上运行中 research/chat 工作的 409 保护，补充 API 回归测试与运行时契约文档，并完成任务归档。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `14e20f4` | (see git log) |
| `d01f39b` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 4: 升级 deep research 事件流显示

**Date**: 2026-04-15
**Task**: 升级 deep research 事件流显示
**Branch**: `master`

### Summary

(Add summary)

### Main Changes

| 领域 | 变更 |
|------|------|
| Backend | 为 research 运行增加结构化 progress 事件、阶段/任务子阶段信息，以及 `research_run_events` 持久化表。 |
| Frontend | 在会话线程中新增 `ResearchProgressCard`，支持 live 进度显示和历史静态回放。 |
| Contracts | 扩展 `RunDetail.progress_events` 和 research SSE `data.progress` 结构，并同步前后端类型。 |
| Spec | 更新 backend runtime、frontend state management、frontend type safety 规范文档。 |

**验证**:
- `uv run ruff check app tests`
- `python3 -m compileall app tests`
- `uv run pytest`
- `npm run lint`
- `npm run build`


### Git Commits

| Hash | Message |
|------|---------|
| `ccafd08` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 5: 重构前端侧边栏（方案B）

**Date**: 2026-04-15
**Task**: 重构前端侧边栏（方案B）
**Branch**: `master`

### Summary

(Add summary)

### Main Changes

## 完成内容

重构了前端侧边栏，实现了方案B的所有核心需求：

- **平滑动画折叠**：侧边栏不再直接卸载，而是缩放到 64px 宽的 icon-only rail，主内容区同步过渡
- **会话分区**：新增 `is_pinned` 字段，侧边栏分为 Pinned / Recent 两个区域
- **搜索过滤**：在会话列表顶部增加搜索框，实时按标题过滤
- **状态增强**：Research 模式会话左侧显示 indigo 色条，运行中/排队状态的会话显示 loading spinner
- **组件化拆分**：拆分为 SidebarHeader、SidebarRail、ConversationList、ConversationItem、SidebarFooter
- **DropdownMenu 替换**：将手写菜单替换为 shadcn/ui 的 DropdownMenu，支持置顶/取消置顶
- **空状态**：无会话和搜索无结果时显示友好提示
- **后端同步**：在 `ResearchConversationSummary` 中暴露 `is_pinned` 字段，API 正确返回

## 变更文件

### 前端
- `web/src/components/Sidebar.tsx`
- `web/src/layouts/MainLayout.tsx`
- `web/src/components/SidebarHeader.tsx` (new)
- `web/src/components/SidebarRail.tsx` (new)
- `web/src/components/SidebarFooter.tsx` (new)
- `web/src/components/ConversationList.tsx` (new)
- `web/src/components/ConversationItem.tsx` (new)
- `web/src/components/ui/dropdown-menu.tsx` (new)
- `web/src/components/ui/tooltip.tsx` (new)
- `web/src/components/ui/separator.tsx` (new)
- `web/src/types/research.ts`
- `web/package.json`

### 后端
- `app/domain/models.py`
- `app/run_store.py`

## 质量检查

- `npm run lint` 通过
- `npm run typecheck` 通过


### Git Commits

| Hash | Message |
|------|---------|
| `0607ca8` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete

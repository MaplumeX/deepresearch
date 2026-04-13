# brainstorm: deep research frontend

## Goal

为当前 `deepresearch` Python/FastAPI 后端补一个基于 React 技术栈的前端页面，用于发起 research run、查看结果、处理中断态人工审核，并为后续扩展成完整 deep research 工作台预留合理演进空间。

## What I already know

* 当前仓库只有 Python 后端，没有现成前端工程、Node 构建配置或 UI 代码。
* 当前公开接口只有 `GET /health`、`POST /api/research/runs`、`POST /api/research/runs/{run_id}/resume`。
* `POST /api/research/runs` 当前是一次性调用，服务端返回时状态只有 `completed` 或 `interrupted`，没有流式进度接口。
* 当图执行进入人工审核节点时，返回结果里会包含 `__interrupt__`，前端需要支持展示 `draft_report`、`warnings` 并提交 resume。
* 运行结果核心数据在图状态里，包括 `tasks`、`findings`、`sources`、`warnings`、`draft_report`、`final_report`。
* 后端当前没有看到 CORS、中间层代理、静态前端托管配置。

## Assumptions (temporary)

* 第一阶段目标应优先聚焦 MVP，而不是一次性做完整多页产品。
* 前端初版更适合做成独立 package，减少对现有 Python 后端结构的侵入。
* TypeScript 应作为默认选择，避免后续前后端契约演进时失控。

## Open Questions

* 无

## Requirements (evolving)

* 前端采用独立 React SPA 形态，作为新 `web/` package 接入现有 FastAPI API。
* 提供一个可输入研究问题和参数的前端页面。
* run 生命周期采用异步创建 + 查询详情/列表模式，而不是同步阻塞请求。
* 支持调用创建 run 接口、查询 run 状态并展示最终结果。
* 支持处理中断态人工审核并恢复 run，恢复后仍可继续通过详情接口查询状态。
* 提供服务端驱动的 run 历史列表或最近记录入口，方便回看最近执行过的 research。
* MVP 必须提供实时状态更新能力，不能仅依赖轮询。
* 界面需要能读懂 Markdown 报告、引用来源和警告信息。
* 技术方案需便于后续扩展到更完整的 research workspace。

## Acceptance Criteria (evolving)

* [ ] 用户可以在页面中提交 `question`、`scope`、`output_language`、`max_iterations`、`max_parallel_tasks`
* [ ] 创建 run 后页面能拿到 `run_id` 并进入详情视图
* [ ] 详情页可以通过实时通道接收状态变化并展示 `queued/running/interrupted/completed/failed`
* [ ] run 完成后，页面可以展示 `final_report` 或 `draft_report`
* [ ] run 被中断时，页面可以展示审核信息并提交 `approved` / `edited_report`
* [ ] 页面可以查看最近的 run 记录，并从记录入口回到对应结果或恢复动作
* [ ] 前端结构能支持后续扩展更多事件类型和多页面导航

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* 本轮不讨论品牌视觉细节和精细 UI 文案
* 本轮不处理用户登录、权限系统、多租户
* 本轮先不做完整研究工作台，不拆成任务面板、证据面板、来源面板的多栏分析视图

## Research Notes

### Constraints from our repo/project

* 后端是 FastAPI + LangGraph，适合先以 HTTP API 方式对接。
* 现有 API 设计偏同步返回，不适合一开始就做复杂实时流 UI。
* 中断恢复是当前工作流的重要分支，前端必须把它当一等场景处理。
* 当前没有前端脚手架，意味着我们可以干净地选择 React 技术栈，但也需要补齐构建、代理、脚本和文档。
* 当前没有 `GET /api/research/runs` 或 `GET /api/research/runs/{run_id}` 之类的查询接口，因此“历史列表”如果要跨刷新、跨设备可靠存在，要么新增后端接口，要么退化为浏览器侧最近记录。
* 用户已选择补服务端历史接口，因此当前任务将扩展为前后端联动，不再局限于纯前端脚手架。
* 用户已选择异步 run 生命周期，因此当前后端接口不应继续把长流程执行绑在单次同步响应上。

### Recommended API Shape

* `POST /api/research/runs`
  * 创建 run，立即返回 `run_id` 与初始状态
* `GET /api/research/runs`
  * 返回 run 列表摘要，供历史页使用
* `GET /api/research/runs/{run_id}`
  * 返回 run 详情，包括状态、请求参数、报告、警告和必要的调试字段
* `GET /api/research/runs/{run_id}/events`
  * 提供 run 实时事件流，向详情页推送状态、阶段与结果更新
* `POST /api/research/runs/{run_id}/resume`
  * 提交人工审核结论，立即返回当前状态，后续由详情接口查询最新状态

### Recommended Run Status

* `queued`
* `running`
* `interrupted`
* `completed`
* `failed`

### Recommended Frontend Route Shape

* `/`
  * 新建 run 表单 + 最近 run 摘要入口
* `/runs`
  * run 历史列表
* `/runs/:runId`
  * run 详情页，包含状态区、报告区、警告区、人工审核区

### Feasible approaches here

**Approach A: Vite + React SPA** (Recommended)

* How it works:
  建一个独立 `web/` 包，使用 React + TypeScript + React Router + TanStack Query；开发期通过 Vite proxy 对接 FastAPI，部署时可分离或编译后再接入托管。
* Pros:
  结构最轻，开发速度快；和当前后端边界清晰；便于先做 MVP，再逐步升级成工作台。
* Cons:
  需要处理 CORS 或 dev proxy；SSR 不存在；如果以后要做 SEO 或复杂服务端编排，需要再演进。

**Approach B: Next.js App Router**

* How it works:
  增加一个 `web/` 的 Next.js 应用，前端通过 server actions / route handlers 代理后端请求。
* Pros:
  后续做流式 UI、服务端渲染、鉴权、BFF 更自然；适合产品继续做大。
* Cons:
  对当前项目来说偏重；会引入更多运行时与部署复杂度；MVP 成本更高。

**Approach C: React SPA + FastAPI Static Hosting**

* How it works:
  前端仍用 React 构建，但最终产物由 FastAPI 统一静态托管，部署成单服务。
* Pros:
  发布链路最简单，适合内部工具；部署统一。
* Cons:
  前后端耦合更高；开发体验和未来拆分灵活性较差；仍需先搭前端构建链路。

## Technical Notes

* Inspected: `README.md`
* Inspected: `pyproject.toml`
* Inspected: `app/main.py`
* Inspected: `app/config.py`
* Inspected: `app/runtime.py`
* Inspected: `app/api/routes.py`
* Inspected: `app/api/schemas.py`
* Inspected: `app/graph/state.py`
* Inspected: `app/graph/nodes/review.py`
* Inspected: `app/graph/nodes/finalize.py`
* Inspected: `app/graph/nodes/audit.py`
* Inspected: `app/services/synthesis.py`
* Inspected: `.trellis/spec/backend/research-agent-runtime.md`

## Decision (ADR-lite)

**Context**: 项目当前只有 Python/FastAPI 后端，没有前端基础设施；需要尽快为 deep research 工作流补齐可用界面，同时尽量降低对现有仓库的侵入。

**Decision**: 前端采用独立 `web/` package 的 React SPA 方案，优先使用 TypeScript，并通过 HTTP API 对接现有 FastAPI 服务。

**Consequences**: 该方案能以最低成本完成 MVP，并保留后续扩展成完整工作台的空间；但初期不具备 SSR/BFF 能力，若未来需要服务端拼装或更复杂部署模型，再评估升级到更重框架。

### Additional Decision

**Context**: MVP 需要 run 历史列表，浏览器本地存储无法满足跨刷新、跨设备或更真实的产品能力。

**Decision**: 历史记录采用服务端接口提供，前端只负责查询与展示。

**Consequences**: 需要新增后端 run 列表/详情能力，并明确结果持久化与状态查询契约；但这样能避免前端后续为“假历史”返工。

### Additional Decision 2

**Context**: deep research 任务可能较长，且 MVP 已明确需要历史列表、详情回看和中断恢复，继续沿用同步阻塞式创建接口会让刷新恢复、失败重试和前端状态管理都变得脆弱。

**Decision**: run 生命周期改为异步创建 + 查询状态/详情模式；前端通过列表/详情接口读取结果，通过 `resume` 接口提交人工审核动作。

**Consequences**: 需要在后端增加 run 元数据与结果快照持久化，并定义状态流转；但能为前端列表页、详情页、轮询更新以及后续进度流扩展打下稳定基础。

### Additional Decision 3

**Context**: 用户明确要求 MVP 不能只靠轮询，必须在这一轮提供实时状态更新。

**Decision**: run 详情页必须接入服务端推送的实时事件通道。

**Consequences**: 后端除了列表/详情接口，还需要提供事件流接口与事件模型；前端需要建立连接、处理断线重连和终态关闭逻辑。

### Additional Decision 4

**Context**: 当前场景主要是服务端单向推送 run 状态、阶段变化和结果更新，客户端主动动作仍然只有创建 run 与提交 resume。

**Decision**: MVP 实时协议采用 `SSE`，不使用 `WebSocket`。

**Consequences**: 协议更简单，和现有 FastAPI/HTTP 边界更一致；但如果未来要支持更复杂的双向会话控制，再评估升级为 `WebSocket`。

## Technical Approach

* Frontend:
  * 使用 `Vite + React + TypeScript`
  * 使用 `React Router` 管理首页、历史页、详情页
  * 使用 `TanStack Query` 管理 create/list/detail/resume 请求
  * 使用 `react-hook-form + zod` 管理表单和参数校验
  * 使用 `react-markdown` 渲染报告内容
  * 使用单独的 SSE 订阅层处理事件流连接与状态同步
* Backend:
  * 新增 run 持久化模型与查询接口
  * 将执行入口改为异步启动，返回 `run_id` 后由后台任务推进
  * 将图执行结果、中断信息、错误信息映射到统一 run 状态模型
  * 增加 SSE 实时事件接口，向前端推送状态和关键阶段变化

### Recommended Event Shape

* `run.created`
* `run.status_changed`
* `run.progress`
* `run.interrupted`
* `run.completed`
* `run.failed`
* `run.resumed`

## Code-Spec Depth Check

### Target Spec Files To Update

* `.trellis/spec/backend/research-agent-runtime.md`
* `.trellis/spec/backend/directory-structure.md`
* `.trellis/spec/frontend/directory-structure.md`
* `.trellis/spec/frontend/state-management.md`
* `.trellis/spec/frontend/type-safety.md`

### Concrete Contracts

#### API Contracts

* `POST /api/research/runs`
  * input: `RunRequest`
  * output: `RunCreatedResponse`
* `GET /api/research/runs`
  * output: `RunListResponse`
* `GET /api/research/runs/{run_id}`
  * output: `RunDetailResponse`
* `GET /api/research/runs/{run_id}/events`
  * output: `text/event-stream` with JSON payload events
* `POST /api/research/runs/{run_id}/resume`
  * input: `ResumeRequest`
  * output: `RunDetailResponse`

#### Run Detail Fields

* `run_id`
* `status`
* `request`
* `result`
* `warnings`
* `error_message`
* `created_at`
* `updated_at`
* `completed_at`

#### Event Fields

* `type`
* `run_id`
* `status`
* `timestamp`
* `data`

### Validation And Error Matrix

| Boundary | Input | Validation | Failure Behavior |
|----------|-------|------------|------------------|
| create API -> run store | `RunRequest` | reuse request schema validation | return 422 before run creation |
| create API -> background runtime | new `run_id` + validated request | persisted queued record must exist before task launch | mark run failed if launch crashes |
| runtime -> run detail snapshot | graph result or interrupt payload | normalize to allowed run statuses and JSON-safe payload | persist `failed` with `error_message` |
| detail API -> frontend | `run_id` path param | run must exist | return 404 |
| resume API -> runtime | `approved`, optional `edited_report` | only allow resume from `interrupted` run | return 409 for invalid status |
| SSE API -> frontend | `run_id` path param | run must exist before stream opens | return 404 or terminal snapshot event |
| SSE payload -> frontend state | event `type/status/data` | unknown event types ignored, malformed JSON guarded | keep last known detail and show stream warning |

### Good / Base / Bad Cases

#### Good

* 用户创建 run 后立即拿到 `run_id`，详情页通过 SSE 收到 `running -> completed`。
* 用户打开一个 `interrupted` run，看到 `draft_report` 与 `warnings`，编辑后成功 `resume`。

#### Base

* 页面刷新后，前端通过 `GET /api/research/runs/{run_id}` 恢复详情，再重新建立 SSE 连接。
* 没有活跃 SSE 订阅时，run 仍能继续执行并持久化最终结果。

#### Bad

* 用户 resume 一个 `completed` run。
* 浏览器订阅一个不存在的 `run_id`。
* 服务重启时有 `queued/running` run 未完成，历史列表留下悬空状态。

# brainstorm: optimize deep research flow

## Goal

聚焦 deep research 的“研究质量闭环”方向，围绕结构化缺口识别、定向重规划和补检索策略，收敛出一个适合先做的 MVP 方案，让下一轮研究不是简单重跑，而是明确知道“缺了什么、为什么缺、下一步补什么”。

## What I already know

* 当前主图已经具备完整链路：ingest -> clarify -> plan -> dispatch -> research_worker -> merge -> gap_check -> synthesize -> audit -> review/finalize。
* `research_worker` 已经是内部子图，包含 query rewrite、搜索聚合、内容获取、过滤、抽取和证据评分，但对外只回 `raw_findings` 与 `raw_source_batches`。
* `gap_check` 目前仍是字符串级规则，只能表达“某 task 没 evidence”或“source 不够多”，无法表达失败原因和补救策略。
* `plan_research_tasks()` 对 gap 的消费也还是文本拼接式，fallback 直接把 gap 包成 `Resolve gap: ...`。
* 当前用户已经明确，优先关注“研究质量闭环”，不是运行可观测性或 UI 优化。

## Assumptions (temporary)

* 第一阶段优先复用现有主图，不引入完整 autonomous multi-agent loop。
* 第一阶段可以接受 graph state 和 worker 输出契约的小幅扩展，只要边界清晰、测试可控。
* “研究质量闭环”优先级高于“展示更细进度”，但如果产生结构化诊断，后续会自然帮助可观测性。

## Open Questions

* 第一阶段要不要把 synthesis 前的 quality gate 一起纳入，还是先只做“结构化 gap + 定向 replan”？

## Requirements (evolving)

* 基于当前代码事实定义“研究质量闭环”的最小可行改造方案。
* 新方案至少回答以下问题：
  * 当前 task 为什么失败或证据弱？
  * 下一轮重规划应该补哪一类缺口？
  * 是否需要在 worker 内部做一次有预算的二次补检索？
* 若修改 state / worker 合约，必须明确新增字段的职责与流向。
* 新方案应保留 deterministic fallback，不把“质量闭环”建立在 LLM 必须可用的前提上。

## Acceptance Criteria (evolving)

* [ ] 已明确研究质量闭环的核心瓶颈和代码落点。
* [ ] 已形成 2-3 个可执行方案，并给出推荐方向。
* [ ] 已说明 graph / worker / planner / gap_check 需要怎样协同变化。
* [ ] 已收敛第一阶段是否包含 synthesis 前 quality gate。

## Definition of Done (team quality bar)

* 结论可直接转入后续实现任务
* 优化建议和现有代码契约不冲突，或已明确指出需要改动的契约
* 产出能支持下一步 PRD/MVP 选择

## Out of Scope (explicit)

* 本任务内直接实现优化方案
* 重做整个 runtime 或引入完整 autonomous agent 框架
* 与研究质量闭环无关的独立 UI 重设计

## Technical Notes

### Relevant files inspected

* `docs/current-langgraph-graph.md`
* `.trellis/spec/backend/research-agent-runtime.md`
* `README.md`
* `app/graph/nodes/clarify.py`
* `app/graph/nodes/planner.py`
* `app/graph/nodes/dispatcher.py`
* `app/graph/nodes/gap_check.py`
* `app/graph/nodes/audit.py`
* `app/graph/nodes/review.py`
* `app/graph/subgraphs/research_worker.py`
* `app/services/planning.py`
* `app/services/research_worker.py`
* `app/services/synthesis.py`
* `app/services/conversation_memory.py`
* `app/run_manager.py`
* `app/run_store.py`
* `web/src/hooks/useRunEvents.ts`
* `web/src/components/ConversationThread.tsx`
* `web/src/pages/ConversationPage.tsx`

### Current observations

* scope 澄清目前只是默认文案补全，还没有真正的 ambiguity resolution。
* `GraphState.gaps` 还是 `list[str]`，天然限制了 gap 的表达能力。
* `research_worker` 子图的内部阶段已经拆开，但外层没有 `task_outcomes` / `task_diagnostics` 之类的结构化出口。
* 现在的 planner 与 gap_check 之间是“字符串协议”，导致闭环弱且难测试。
* 现有测试也主要覆盖 fallback planner / synthesis 的基础行为，尚未建立“弱证据 -> 补洞 -> 再规划”的闭环测试。

## Research Notes

### 方案 A：结构化 gap + 定向 replan（推荐）

* How it works:
  * worker 对外新增 task 级诊断，例如：
    * 查询数
    * 命中数
    * 获取成功数
    * evidence 数
    * 失败原因枚举
    * source host 分布
  * `gap_check` 不再只产出字符串，而是产出结构化 gap：
    * `gap_type`
    * `task_id`
    * `severity`
    * `reason`
    * `retry_hint`
  * `plan_research` / `plan_research_tasks` 消费这些结构化 gap，生成更定向的 follow-up task。
* Pros:
  * 最符合“研究质量闭环”的核心目标。
  * 改动集中在 backend graph/contracts，边界清晰。
  * deterministic fallback 也容易覆盖。
* Cons:
  * 需要扩展 state contract 和若干测试。
  * 第一阶段还不会自动在 worker 内部自愈。

### 方案 B：在 A 基础上增加 worker 内部一次补检索

* How it works:
  * 先做方案 A。
  * 对弱结果 task，在 worker 内部按预算再跑一次替代查询或 source-policy 补检索。
* Pros:
  * 更接近真正的质量闭环，用户更少看到“空结果但流程完成”。
  * 一部分问题可在单 task 内自愈，无需等整轮 replan。
* Cons:
  * 延迟、预算和失败语义会复杂很多。
  * 更容易把第一阶段做大。

### 方案 C：只做 synthesis 前质量门禁

* How it works:
  * 不大改 worker，对现有 findings/sources 增加 coverage gate。
  * 如果 coverage 不足，就回到 `plan_research`。
* Pros:
  * 代码改动最小。
  * 能快速减少“证据很弱但仍然出报告”的情况。
* Cons:
  * 不知道为什么弱，也不知道该怎么补。
  * 容易退化成重复跑流程，闭环质量仍然一般。

## Preliminary Recommendation

优先做方案 A，把“结构化 gap + 定向 replan”先建立起来。它是最小但真正有效的闭环基础；如果这层没做对，直接加 worker 内部补检索，通常只会把复杂度和不确定性一起放大。

## Decision

已确认选择方案 A：

* 第一阶段不做 worker 内部自动补检索。
* 第一阶段聚焦建立可解释、可测试的研究质量闭环基础。
* 第一阶段采用 `A1`：
  * `structured gaps + task diagnostics + targeted replan + synthesis 前 quality gate`

## MVP Shape

### 1. State contract changes

建议把以下字段作为 MVP 的最小新增或改造：

* `GraphState.gaps`
  * 从 `list[str]` 升级为 `list[dict]`
  * 每个 gap 至少包含：
    * `gap_type`
    * `task_id`
    * `title`
    * `reason`
    * `retry_hint`
    * `severity`
* `GraphState.task_outcomes`
  * 新增 reducer-friendly 的 task 级结果列表
  * 用于表达每个 task 在 worker 阶段的质量诊断
* `GraphState.quality_gate`
  * 新增一次聚合后的质量门禁结果
  * 至少包含：
    * `passed`
    * `reasons`
    * `requires_review`
    * `should_replan`

### 2. Worker output changes

`research_worker` 在保留 `raw_findings` / `raw_source_batches` 的同时，再附带一个 task 级诊断对象，例如：

* `task_id`
* `query_count`
* `search_hit_count`
* `acquired_content_count`
* `kept_source_count`
* `evidence_count`
* `failure_reasons`
* `host_count`
* `quality_status`

这样 gap_check 才能区分：

* 是没搜到结果
* 还是搜到了但抓取失败
* 还是抓到了但内容太弱
* 还是有 evidence 但缺独立印证

### 3. Gap model

建议把 gap 先控制在少量稳定枚举，避免过度设计：

* `missing_evidence`
* `weak_evidence`
* `low_source_diversity`
* `retrieval_failure`

对应 `retry_hint` 可以先做 deterministic 文案，不依赖 LLM。

### 4. Planner consumption

`plan_research_tasks()` 不再简单把 gap 当字符串拼到 title 里，而是：

* 先按 gap_type 生成更明确的 follow-up topic
* 再把 `retry_hint` 拼到 task question
* fallback planner 也能保持稳定行为

### 5. Testing impact

第一阶段至少应补这些测试：

* `test_gap_check.py`
  * 从字符串断言改成结构化 gap 断言
* `test_planning.py`
  * 验证 structured gap 会生成定向 follow-up task
* `test_research_worker_service.py` 或 worker subgraph 测试
  * 验证 task diagnostics 的质量状态与失败原因
* `test_conversation_memory.py`
  * 确认结构化 gap 仍能被 memory 提取为用户可读 open questions

## Next Step Proposal

如果继续推进，实现阶段建议遵循下面这个最小设计。

## A1 Execution Design

### 1. Quality gate placement

推荐不要新加独立 graph 节点，而是在现有 `gap_check` 阶段同时完成：

* task-level gap extraction
* run-level quality gate evaluation
* route decision

原因：

* 现有图已经是 `merge_evidence -> gap_check -> synthesize_report`
* 质量门禁本质上就是“是否允许进入 synthesis”
* 放在 `gap_check` 最符合现有职责，不需要额外增加新的 routing node

### 2. Quality gate routing rule

推荐规则：

* 如果 quality gate 不通过，且还有 iteration budget：
  * `should_replan = true`
  * 回到 `plan_research`
* 如果 quality gate 不通过，但已经没有 iteration budget：
  * 允许进入 `synthesize_report`
  * 同时写入 warning
  * 并设置 `requires_review = true`
  * 后续在 `citation_audit`/`human_review` 路径上强制人工把关
* 如果 quality gate 通过：
  * 正常进入 `synthesize_report`

这能避免两种坏情况：

* 质量差但无条件直接出报告
* 质量差且预算耗尽时无限回环

### 3. Minimal contract draft

建议先引入这两个结构：

```json
{
  "task_outcomes": [
    {
      "task_id": "task-1",
      "quality_status": "ok | weak | failed",
      "query_count": 3,
      "search_hit_count": 8,
      "acquired_content_count": 4,
      "kept_source_count": 2,
      "evidence_count": 2,
      "host_count": 2,
      "failure_reasons": ["retrieval_failure"]
    }
  ],
  "quality_gate": {
    "passed": false,
    "should_replan": true,
    "requires_review": false,
    "reasons": ["weak_evidence", "low_source_diversity"]
  }
}
```

### 4. Deterministic gate rules

第一阶段建议全部用确定性规则，不引入 LLM 判分：

* 某个 task `evidence_count == 0`
  * 产出 `missing_evidence` 或 `retrieval_failure`
* 某个 task `evidence_count > 0` 但 `host_count < 2`
  * 产出 `low_source_diversity`
* 整轮 findings 总量过低，或只有单一来源
  * quality gate 不通过

这样第一阶段更容易写单测，也更稳定。

### 5. Contract touch points

第一阶段最可能要改这些位置：

* `app/domain/models.py`
  * 新增 gap / task outcome / quality gate 模型
* `app/graph/state.py`
  * 扩展 graph state 字段
* `app/runtime.py`
  * 初始化新增 state 字段
* `app/graph/nodes/ingest.py`
  * 保持新增字段在 resume/snapshot 中稳定存在
* `app/graph/subgraphs/research_worker.py`
  * 输出 `task_outcomes`
* `app/graph/nodes/gap_check.py`
  * 生成 structured gaps + quality gate + route decision input
* `app/services/planning.py`
  * 消费 structured gaps 并生成定向 follow-up task
* `app/graph/nodes/audit.py`
  * 兼容来自 quality gate 的 warning/review_required
* `app/services/conversation_memory.py`
  * 把 structured gaps 转成用户可读 open questions

### 6. Recommended implementation order

建议按这个顺序落地：

1. 先建模型和 state contract
2. 再改 worker 输出 task diagnostics
3. 再改 `gap_check` 为 structured gaps + quality gate
4. 再改 planner 消费 structured gaps
5. 最后补 memory / audit / tests

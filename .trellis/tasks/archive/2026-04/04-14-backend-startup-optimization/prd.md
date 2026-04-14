# Optimize backend startup

## Goal

优化当前后端服务的启动体验，让本地开发和日常运行更直接、更稳定，减少手工环境准备和易错步骤。

## What I already know

* 当前后端为 Python `3.11+` + FastAPI + Uvicorn。
* 当前 README 推荐通过 `uvicorn app.main:app --reload` 启动服务。
* 当前项目不会自动读取 `.env` 文件，README 要求用户先执行 `set -a; source .env; set +a`。
* 应用入口在 `app/main.py`，通过 `create_app()` 创建 FastAPI 应用，并在 lifespan 中初始化 `ResearchRunManager`。
* 项目根目录存在 `pyproject.toml`，但暂未看到统一的后端启动脚本或 CLI 入口。
* 仓库内没有现成的 `Makefile`、`Justfile`、`Taskfile`、`scripts/start-*.sh` 之类的后端启动封装。
* `.env.example` 只定义业务与运行时变量，暂未包含 `HOST`、`PORT`、`RELOAD` 一类启动参数。

## Assumptions (temporary)

* 用户希望优化的是“开发/本地运行启动方式”，而不是 LangGraph 运行时内部启动流程。
* 本次更可能涉及启动命令、环境变量加载、默认 host/port、开发入口脚本或文档，而不是重构业务逻辑。
* 需要尽量保持现有 API 与运行时行为不变，只改善启动体验。

## Open Questions

* 用户更偏好哪一种“一键启动”入口形式。
* 是否需要切换当前活跃任务，转到这个新的后端任务继续？

## Requirements (evolving)

* 提供比当前 `uvicorn app.main:app --reload` 更顺手的后端启动方式。
* 减少手工执行环境准备命令的成本。
* 保持现有后端接口与核心运行时逻辑兼容。
* 尽量避免让开发者直接接触底层 `uvicorn` 启动命令，优先提供更高层的一键入口。

## Acceptance Criteria (evolving)

* [ ] 后端启动步骤比当前更少或更明确。
* [ ] 新启动方式在本地开发环境可重复执行。
* [ ] README 或相关文档与实际启动方式一致。

## Definition of Done (team quality bar)

* Tests added/updated when behavior changes
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* 暂不默认包含前端联动启动，除非确认需要 fullstack 一键启动。
* 暂不重构 research graph、API 路由或业务服务实现。

## Technical Notes

* 已检查文件：
  * `README.md`
  * `app/main.py`
  * `app/config.py`
  * `pyproject.toml`
  * `.env.example`
* 当前主要痛点候选：
  * 需要手动 `source .env`
  * 启动命令裸露在 README，没有封装成稳定入口
  * host/port/reload 等运行参数没有集中入口

## Research Notes

### Constraints from current repo

* 当前依赖里没有 `python-dotenv` 或 `pydantic-settings`。
* 项目已经使用 `uv` 作为推荐开发工具，且 README 里的 lint/test 命令也优先使用 `uv run`。
* 如果走 shell 脚本方案，会更依赖 Unix shell；跨平台一致性会更弱。

### Feasible approaches here

**Approach A: Python CLI entrypoint via `uv run`** (Recommended)

* How it works:
  * 新增一个 Python 启动入口，例如 `python -m app.dev` 或 `uv run deepresearch-api`
  * 启动时自动读取 `.env`
  * 内部统一调用 `uvicorn.run(...)`
* Pros:
  * 真正单命令
  * 跨平台最好
  * 启动参数、默认值、日志都能集中管理
* Cons:
  * 需要少量新增代码和一个依赖或简单 `.env` 解析逻辑

**Approach A2: FastAPI CLI wrapper**

* How it works:
  * 提供 `fastapi dev app/main.py` 或类似高层入口
  * 让使用者面对的是框架级命令而不是 `uvicorn`
* Pros:
  * 语义更贴近 FastAPI
  * 命令层面对用户更友好
* Cons:
  * 仍需补充 CLI 依赖与项目适配
  * 对当前项目的可控性不如自定义 Python 入口

**Approach B: Root shell script**

* How it works:
  * 新增 `scripts/start-backend.sh`
  * 脚本里自动 `source .env` 后调用 `uvicorn`
* Pros:
  * 实现最快
  * 对当前结构侵入最小
* Cons:
  * 主要偏 Unix
  * Windows/跨平台体验一般
  * 参数扩展和测试性较差

**Approach C: Task runner command such as `make backend`**

* How it works:
  * 引入 `Makefile` 或类似任务工具，封装启动命令
* Pros:
  * 命令短
  * 后续可顺手封装 test/lint/dev
* Cons:
  * 新增一层工具约定
  * 仍需要处理 `.env` 自动加载问题
  * 对“尽量少复杂度”不一定最优

**Approach D: Replace `uvicorn` with another ASGI server**

* How it works:
  * 使用 `hypercorn`、`granian` 等替代运行时
* Pros:
  * 可以真正摆脱 `uvicorn`
* Cons:
  * 解决的是“运行时选择”，不直接解决“一键启动体验”
  * 会引入新的服务器语义、依赖与验证成本
  * 对当前项目属于次优先级

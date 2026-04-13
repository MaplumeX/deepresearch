# deepresearch

基于 `LangGraph + LangChain` 的 Python deep research agent 骨架，支持 `OpenAI-compatible` 模型接口。

## 当前能力

- LangGraph 主图编排：规划、派发、研究、合并、补洞、综合、引用审计、人工审核
- FastAPI 接口：创建 run、恢复 interrupt run、健康检查
- OpenAI-compatible LLM 接入：支持自定义 `base_url`
- SQLite checkpoint：支持长流程恢复
- 搜索/抓取/抽取工具边界已经拆开，后续可替换成更强 provider

## 前置要求

- Python `3.11+`
- 一个 OpenAI-compatible 模型接口
- 一个搜索 provider key
  - 当前代码默认对接 `Tavily`

## 1. 安装依赖

### 方式 A：使用 uv

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 方式 B：使用 venv + pip

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 2. 配置环境变量

先复制示例文件：

```bash
cp .env.example .env
```

然后至少填写这些值：

```bash
LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
LLM_API_KEY=your-api-key
PLANNER_MODEL=your-model-name
SYNTHESIS_MODEL=your-model-name
TAVILY_API_KEY=your-tavily-api-key
```

常见 `LLM_BASE_URL` 形式：

- OpenAI: `https://api.openai.com/v1`
- OpenRouter: `https://openrouter.ai/api/v1`
- 本地 vLLM / One API / 代理网关: `http://host:port/v1`

如果你的兼容接口不要求鉴权，也可以只设置 `LLM_BASE_URL`。当前实现会在缺少 key 时传一个占位值，兼容很多 OpenAI-compatible 网关。

注意：当前项目不会自动读取 `.env` 文件。启动前需要先把变量导入 shell：

```bash
set -a
source .env
set +a
```

## 3. 启动服务

```bash
uvicorn app.main:app --reload
```

默认地址：

```text
http://127.0.0.1:8000
```

## 4. 验证服务是否启动

```bash
curl http://127.0.0.1:8000/health
```

预期返回：

```json
{"status":"ok"}
```

## 5. 发起一次 research run

```bash
curl -X POST http://127.0.0.1:8000/api/research/runs \
  -H "Content-Type: application/json" \
  -d '{
    "question": "如何用 LangGraph 构建一个 deep research agent?",
    "max_iterations": 2,
    "max_parallel_tasks": 3
  }'
```

返回里会包含：

- `run_id`
- `status`
- `result`

当 `status=interrupted` 时，说明当前流程停在人工审核节点，可以继续恢复：

```bash
curl -X POST http://127.0.0.1:8000/api/research/runs/<run_id>/resume \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true
  }'
```

如果你想人工修改报告后再恢复：

```bash
curl -X POST http://127.0.0.1:8000/api/research/runs/<run_id>/resume \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "edited_report": "# Revised Report\n\n..."
  }'
```

## 6. 开发期常用命令

语法编译：

```bash
python3 -m compileall app tests
```

单元测试：

```bash
python3 -m unittest discover -s tests/unit
```

## 运行说明

- 如果没有配置 `LLM_BASE_URL` / `LLM_API_KEY`，规划和综合会退化为确定性 fallback
- 如果没有配置 `TAVILY_API_KEY`，流程仍然能运行，但通常拿不到真实网页证据
- 当前 `research_worker` 是骨架实现，后续适合替换成更强的 deepagents 子代理执行层

## 下一步建议

1. 补 `.env` 自动加载，省掉手动 `source`
2. 加一个真正的 smoke test，覆盖从 API 到 graph 的单次运行
3. 把 `research_worker` 升级为带查询重写、网页筛选和证据打分的真实研究子图

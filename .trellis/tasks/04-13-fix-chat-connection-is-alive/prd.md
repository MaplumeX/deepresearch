# 修复对话 `Connection.is_alive` 报错

## Goal
修复对话创建或续聊时后台研究任务因 `aiosqlite` 兼容性问题失败，避免出现 `'Connection' object has no attribute 'is_alive'`。

## Requirements
- 在不改动业务图状态和对话存储逻辑的前提下修复 runtime 初始化 checkpoint 的兼容性问题。
- 修复应同时覆盖首次运行和 resume 路径。
- 为该兼容性问题补充单元测试，防止回归。

## Acceptance Criteria
- [ ] 创建对话后后台任务不再因为缺少 `is_alive` 属性而失败。
- [ ] resume 路径使用同一兼容逻辑。
- [ ] 新增单测覆盖兼容补丁行为。

## Technical Notes
- 根因是 `langgraph-checkpoint-sqlite` 仍调用 `aiosqlite.Connection.is_alive()`，但当前安装的 `aiosqlite` 版本已移除该方法。
- 兼容逻辑应放在 `app/runtime.py`，作为外部依赖适配层处理。

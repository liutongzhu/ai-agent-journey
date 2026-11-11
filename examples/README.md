# Examples — 可运行示例

每通关一关，这里会新增一个真实可运行的 Demo。所有 Demo 必须实际运行成功后才能标记为可用。

## 计划中的 Demo（随关卡解锁）

| Demo | 对应关卡 | 状态 |
|---|---|---|
| `level0_echo_demo.py` — 第一次工具调用（Mock LLM → ToolCall → echo） | Level 0 | ✅ 已实现（2026-11-11，mock 模式运行通过；`--live` 需 `ANTHROPIC_API_KEY`） |
| `level1_agent_loop_demo.py` — Agent Loop 多步执行（mock / live 两种模式） | Level 1 | 未实现 |
| `level2_bugfix_demo.py` — 教学工作区内修复 Bug 并跑测试 | Level 2 | 未实现 |
| `level3_sandbox_demo.py` — Sandbox 隔离、超时与 Fail Closed 演示 | Level 3 | 未实现 |
| `level4_crash_demo.py` — 运行中崩溃 → 重启恢复演示 | Level 4 | 未实现 |
| `level5_workflow_demo.py` — Plan → Code → Test → Review 工作流 | Level 5 | 未实现 |
| `level6_agentos_demo.py` — 多任务提交 / 查询 / 取消演示 | Level 6 | 未实现 |
| `level7_mcp_demo.py` — 连接 MCP Server 调用外部工具 | Level 7 | 未实现 |
| `level8_benchmark_demo.py` — 评估任务集与 Benchmark 报告 | Level 8 | 未实现 |

> 状态为「未实现」的 Demo 不存在对应文件，属正常情况。不要虚构运行结果。

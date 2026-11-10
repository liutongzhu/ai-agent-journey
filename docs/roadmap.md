# Season 2 · Agent Engineering — 九关工程实战路线

> 每关一个真实的工程能力跃迁。一次只引入当前需要的复杂度。
>
> 分季说明:Season 1([content/season-1/](../content/season-1/README.md))负责原理理解,本路线(Season 2)负责工程实现。

## 冒险地图

| # | 关卡 | 技术主题 | 解锁能力 | Milestone | 状态 | 任务书 |
|---|---|---|---|---|---|---|
| 0 | ⚡ 智能觉醒 | Minimal Agent Harness | Tool Calling | `v0.1.0` | 🔒 未开始 | [level-0.md](levels/level-0.md) |
| 1 | 🧠 自主意识 | Agent Loop | Autonomous Multi-step Execution | `v0.2.0` | 🔒 未开始 | [level-1.md](levels/level-1.md) |
| 2 | 🛠️ 代码工匠 | Mini Coding Agent | Code Editing | `v0.3.0` | 🔒 未开始 | [level-2.md](levels/level-2.md) |
| 3 | 🛡️ 安全堡垒 | Linux Sandbox Executor | Sandboxed Execution | `v0.4.0` | 🔒 未开始 | [level-3.md](levels/level-3.md) |
| 4 | 💾 时间回溯 | State Machine + Checkpoint | Crash Recovery | `v0.5.0` | 🔒 未开始 | [level-4.md](levels/level-4.md) |
| 5 | 🗺️ 命运之图 | Graph Orchestration | Workflow Orchestration | `v0.6.0` | 🔒 未开始 | [level-5.md](levels/level-5.md) |
| 6 | 🏰 指挥中心 | Mini AgentOS | Task Management & Scheduling | `v0.7.0` | 🔒 未开始 | [level-6.md](levels/level-6.md) |
| 7 | 🔌 能力之门 | MCP / Skills | Extensible Tool Ecosystem | `v0.8.0` | 🔒 未开始 | [level-7.md](levels/level-7.md) |
| 8 | 🏆 终极试炼 | Evaluation / Benchmark | Measurable Reliability | `v0.9.0` | 🔒 未开始 | [level-8.md](levels/level-8.md) |

状态说明：🔒 未开始 ｜ 🔄 进行中 ｜ 🛡️ Builder ｜ 🛠️ Engineer ｜ 👑 Master

## 当前主线

**S2-L0 — ⚡ 智能觉醒**:为 Mini Agent 打造第一套工具系统。

## 路线原则

- 顺序推进：后面的关卡建立在前面的能力之上（Sandbox 之前不执行不可信代码）。
- Tag 只在工程通关后创建，不提前打标。
- 任何一关都可以在工程通关后继续打磨个人掌握（Personal Mastery）。
- Rust Executor（[executor-rs/](../executor-rs/README.md)）是主线之外的扩展，不占用关卡。

## 学习循环

```text
理解核心原理 → 构建最小实现 → 运行 Demo → 阅读关键代码
    → 主动制造故障 → 修复与验证 → 通关
```

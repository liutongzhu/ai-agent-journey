# Progress — 进度系统

> 最后更新:2026-11-10(Season 1 前三篇提纲完成;工程线仍处于初始化状态,未开始任何关卡)

## 三线进度定义

三种进度互相独立,**不能混为一谈**:

| 进度线 | 含义 | 判定依据 |
|---|---|---|
| **Learning Progress** | 某个原理是否已经理解,能否复述与应用 | 学习笔记、能讲清执行链路、能预测故障行为 |
| **Content Progress** | 对应文章是否已起草、审核或发布 | `content/season-1/` 各集状态(提纲 → 草稿 → 已审核 → 已发布) |
| **Engineering Progress** | 实验代码和测试是否真正完成 | Demo 真实运行输出、通过的测试、Boss 测试、Git 提交 |

约束:

- 原理「已讨论、待复习」≠ 工程通关。
- 文章未公开发布时,不得标记 Published。
- XP、Builder / Engineer / Master、Git Milestone 规则保留:XP 与成就等级以工程线判定为准,个人掌握(Personal Mastery)对应 Learning 线。

## 当前状态总览

| 进度线 | 当前状态 |
|---|---|
| Learning | Level 0 / Level 1 原理已讨论(待复习);其余未开始 |
| Content | EP00、Level 0、Level 1 提纲完成,均未发布 |
| Engineering | 0 / 9 关,工程初始化完成,全部关卡未开始 |

## Learning Progress(学习进度)

| 编号 | 原理主题 | 状态 | 讨论位置 |
|---|---|---|---|
| S1-L0(对应 S2-L0) | Agent Harness / Tool Calling | 已讨论(待复习) | [content/season-1/level-0](../content/season-1/level-0/) |
| S1-L1(对应 S2-L1) | Agent Loop | 已讨论(待复习) | [content/season-1/level-1](../content/season-1/level-1/) |
| S1-L2 起 | — | 未开始 | — |

## Content Progress(发布进度)

内容状态:提纲(Outline) → 草稿(Draft) → 已审核(Reviewed) → 已发布(Published)

| 篇目 | 提纲 | 草稿 | 审核 | 发布 | 位置 |
|---|---|---|---|---|---|
| S1-EP00 — 从零养成一个 AI Agent | ✅ 2026-11-10 | ❌ | ❌ | ❌ | [content/season-1/ep00](../content/season-1/ep00/) |
| S1-L0 — 给 AI Agent 装上手脚 | ✅ 2026-11-10 | ❌ | ❌ | ❌ | [content/season-1/level-0](../content/season-1/level-0/) |
| S1-L1 — 让 Agent 学会连续行动 | ✅ 2026-11-10 | ❌ | ❌ | ❌ | [content/season-1/level-1](../content/season-1/level-1/) |
| S1-L2 起 | 按需创建(正文确定时) | — | — | — | — |

发布渠道:公众号(`article.md`)/ 朋友圈(`moments.md`)/ X(`x-thread.md`)。未实际发布不得标记 Published。

## Engineering Progress(工程进度)

### 玩家状态

| 字段 | 值 |
|---|---|
| Player | Agent Architect |
| Player Level | 0 |
| Completed Levels | 0 / 9 |
| Total XP | 0 |
| Current Quest | S2-L0 — ⚡ 智能觉醒 |
| Unlocked Skills | None |
| Achievements | None |

### XP 规则(每关上限 100)

| 行为 | XP |
|---|---:|
| 能解释核心原理并记录关键代码 | 20 |
| Demo 实际运行成功 | 30 |
| 自动化测试通过 | 20 |
| Boss 战通过 | 20 |
| Git Commit 完成 | 10 |

### 通关记录

| Level | 工程通关 | 个人掌握 | XP | 成就等级 | Milestone Tag |
|---|---|---|---:|---|---|
| S2-L0 ⚡ 智能觉醒 | 未开始 | 未开始 | 0 | — | — |
| S2-L1 🧠 自主意识 | 未开始 | 未开始 | 0 | — | — |
| S2-L2 🛠️ 代码工匠 | 未开始 | 未开始 | 0 | — | — |
| S2-L3 🛡️ 安全堡垒 | 未开始 | 未开始 | 0 | — | — |
| S2-L4 💾 时间回溯 | 未开始 | 未开始 | 0 | — | — |
| S2-L5 🗺️ 命运之图 | 未开始 | 未开始 | 0 | — | — |
| S2-L6 🏰 指挥中心 | 未开始 | 未开始 | 0 | — | — |
| S2-L7 🔌 能力之门 | 未开始 | 未开始 | 0 | — | — |
| S2-L8 🏆 终极试炼 | 未开始 | 未开始 | 0 | — | — |

### 双层通关机制

#### Engineering Clear(工程通关)

- Demo 成功运行。
- 自动化测试通过。
- Boss 故障测试通过。
- Git 提交完成。

#### Personal Mastery(个人掌握)

- 能解释关键执行链路。
- 能指出最重要的 20–50 行代码。
- 能独立修改一个小功能。
- 能预测并验证一次故障行为。

两者独立记录。**Claude Code 生成的代码不等于学习者已掌握。**

### XP 发放纪律

- XP 只根据**真实证据**发放:可复现的运行输出、通过的测试、Git 提交。
- 文档已创建 ≠ 能力已解锁。
- 不提前发放 XP,不提前创建 Tag。

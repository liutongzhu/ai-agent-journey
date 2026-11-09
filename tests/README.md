# Tests — 测试与故障实验

测试是本项目验收的核心：每个关卡的胜利条件都以自动化测试为准。

## 目录约定

```text
tests/
├── level0/ ... level8/     # 各关功能测试
├── boss/                   # Boss 战：故障注入测试（每关一个）
└── security/               # 安全回归：越界、逃逸用例（Level 2 起积累）
```

## 运行方式

```bash
pip install -e ".[dev]"    # 安装 pytest
pytest                     # 全量
pytest tests/level0 -v     # 单关
pytest tests/boss -v       # 全部 Boss 战
```

## 原则

- Boss 战测试是**可复现的故障**，不是手工演示。
- 安全回归用例一旦加入，后续所有关卡都要持续通过。
- 只写与已实现功能匹配的测试；不为未实现的模块预写空壳测试。

# executor-rs — Rust Executor（未来扩展）

> 本目录属于**未来扩展**，不属于九关主线的必需实现。
> 主线到 `v0.9.0` 为止不依赖 Rust；请勿在完成 Level 0–8 之前提前投入。

## 设想

当 Python 版 Sandbox Executor（`sandbox/`，Level 3）在进程监督、资源控制或高并发调度上遇到瓶颈时，可以考虑用 Rust 重写执行内核：

- 更精确的进程组管理与 `cgroup` 资源限制
- 更低的调度延迟（Level 6 高并发场景）
- 内存安全的超时与清理逻辑

## 与主线的关系

- Rust Executor 通过与 Python Executor 相同的接口（`run(cmd, limits) -> result`）接入。
- 替换的是**执行层实现**，不改变 Runtime / Orchestration 的任何上层设计。
- 评估其必要性的时机在 Level 8 的 Benchmark 数据出来之后——用数据说话。

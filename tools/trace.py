"""结构化 Trace(Level 0):可还原一次完整调用,且不记录参数值与凭据。

原则 17/19:Trace 要能回答"刚才发生了什么",同时凭据与敏感字段必须脱敏。
Dispatcher 只记录元数据(工具名、状态、耗时、错误码),不记录参数值;
redact 作为纵深防御,兜底处理任何意外进入 Trace 的字段。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

_MAX_VALUE_LENGTH = 200
_SENSITIVE_KEY_MARKERS = (
    "api_key",
    "apikey",
    "authorization",
    "token",
    "secret",
    "password",
    "x-api-key",
)


def redact(value):
    """递归脱敏:敏感键替换为 [REDACTED],超长字符串截断。"""
    if isinstance(value, dict):
        return {
            key: ("[REDACTED]" if any(marker in key.lower() for marker in _SENSITIVE_KEY_MARKERS)
                  else redact(val))
            for key, val in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str) and len(value) > _MAX_VALUE_LENGTH:
        return value[:_MAX_VALUE_LENGTH] + f"...[truncated {len(value)} chars]"
    return value


class TraceRecorder:
    """按序收集结构化事件,可渲染为一行式日志或 JSON。"""

    def __init__(self) -> None:
        self.events: list[dict] = []

    def emit(self, event: str, **fields) -> None:
        record = {"ts": datetime.now(timezone.utc).isoformat(), "event": event}
        record.update(redact(fields))
        self.events.append(record)

    def lines(self) -> list[str]:
        """一行式渲染,便于 demo 输出与终端查看。"""
        rendered = []
        for event in self.events:
            fields = {k: v for k, v in event.items() if k not in ("ts", "event")}
            field_text = " ".join(f"{k}={v}" for k, v in fields.items())
            rendered.append(f"[trace] event={event['event']}" + (f" {field_text}" if field_text else ""))
        return rendered

    def to_json(self) -> str:
        return json.dumps(self.events, ensure_ascii=False, indent=2)

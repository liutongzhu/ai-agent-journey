"""Level 0: 结构化 Trace 与脱敏。"""

import json

from tools.trace import TraceRecorder, redact


def test_emit_records_event_with_timestamp():
    recorder = TraceRecorder()
    recorder.emit("tool_executed", call_id="c1", tool="echo", status="ok")
    event = recorder.events[0]
    assert event["event"] == "tool_executed"
    assert event["call_id"] == "c1"
    assert "ts" in event


def test_redact_replaces_sensitive_keys():
    payload = {
        "x-api-key": "sk-ant-real-key",
        "api_key": "another-secret",
        "Authorization": "Bearer xyz",
        "nested": {"token": "t", "safe": "v"},
        "list": [{"secret": "s"}],
    }
    redacted = redact(payload)
    assert redacted["x-api-key"] == "[REDACTED]"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["Authorization"] == "[REDACTED]"
    assert redacted["nested"] == {"token": "[REDACTED]", "safe": "v"}
    assert redacted["list"] == [{"secret": "[REDACTED]"}]


def test_redact_truncates_long_strings():
    long_text = "x" * 500
    result = redact(long_text)
    assert result.startswith("x" * 200)
    assert "truncated 500 chars" in result


def test_lines_rendering():
    recorder = TraceRecorder()
    recorder.emit("tool_executed", call_id="c1", tool="echo", status="ok", duration_ms=2)
    line = recorder.lines()[0]
    assert line.startswith("[trace] event=tool_executed")
    assert "tool=echo" in line
    assert "duration_ms=2" in line


def test_to_json_roundtrip():
    recorder = TraceRecorder()
    recorder.emit("run_started", mode="single_round")
    parsed = json.loads(recorder.to_json())
    assert parsed[0]["event"] == "run_started"
    assert parsed[0]["mode"] == "single_round"


def test_redaction_applies_on_emit():
    recorder = TraceRecorder()
    recorder.emit("llm_request", headers={"x-api-key": "sk-secret"}, note="safe")
    rendered = recorder.to_json()
    assert "sk-secret" not in rendered
    assert "[REDACTED]" in rendered
    assert "safe" in rendered

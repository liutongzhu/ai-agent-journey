"""Level 0: ToolCall 信封解析与统一结果格式。"""

import json

import pytest

from tools.protocol import (
    PROTOCOL_VERSION,
    ErrorCode,
    ToolCallRejected,
    from_tool_use,
    ok_result,
    parse_tool_call,
    rejected_result,
)


def make_envelope(**overrides):
    envelope = {
        "protocol_version": PROTOCOL_VERSION,
        "call_id": "call_1",
        "name": "echo",
        "arguments": {"text": "hi"},
    }
    envelope.update(overrides)
    return envelope


class TestParseToolCall:
    def test_parses_mapping(self):
        call = parse_tool_call(make_envelope())
        assert call.call_id == "call_1"
        assert call.name == "echo"
        assert call.arguments == {"text": "hi"}

    def test_parses_json_string(self):
        call = parse_tool_call(json.dumps(make_envelope()))
        assert call.name == "echo"
        assert call.arguments == {"text": "hi"}

    def test_parses_bytes(self):
        call = parse_tool_call(json.dumps(make_envelope()).encode("utf-8"))
        assert call.call_id == "call_1"

    def test_invalid_json_rejected(self):
        with pytest.raises(ToolCallRejected) as excinfo:
            parse_tool_call('{"name": "echo", ')
        assert excinfo.value.code == ErrorCode.INVALID_JSON

    def test_non_object_json_rejected(self):
        with pytest.raises(ToolCallRejected) as excinfo:
            parse_tool_call("[1, 2, 3]")
        assert excinfo.value.code == ErrorCode.INVALID_CALL

    def test_missing_field_rejected(self):
        envelope = make_envelope()
        del envelope["call_id"]
        with pytest.raises(ToolCallRejected) as excinfo:
            parse_tool_call(envelope)
        assert excinfo.value.code == ErrorCode.INVALID_CALL
        assert "call_id" in excinfo.value.message

    def test_unknown_envelope_field_rejected(self):
        with pytest.raises(ToolCallRejected) as excinfo:
            parse_tool_call(make_envelope(raw_cmd="rm -rf /"))
        assert excinfo.value.code == ErrorCode.INVALID_CALL

    def test_wrong_protocol_version_rejected(self):
        with pytest.raises(ToolCallRejected) as excinfo:
            parse_tool_call(make_envelope(protocol_version=2))
        assert excinfo.value.code == ErrorCode.UNSUPPORTED_VERSION

    def test_string_protocol_version_rejected(self):
        with pytest.raises(ToolCallRejected) as excinfo:
            parse_tool_call(make_envelope(protocol_version="1"))
        assert excinfo.value.code == ErrorCode.UNSUPPORTED_VERSION

    @pytest.mark.parametrize("kwargs", [
        {"call_id": ""},
        {"call_id": 7},
        {"name": ""},
        {"name": None},
        {"arguments": '{"text": "hi"}'},
        {"arguments": ["text"]},
    ])
    def test_bad_field_types_rejected(self, kwargs):
        with pytest.raises(ToolCallRejected) as excinfo:
            parse_tool_call(make_envelope(**kwargs))
        assert excinfo.value.code == ErrorCode.INVALID_CALL

    def test_oversized_string_payload_rejected(self):
        huge = json.dumps(make_envelope(text="x" * 100_000))
        with pytest.raises(ToolCallRejected) as excinfo:
            parse_tool_call(huge)
        assert excinfo.value.code == ErrorCode.INPUT_TOO_LARGE

    def test_oversized_bytes_payload_rejected(self):
        with pytest.raises(ToolCallRejected) as excinfo:
            parse_tool_call(b" " * (70 * 1024))
        assert excinfo.value.code == ErrorCode.INPUT_TOO_LARGE


class TestFromToolUse:
    def test_converts_structured_block(self):
        call = from_tool_use({"id": "tu_1", "name": "echo", "input": {"text": "hi"}})
        assert call.call_id == "tu_1"
        assert call.name == "echo"
        assert call.arguments == {"text": "hi"}

    def test_missing_id_rejected(self):
        with pytest.raises(ToolCallRejected):
            from_tool_use({"name": "echo", "input": {}})

    def test_non_object_input_rejected(self):
        with pytest.raises(ToolCallRejected) as excinfo:
            from_tool_use({"id": "tu_1", "name": "echo", "input": "hi"})
        assert excinfo.value.code == ErrorCode.INVALID_CALL


class TestResultFormat:
    def test_ok_result_to_dict(self):
        result = ok_result("call_1", "echo", "hi", duration_ms=3)
        assert result.to_dict() == {
            "protocol_version": PROTOCOL_VERSION,
            "call_id": "call_1",
            "tool": "echo",
            "status": "ok",
            "output": "hi",
            "duration_ms": 3,
        }

    def test_rejected_result_to_dict(self):
        result = rejected_result("call_9", "echo", ErrorCode.UNKNOWN_TOOL, "nope")
        data = result.to_dict()
        assert data["status"] == "error"
        assert data["error"] == {"code": "unknown_tool", "message": "nope"}
        assert "output" not in data

    def test_feedback_text(self):
        assert ok_result("c", "echo", "hi").feedback_text() == "hi"
        rejected = rejected_result("c", "echo", ErrorCode.TIMEOUT, "too slow")
        assert rejected.feedback_text() == "error timeout: too slow"

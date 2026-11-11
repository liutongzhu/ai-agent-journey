"""Level 0: LLM Adapter — 请求构造、响应解析与错误映射(全部离线、确定性)。

真实网络的用例在文件末尾,由 ANTHROPIC_API_KEY 门控;
没有 Key 时 skip,不会被标记为通过。
"""

import io
import json
import urllib.error

import pytest

from agent import (
    ANTHROPIC_API_URL,
    API_KEY_ENV_VAR,
    DEFAULT_MODEL,
    AnthropicLLMClient,
    LLMError,
    LLMResponse,
    MockLLMClient,
)
from tools.echo import EchoTool


@pytest.fixture(autouse=True)
def clean_api_key_env(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)


def make_client(api_key="test-key"):
    return AnthropicLLMClient(api_key=api_key)


def echo_definition():
    return EchoTool().definition


class TestMockClient:
    def test_returns_scripted_responses_in_order(self):
        client = MockLLMClient([LLMResponse(text="a"), LLMResponse(text="b")])
        assert client.complete([], []).text == "a"
        assert client.complete([], []).text == "b"

    def test_records_received_requests(self):
        client = MockLLMClient([LLMResponse(text="a")])
        client.complete([{"role": "user", "content": "hi"}], [echo_definition()])
        assert client.received_requests[0]["tool_definitions"] == ["echo"]
        assert client.received_requests[0]["messages"][0]["content"] == "hi"

    def test_exhaustion_raises(self):
        client = MockLLMClient([])
        with pytest.raises(RuntimeError, match="exhausted"):
            client.complete([], [])


class TestMissingKeyFailClosed:
    def test_missing_env_key_refuses_to_start(self):
        with pytest.raises(RuntimeError, match=API_KEY_ENV_VAR):
            AnthropicLLMClient()

    def test_explicit_key_used_without_env(self):
        client = AnthropicLLMClient(api_key="explicit-key")
        assert client is not None


class TestRequestConstruction:
    def test_body_contains_tools_and_no_credentials(self):
        client = make_client(api_key="sk-ant-SECRET")
        body = client.build_request_body(
            [{"role": "user", "content": "hello"}], [echo_definition()]
        )
        assert body["model"] == DEFAULT_MODEL
        assert body["messages"] == [{"role": "user", "content": "hello"}]
        assert body["tools"] == [{
            "name": "echo",
            "description": echo_definition().description,
            "input_schema": echo_definition().parameters,
        }]
        rendered = json.dumps(body)
        assert "sk-ant-SECRET" not in rendered
        assert "api_key" not in rendered

    def test_unsupported_role_rejected(self):
        client = make_client()
        with pytest.raises(LLMError, match="role"):
            client.build_request_body([{"role": "system", "content": "x"}], [])


class TestResponseParsing:
    def test_tool_use_and_text_blocks(self):
        client = make_client()
        payload = {
            "content": [
                {"type": "text", "text": "thinking"},
                {"type": "tool_use", "id": "tu_1", "name": "echo",
                 "input": {"text": "hi"}},
            ]
        }
        response = client.parse_response(payload)
        assert response.text == "thinking"
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "echo"
        assert response.raw_content == payload["content"]

    def test_malformed_tool_use_raises_llm_error(self):
        client = make_client()
        with pytest.raises(LLMError, match="tool_use"):
            client.parse_response({"content": [{"type": "tool_use", "name": "echo"}]})

    def test_missing_content_raises_llm_error(self):
        client = make_client()
        with pytest.raises(LLMError, match="content"):
            client.parse_response({})


class TestErrorMapping:
    def _client_with_mocked_urlopen(self, monkeypatch, raise_exc, api_key="test-key"):
        client = AnthropicLLMClient(api_key=api_key)
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["headers"] = dict(request.header_items())
            raise raise_exc

        monkeypatch.setattr("agent.llm.urllib.request.urlopen", fake_urlopen)
        return client, captured

    def test_http_error_maps_to_llm_error_with_status(self, monkeypatch):
        exc = urllib.error.HTTPError(
            ANTHROPIC_API_URL, 401, "Unauthorized",
            hdrs=None, fp=io.BytesIO(b'{"error":{"message":"invalid x-api-key"}}'),
        )
        client, _ = self._client_with_mocked_urlopen(monkeypatch, exc)
        with pytest.raises(LLMError, match="http 401"):
            client.complete([{"role": "user", "content": "hi"}], [echo_definition()])

    def test_url_error_hides_internal_details(self, monkeypatch):
        client, _ = self._client_with_mocked_urlopen(
            monkeypatch, urllib.error.URLError("dns failure with secret-value"))
        with pytest.raises(LLMError) as excinfo:
            client.complete([{"role": "user", "content": "hi"}], [echo_definition()])
        assert "secret-value" not in str(excinfo.value)

    def test_request_sends_api_key_in_header_only(self, monkeypatch):
        exc = urllib.error.HTTPError(ANTHROPIC_API_URL, 500, "Err", None, io.BytesIO(b"{}"))
        client, captured = self._client_with_mocked_urlopen(
            monkeypatch, exc, api_key="sk-ant-HEADER-KEY")
        with pytest.raises(LLMError):
            client.complete([{"role": "user", "content": "hi"}], [echo_definition()])
        headers = {k.lower(): v for k, v in captured["headers"].items()}
        assert headers.get("x-api-key") == "sk-ant-HEADER-KEY"


@pytest.mark.live
@pytest.mark.skipif(
    not __import__("os").environ.get(API_KEY_ENV_VAR),
    reason=f"{API_KEY_ENV_VAR} 未设置,真实 API 用例不运行(不会被标记为通过)",
)
class TestRealApiLive:
    """真实网络用例:只有设置 ANTHROPIC_API_KEY 时才会运行。"""

    def test_real_structured_tool_call(self):
        client = AnthropicLLMClient(max_tokens=256)
        response = client.complete(
            [{"role": "user", "content": "请调用 echo 工具,text 传 'live-ok'。不要输出其他内容。"}],
            [echo_definition()],
        )
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "echo"
        assert response.tool_calls[0].arguments == {"text": "live-ok"}

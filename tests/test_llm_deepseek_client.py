from __future__ import annotations

import json
import urllib.error

import pytest

from dsstar.llm.deepseek_client import DeepSeekClient
from dsstar.llm.registry import get_client


class _FakeHTTPResponse:
    def __init__(self, body: dict) -> None:
        self._body = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_deepseek_complete_parses_content_and_sets_auth_header(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def _fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["authorization"] = request.headers.get("Authorization")
        body = json.loads(request.data.decode("utf-8"))
        captured["model"] = body["model"]
        captured["messages"] = body["messages"]
        return _FakeHTTPResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "OK from deepseek",
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    client = DeepSeekClient(api_key="test-key", model="deepseek-reasoner", base_url="https://api.deepseek.com")
    result = client.complete("Reply with OK")

    assert result == "OK from deepseek"
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["timeout"] == 60
    assert captured["authorization"] == "Bearer test-key"
    assert captured["model"] == "deepseek-reasoner"
    assert captured["messages"] == [{"role": "user", "content": "Reply with OK"}]


@pytest.mark.parametrize(
    "base_url,expected",
    [
        ("https://api.deepseek.com", "https://api.deepseek.com/chat/completions"),
        ("https://api.deepseek.com/v1", "https://api.deepseek.com/v1/chat/completions"),
    ],
)
def test_deepseek_url_builder_handles_base_url_variants(base_url: str, expected: str) -> None:
    client = DeepSeekClient(api_key="test-key", base_url=base_url)
    assert client._chat_completions_url() == expected


def test_deepseek_http_error_includes_status_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            url=request.full_url,
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    client = DeepSeekClient(api_key="secret-key")
    with pytest.raises(RuntimeError) as exc:
        client.complete("hello")

    message = str(exc.value)
    assert "401" in message
    assert "secret-key" not in message


def test_registry_deepseek_without_key_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = get_client("deepseek")
    assert client.name == "mock"

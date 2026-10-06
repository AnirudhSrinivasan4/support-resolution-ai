"""The provider adapter is covered without making external LLM calls."""

import json
from io import BytesIO

from app.infrastructure.llm import openai_compatible
from app.infrastructure.llm.openai_compatible import (
    LLMProviderError,
    OpenAICompatibleLLMProvider,
)


def test_openai_compatible_provider_sends_json_request_and_parses_response(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, *, timeout):
        captured["url"] = request.full_url
        captured["auth"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return BytesIO(
            json.dumps(
                {"choices": [{"message": {"content": '{"resolution":"ok"}'}}]}
            ).encode("utf-8")
        )

    monkeypatch.setattr(openai_compatible, "urlopen", fake_urlopen)
    provider = OpenAICompatibleLLMProvider(
        base_url="http://localhost:9000/v1/", model="local-model", api_key="test-secret"
    )
    result = provider.generate_structured(
        system_prompt="system", user_prompt="user", schema={"type": "object"}
    )
    assert result == {"resolution": "ok"}
    assert captured["url"] == "http://localhost:9000/v1/chat/completions"
    assert captured["auth"] == "Bearer test-secret"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["payload"]["model"] == "local-model"


def test_provider_rejects_invalid_provider_json(monkeypatch) -> None:
    monkeypatch.setattr(openai_compatible, "urlopen", lambda *_args, **_kwargs: BytesIO(b"{}"))
    provider = OpenAICompatibleLLMProvider(base_url="http://local/v1", model="local")
    try:
        provider.generate_structured(system_prompt="s", user_prompt="u", schema={})
    except LLMProviderError as error:
        assert "invalid structured output" in str(error)
    else:
        raise AssertionError("invalid provider response was accepted")

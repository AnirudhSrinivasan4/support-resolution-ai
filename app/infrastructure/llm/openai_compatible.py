"""Small synchronous adapter for OpenAI Chat Completions-compatible APIs."""

import json
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMProviderError(RuntimeError):
    """A provider call failed or returned an invalid structured payload."""


class OpenAICompatibleLLMProvider:
    """Call a configurable Chat Completions endpoint without vendor SDK coupling."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: int = 45,
    ) -> None:
        if not model.strip():
            raise ValueError("LLM_MODEL must be configured for the LLM provider")
        if timeout_seconds < 1:
            raise ValueError("LLM_TIMEOUT_SECONDS must be positive")
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._model = model
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Request JSON output and reject malformed or non-object responses."""
        payload = json.dumps(
            {
                "model": self._model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Return JSON matching this schema:\n{json.dumps(schema)}\n\n{user_prompt}",
                    },
                ],
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        request = Request(self._endpoint, data=payload, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                provider_response = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise LLMProviderError("configured LLM provider request failed") from error
        try:
            content = provider_response["choices"][0]["message"]["content"]
            result = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise LLMProviderError("LLM provider returned invalid structured output") from error
        if not isinstance(result, dict):
            raise LLMProviderError("LLM provider output must be a JSON object")
        return result

"""A thin adapter around an OpenAI-compatible Chat Completions API.

This is deliberately only an API client. Tool execution and the agent loop remain
in this repository instead of being delegated to an agent framework.
"""

from __future__ import annotations

import time
from typing import Any

from .config import AgentConfig


MAX_API_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 1.0


class OpenAICompatibleChatModel:
    def __init__(self, config: AgentConfig):
        try:
            from openai import OpenAI, OpenAIError
        except ImportError as exc:
            raise RuntimeError(
                "The openai package is missing. Run: pip install -r requirements.txt"
            ) from exc

        self._client = OpenAI(api_key=config.api_key, base_url=config.base_url)
        self._api_error_type = OpenAIError
        self._model = config.model

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> Any:
        """Return one assistant message from the configured model."""
        for attempt in range(1, MAX_API_ATTEMPTS + 1):
            try:
                completion = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
                break
            except self._api_error_type as exc:
                if attempt < MAX_API_ATTEMPTS and _is_retryable(exc):
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue
                status = getattr(exc, "status_code", None)
                body = getattr(exc, "body", None)
                detail = _extract_error_detail(body) or str(exc)
                detail = detail.replace("\n", " ")[:600]
                status_text = f" (HTTP {status})" if status else ""
                raise RuntimeError(
                    f"Model API request failed{status_text}: {detail}"
                ) from exc
        if not completion.choices:
            raise RuntimeError("The model returned no choices")
        return completion.choices[0].message


def _extract_error_detail(body: Any) -> str:
    """Extract a concise provider message from an OpenAI-compatible error body."""
    if not isinstance(body, dict):
        return ""
    error = body.get("error", body)
    if not isinstance(error, dict):
        return str(error)
    code = str(error.get("code", "")).strip()
    message = str(error.get("message", "")).strip()
    if code and message:
        return f"{code}: {message}"
    return message or code


def _is_retryable(exc: Exception) -> bool:
    """Retry connection failures, rate limits, and temporary server errors."""
    status = getattr(exc, "status_code", None)
    if status is None:
        return True
    return status in {408, 409, 429} or 500 <= status <= 599

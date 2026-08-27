"""A thin adapter around an OpenAI-compatible Chat Completions API.

This is deliberately only an API client. Tool execution and the agent loop remain
in this repository instead of being delegated to an agent framework.
"""

from __future__ import annotations

from typing import Any

from .config import AgentConfig


class OpenAICompatibleChatModel:
    def __init__(self, config: AgentConfig):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The openai package is missing. Run: pip install -r requirements.txt"
            ) from exc

        self._client = OpenAI(api_key=config.api_key, base_url=config.base_url)
        self._model = config.model

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> Any:
        """Return one assistant message from the configured model."""
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        if not completion.choices:
            raise RuntimeError("The model returned no choices")
        return completion.choices[0].message


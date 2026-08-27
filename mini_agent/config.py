"""Environment-based configuration for the coding agent."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    """Settings required to call an OpenAI-compatible chat API."""

    api_key: str
    base_url: str
    model: str
    max_steps: int = 20

    @classmethod
    def from_env(cls) -> "AgentConfig":
        api_key = os.getenv("AGENT_API_KEY", "").strip()
        base_url = os.getenv("AGENT_BASE_URL", "https://api.openai.com/v1").strip()
        model = os.getenv("AGENT_MODEL", "").strip()
        max_steps_text = os.getenv("AGENT_MAX_STEPS", "20").strip()

        missing = []
        if not api_key:
            missing.append("AGENT_API_KEY")
        if not model:
            missing.append("AGENT_MODEL")
        if missing:
            names = ", ".join(missing)
            raise ValueError(f"Missing environment variables: {names}")

        try:
            max_steps = int(max_steps_text)
        except ValueError as exc:
            raise ValueError("AGENT_MAX_STEPS must be an integer") from exc
        if not 1 <= max_steps <= 100:
            raise ValueError("AGENT_MAX_STEPS must be between 1 and 100")

        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_steps=max_steps,
        )


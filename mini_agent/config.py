"""Environment-based configuration for the coding agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _read_env_file(path: Path) -> dict[str, str]:
    """Read the small KEY=VALUE subset needed by this project."""
    if not path.is_file():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


@dataclass(frozen=True)
class AgentConfig:
    """Settings required to call an OpenAI-compatible chat API."""

    api_key: str
    base_url: str
    model: str
    max_steps: int = 20

    @classmethod
    def from_env(cls) -> "AgentConfig":
        file_values = _read_env_file(Path(".env"))

        def setting(name: str, default: str = "") -> str:
            # Explicit process environment variables override the local .env file.
            return os.getenv(name, file_values.get(name, default)).strip()

        api_key = setting("AGENT_API_KEY")
        base_url = setting("AGENT_BASE_URL", "https://api.openai.com/v1")
        model = setting("AGENT_MODEL")
        max_steps_text = setting("AGENT_MAX_STEPS", "20")

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

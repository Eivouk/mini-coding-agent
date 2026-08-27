"""The hand-written agent loop that connects a model to local tools."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .prompts import SYSTEM_PROMPT
from .tools import TOOL_DEFINITIONS, WorkspaceTools


class ChatModel(Protocol):
    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> Any: ...


EventHandler = Callable[[str, str], None]


@dataclass(frozen=True)
class AgentRunResult:
    final_text: str
    steps: int
    completed: bool


class CodingAgent:
    """Repeatedly ask the model what to do, execute tools, and return results."""

    def __init__(
        self,
        model: ChatModel,
        workspace_tools: WorkspaceTools,
        max_steps: int = 20,
        on_event: EventHandler | None = None,
    ):
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self.model = model
        self.workspace_tools = workspace_tools
        self.max_steps = max_steps
        self.on_event = on_event or (lambda _kind, _message: None)

    def run(self, task: str) -> AgentRunResult:
        if not task.strip():
            raise ValueError("Task cannot be empty")

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task.strip()},
        ]

        for step in range(1, self.max_steps + 1):
            self.on_event("step", f"Step {step}/{self.max_steps}: asking the model")
            message = self.model.complete(messages, TOOL_DEFINITIONS)
            tool_calls = list(getattr(message, "tool_calls", None) or [])
            content = getattr(message, "content", None) or ""

            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": content,
            }

            if tool_calls:
                assistant_message["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ]
            messages.append(assistant_message)

            if content:
                self.on_event("model", content)

            if not tool_calls:
                final_text = content or "The model stopped without a final message."
                return AgentRunResult(final_text=final_text, steps=step, completed=True)

            for call in tool_calls:
                name = call.function.name
                self.on_event("tool", f"Calling {name}")
                try:
                    arguments = json.loads(call.function.arguments or "{}")
                    if not isinstance(arguments, dict):
                        raise ValueError("Tool arguments must be a JSON object")
                    result = self.workspace_tools.execute(name, arguments)
                except (json.JSONDecodeError, ValueError) as exc:
                    result = json.dumps(
                        {"ok": False, "error": f"Invalid tool arguments: {exc}"},
                        ensure_ascii=False,
                    )

                self.on_event("result", result)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    }
                )

        final_text = f"Stopped after reaching the maximum of {self.max_steps} steps."
        self.on_event("stopped", final_text)
        return AgentRunResult(
            final_text=final_text,
            steps=self.max_steps,
            completed=False,
        )


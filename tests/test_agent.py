from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from mini_agent.agent import CodingAgent
from mini_agent.tools import WorkspaceTools


def tool_call(
    call_id: str,
    name: str,
    arguments: dict[str, Any] | str,
) -> Any:
    serialized = arguments if isinstance(arguments, str) else json.dumps(arguments)
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(
            name=name,
            arguments=serialized,
        ),
    )


class FakeModel:
    def __init__(self) -> None:
        self.calls = 0
        self.seen_messages: list[list[dict[str, Any]]] = []

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        self.calls += 1
        self.seen_messages.append(list(messages))
        if self.calls == 1:
            return SimpleNamespace(
                content="I will create the requested file.",
                tool_calls=[
                    tool_call(
                        "call-1",
                        "write_file",
                        {"path": "hello.py", "content": "print('hello')\n"},
                    )
                ],
            )
        return SimpleNamespace(content="Created hello.py successfully.", tool_calls=None)


class CodingAgentTests(unittest.TestCase):
    def test_agent_executes_tool_and_returns_result_to_model(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root = Path(temp_dir)
            model = FakeModel()
            agent = CodingAgent(model, WorkspaceTools(root), max_steps=3)

            result = agent.run("Create hello.py")

            self.assertTrue(result.completed)
            self.assertEqual(result.steps, 2)
            self.assertEqual((root / "hello.py").read_text(encoding="utf-8"), "print('hello')\n")
            second_request = model.seen_messages[1]
            self.assertEqual(second_request[-1]["role"], "tool")
            self.assertIn('"ok": true', second_request[-1]["content"])

    def test_agent_stops_at_step_limit(self) -> None:
        class EndlessModel:
            def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
                return SimpleNamespace(
                    content="Checking again.",
                    tool_calls=[tool_call("repeat", "list_files", {"path": "."})],
                )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            agent = CodingAgent(EndlessModel(), WorkspaceTools(temp_dir), max_steps=2)
            result = agent.run("Keep checking")

        self.assertFalse(result.completed)
        self.assertEqual(result.steps, 2)
        self.assertIn("maximum", result.final_text)

    def test_agent_returns_malformed_arguments_to_model(self) -> None:
        class MalformedModel:
            def __init__(self) -> None:
                self.calls = 0
                self.last_messages: list[dict[str, Any]] = []

            def complete(
                self,
                messages: list[dict[str, Any]],
                tools: list[dict[str, Any]],
            ) -> Any:
                self.calls += 1
                self.last_messages = list(messages)
                if self.calls == 1:
                    return SimpleNamespace(
                        content="",
                        tool_calls=[tool_call("bad", "read_file", "{not-json")],
                    )
                return SimpleNamespace(content="Recovered from bad arguments.", tool_calls=None)

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            model = MalformedModel()
            result = CodingAgent(model, WorkspaceTools(temp_dir), max_steps=2).run("Read")

        self.assertTrue(result.completed)
        self.assertEqual(model.last_messages[-1]["role"], "tool")
        self.assertIn("Invalid tool arguments", model.last_messages[-1]["content"])

    def test_agent_executes_multiple_calls_from_one_model_message(self) -> None:
        class MultipleCallsModel:
            def __init__(self) -> None:
                self.calls = 0
                self.last_messages: list[dict[str, Any]] = []

            def complete(
                self,
                messages: list[dict[str, Any]],
                tools: list[dict[str, Any]],
            ) -> Any:
                self.calls += 1
                self.last_messages = list(messages)
                if self.calls == 1:
                    return SimpleNamespace(
                        content="Creating two files.",
                        tool_calls=[
                            tool_call("one", "write_file", {"path": "one.txt", "content": "1"}),
                            tool_call("two", "write_file", {"path": "two.txt", "content": "2"}),
                        ],
                    )
                return SimpleNamespace(content="Created both files.", tool_calls=None)

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root = Path(temp_dir)
            model = MultipleCallsModel()
            result = CodingAgent(model, WorkspaceTools(root), max_steps=2).run("Create files")

            self.assertEqual((root / "one.txt").read_text(encoding="utf-8"), "1")
            self.assertEqual((root / "two.txt").read_text(encoding="utf-8"), "2")

        self.assertTrue(result.completed)
        self.assertEqual([item["role"] for item in model.last_messages[-2:]], ["tool", "tool"])


if __name__ == "__main__":
    unittest.main()

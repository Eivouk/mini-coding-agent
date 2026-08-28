from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mini_agent.tools import WorkspaceTools


class WorkspaceToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        # Keep test files inside the project so restricted environments can write them.
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.root = Path(self.temp_dir.name)
        self.tools = WorkspaceTools(self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_write_read_and_list_file(self) -> None:
        write_result = self.tools.write_file("src/hello.py", "print('hello')\n")
        self.assertIn("src/hello.py", write_result)

        read_result = self.tools.read_file("src/hello.py")
        self.assertEqual(read_result, "1: print('hello')")
        self.assertIn("src/hello.py", self.tools.list_files("."))

    def test_rejects_path_outside_workspace(self) -> None:
        payload = json.loads(self.tools.execute("read_file", {"path": "../secret.txt"}))
        self.assertFalse(payload["ok"])
        self.assertIn("escapes the workspace", payload["error"])

    def test_runs_command_and_captures_output(self) -> None:
        command = f'"{sys.executable}" -c "print(123)"'
        payload = json.loads(self.tools.execute("run_command", {"command": command}))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["exit_code"], 0)
        self.assertIn("123", payload["result"]["stdout"])

    def test_nonzero_command_is_reported_as_failure_with_output(self) -> None:
        command = f'"{sys.executable}" -c "raise SystemExit(3)"'
        payload = json.loads(self.tools.execute("run_command", {"command": command}))
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["result"]["exit_code"], 3)
        self.assertIn("stderr", payload["result"])

    def test_command_timeout_is_reported_as_tool_error(self) -> None:
        timeout = subprocess.TimeoutExpired(cmd="slow-command", timeout=1)
        with patch("mini_agent.tools.subprocess.run", side_effect=timeout):
            payload = json.loads(
                self.tools.execute(
                    "run_command",
                    {"command": "slow-command", "timeout": 1},
                )
            )

        self.assertFalse(payload["ok"])
        self.assertIn("TimeoutError", payload["error"])

    def test_edit_file_replaces_one_exact_match(self) -> None:
        self.tools.write_file("example.py", "value = 1\nprint(value)\n")
        result = self.tools.edit_file("example.py", "value = 1", "value = 2")

        self.assertIn("example.py", result)
        self.assertEqual(
            (self.root / "example.py").read_text(encoding="utf-8"),
            "value = 2\nprint(value)\n",
        )

    def test_edit_file_rejects_missing_or_ambiguous_match(self) -> None:
        self.tools.write_file("example.py", "same\nsame\n")

        missing = json.loads(
            self.tools.execute(
                "edit_file",
                {"path": "example.py", "old_text": "absent", "new_text": "new"},
            )
        )
        ambiguous = json.loads(
            self.tools.execute(
                "edit_file",
                {"path": "example.py", "old_text": "same", "new_text": "new"},
            )
        )

        self.assertFalse(missing["ok"])
        self.assertIn("not found", missing["error"])
        self.assertFalse(ambiguous["ok"])
        self.assertIn("2 times", ambiguous["error"])

    def test_unknown_tool_is_reported_to_model(self) -> None:
        payload = json.loads(self.tools.execute("missing_tool", {}))
        self.assertFalse(payload["ok"])
        self.assertIn("Unknown tool", payload["error"])

    def test_blocks_destructive_command(self) -> None:
        payload = json.loads(self.tools.execute("run_command", {"command": "git reset --hard"}))
        self.assertFalse(payload["ok"])
        self.assertIn("destructive", payload["error"])


if __name__ == "__main__":
    unittest.main()

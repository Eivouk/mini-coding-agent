from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

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
        result = self.tools.run_command(command)
        self.assertIn("exit_code: 0", result)
        self.assertIn("123", result)

    def test_blocks_destructive_command(self) -> None:
        payload = json.loads(self.tools.execute("run_command", {"command": "git reset --hard"}))
        self.assertFalse(payload["ok"])
        self.assertIn("destructive", payload["error"])


if __name__ == "__main__":
    unittest.main()

"""Local tools exposed to the language model.

The model can request these operations, but this module performs the real local work.
It validates paths, limits output, and converts failures into text the model can use.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


MAX_FILE_CHARS = 50_000
MAX_COMMAND_CHARS = 12_000
IGNORED_DIRECTORIES = {".git", ".venv", "__pycache__", ".pytest_cache"}


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories inside the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path, or . for workspace root.",
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file from the workspace with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."},
                    "start_line": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "First line to read, starting at 1.",
                    },
                    "end_line": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Last line to read, inclusive.",
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or completely replace a UTF-8 text file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."},
                    "content": {"type": "string", "description": "Complete new file content."},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Replace one exact, uniquely occurring text block in an existing "
                "UTF-8 file. Prefer this for small edits."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."},
                    "old_text": {
                        "type": "string",
                        "description": "Exact existing text that must occur once.",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text; may be empty to delete.",
                    },
                },
                "required": ["path", "old_text", "new_text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a non-destructive shell command inside the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run."},
                    "timeout": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 120,
                        "description": "Timeout in seconds. Default is 30.",
                    },
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    },
]


class WorkspaceTools:
    """Execute model-requested operations inside a single workspace."""

    _blocked_command_patterns = (
        r"\brm\s+-[^\r\n]*r[^\r\n]*f\b",
        r"\brmdir\s+/s\b",
        r"\bremove-item\b[^\r\n]*\b-recurse\b",
        r"\bformat\s+[a-z]:",
        r"\bshutdown\b",
        r"\bgit\s+reset\s+--hard\b",
        r"\bgit\s+clean\s+-[^\r\n]*f\b",
    )

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise ValueError(f"Workspace does not exist: {self.root}")

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """Dispatch a tool call and always return a JSON string."""
        try:
            handlers = {
                "list_files": self.list_files,
                "read_file": self.read_file,
                "write_file": self.write_file,
                "edit_file": self.edit_file,
                "run_command": self.run_command,
            }
            handler = handlers.get(name)
            if handler is None:
                raise ValueError(f"Unknown tool: {name}")
            result = handler(**arguments)
            ok = result["exit_code"] == 0 if name == "run_command" else True
            payload = {"ok": ok, "result": result}
        except Exception as exc:  # Tool errors should be visible to the model.
            payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        return json.dumps(payload, ensure_ascii=False)

    def list_files(self, path: str = ".") -> str:
        directory = self._resolve(path)
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {path}")

        entries: list[str] = []
        for item in sorted(directory.rglob("*")):
            relative_parts = item.relative_to(self.root).parts
            if any(part in IGNORED_DIRECTORIES for part in relative_parts):
                continue
            relative = item.relative_to(self.root).as_posix()
            entries.append(relative + ("/" if item.is_dir() else ""))
            if len(entries) >= 500:
                entries.append("... output truncated after 500 entries")
                break
        return "\n".join(entries) if entries else "(empty directory)"

    def read_file(
        self,
        path: str,
        start_line: int = 1,
        end_line: int | None = None,
    ) -> str:
        file_path = self._resolve(path)
        if not file_path.is_file():
            raise ValueError(f"Not a file: {path}")
        if start_line < 1:
            raise ValueError("start_line must be at least 1")
        if end_line is not None and end_line < start_line:
            raise ValueError("end_line must not be before start_line")

        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Only UTF-8 text files are supported") from exc

        lines = text.splitlines()
        selected = lines[start_line - 1 : end_line]
        numbered = [
            f"{number}: {line}"
            for number, line in enumerate(selected, start=start_line)
        ]
        output = "\n".join(numbered)
        if len(output) > MAX_FILE_CHARS:
            output = output[:MAX_FILE_CHARS] + "\n... file output truncated"
        return output

    def write_file(self, path: str, content: str) -> str:
        file_path = self._resolve(path)
        if file_path == self.root:
            raise ValueError("Cannot write to the workspace directory")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        relative = file_path.relative_to(self.root).as_posix()
        return f"Wrote {len(content)} characters to {relative}"

    def edit_file(self, path: str, old_text: str, new_text: str) -> str:
        file_path = self._resolve(path)
        if not file_path.is_file():
            raise ValueError(f"Not a file: {path}")
        if not old_text:
            raise ValueError("old_text cannot be empty")
        if old_text == new_text:
            raise ValueError("old_text and new_text must be different")

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Only UTF-8 text files are supported") from exc

        occurrences = content.count(old_text)
        if occurrences == 0:
            raise ValueError("old_text was not found")
        if occurrences > 1:
            raise ValueError(f"old_text appears {occurrences} times; expected exactly once")

        file_path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
        relative = file_path.relative_to(self.root).as_posix()
        return f"Replaced one occurrence in {relative}"

    def run_command(self, command: str, timeout: int = 30) -> dict[str, Any]:
        if not command.strip():
            raise ValueError("Command cannot be empty")
        if not 1 <= timeout <= 120:
            raise ValueError("timeout must be between 1 and 120 seconds")

        lowered = command.lower()
        for pattern in self._blocked_command_patterns:
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                raise ValueError("Potentially destructive command was blocked")

        try:
            completed = subprocess.run(
                command,
                cwd=self.root,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"Command exceeded {timeout} seconds") from exc

        stream_limit = MAX_COMMAND_CHARS // 2
        return {
            "exit_code": completed.returncode,
            "stdout": self._truncate(completed.stdout, stream_limit),
            "stderr": self._truncate(completed.stderr, stream_limit),
        }

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + "\n... output truncated"

    def _resolve(self, relative_path: str) -> Path:
        candidate_input = Path(relative_path)
        if candidate_input.is_absolute():
            raise ValueError("Absolute paths are not allowed")

        candidate = (self.root / candidate_input).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Path escapes the workspace") from exc
        return candidate

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mini_agent.config import AgentConfig


class AgentConfigTests(unittest.TestCase):
    def test_reads_local_env_file(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root = Path(temp_dir)
            (root / ".env").write_text(
                "AGENT_API_KEY=test-key\n"
                "AGENT_BASE_URL=https://example.test/v1\n"
                "AGENT_MODEL=test-model\n"
                "AGENT_MAX_STEPS=7\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                os.chdir(root)
                try:
                    config = AgentConfig.from_env()
                finally:
                    os.chdir(old_cwd)

        self.assertEqual(config.api_key, "test-key")
        self.assertEqual(config.base_url, "https://example.test/v1")
        self.assertEqual(config.model, "test-model")
        self.assertEqual(config.max_steps, 7)

    def test_process_environment_overrides_env_file(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root = Path(temp_dir)
            (root / ".env").write_text(
                "AGENT_API_KEY=file-key\nAGENT_MODEL=file-model\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"AGENT_API_KEY": "process-key", "AGENT_MODEL": "process-model"},
                clear=True,
            ):
                os.chdir(root)
                try:
                    config = AgentConfig.from_env()
                finally:
                    os.chdir(old_cwd)

        self.assertEqual(config.api_key, "process-key")
        self.assertEqual(config.model, "process-model")


if __name__ == "__main__":
    unittest.main()

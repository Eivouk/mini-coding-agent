"""Command-line interface for the coding agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agent import CodingAgent
from .config import AgentConfig
from .model_client import OpenAICompatibleChatModel
from .tools import WorkspaceTools


def _show_event(kind: str, message: str) -> None:
    labels = {
        "step": "AGENT",
        "model": "MODEL",
        "tool": "TOOL",
        "result": "RESULT",
        "stopped": "STOPPED",
    }
    label = labels.get(kind, kind.upper())
    print(f"\n[{label}] {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mini-agent",
        description="A small coding agent built without an agent framework.",
    )
    parser.add_argument("task", nargs="?", help="Programming task for the agent")
    parser.add_argument(
        "--workspace",
        default=".",
        help="Directory the agent is allowed to modify (default: current directory)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    task = args.task or input("Task: ").strip()

    try:
        config = AgentConfig.from_env()
        workspace = Path(args.workspace).resolve()
        tools = WorkspaceTools(workspace)
        model = OpenAICompatibleChatModel(config)
        agent = CodingAgent(
            model=model,
            workspace_tools=tools,
            max_steps=config.max_steps,
            on_event=_show_event,
        )
        result = agent.run(task)
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nStopped by user.", file=sys.stderr)
        return 130

    print(f"\n[FINAL] {result.final_text}")
    return 0 if result.completed else 1


if __name__ == "__main__":
    raise SystemExit(main())


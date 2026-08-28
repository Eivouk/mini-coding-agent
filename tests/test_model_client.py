from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from mini_agent.model_client import (
    OpenAICompatibleChatModel,
    _extract_error_detail,
    _is_retryable,
)


class FakeAPIError(Exception):
    status_code = 404
    body = {
        "error": {
            "code": "ModelNotOpen",
            "message": "The configured model is not active.",
        }
    }


class FailingCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **_kwargs: object) -> object:
        self.calls += 1
        raise FakeAPIError("long provider traceback text")


class RateLimitError(Exception):
    status_code = 429
    body = {"error": {"message": "try again"}}


class RecoveringCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **_kwargs: object) -> object:
        self.calls += 1
        if self.calls == 1:
            raise RateLimitError("rate limited")
        return SimpleNamespace(choices=[SimpleNamespace(message="recovered")])


class ModelClientTests(unittest.TestCase):
    def test_extracts_nested_provider_error(self) -> None:
        detail = _extract_error_detail(FakeAPIError.body)
        self.assertEqual(detail, "ModelNotOpen: The configured model is not active.")

    def test_converts_sdk_error_to_concise_runtime_error(self) -> None:
        completions = FailingCompletions()
        model = OpenAICompatibleChatModel.__new__(OpenAICompatibleChatModel)
        model._model = "test-model"
        model._api_error_type = FakeAPIError
        model._client = SimpleNamespace(
            chat=SimpleNamespace(completions=completions)
        )

        with self.assertRaisesRegex(
            RuntimeError,
            r"Model API request failed \(HTTP 404\): ModelNotOpen",
        ):
            model.complete([], [])
        self.assertEqual(completions.calls, 1)

    def test_retries_rate_limit_once_then_succeeds(self) -> None:
        completions = RecoveringCompletions()
        model = OpenAICompatibleChatModel.__new__(OpenAICompatibleChatModel)
        model._model = "test-model"
        model._api_error_type = RateLimitError
        model._client = SimpleNamespace(
            chat=SimpleNamespace(completions=completions)
        )

        with patch("mini_agent.model_client.time.sleep") as sleep:
            message = model.complete([], [])

        self.assertEqual(message, "recovered")
        self.assertEqual(completions.calls, 2)
        sleep.assert_called_once()

    def test_retry_policy_only_accepts_temporary_failures(self) -> None:
        self.assertTrue(_is_retryable(RateLimitError()))
        self.assertTrue(_is_retryable(SimpleNamespace(status_code=503)))
        self.assertFalse(_is_retryable(FakeAPIError()))


if __name__ == "__main__":
    unittest.main()

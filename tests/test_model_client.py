from __future__ import annotations

import unittest
from types import SimpleNamespace

from mini_agent.model_client import OpenAICompatibleChatModel, _extract_error_detail


class FakeAPIError(Exception):
    status_code = 404
    body = {
        "error": {
            "code": "ModelNotOpen",
            "message": "The configured model is not active.",
        }
    }


class FailingCompletions:
    def create(self, **_kwargs: object) -> object:
        raise FakeAPIError("long provider traceback text")


class ModelClientTests(unittest.TestCase):
    def test_extracts_nested_provider_error(self) -> None:
        detail = _extract_error_detail(FakeAPIError.body)
        self.assertEqual(detail, "ModelNotOpen: The configured model is not active.")

    def test_converts_sdk_error_to_concise_runtime_error(self) -> None:
        model = OpenAICompatibleChatModel.__new__(OpenAICompatibleChatModel)
        model._model = "test-model"
        model._api_error_type = FakeAPIError
        model._client = SimpleNamespace(
            chat=SimpleNamespace(completions=FailingCompletions())
        )

        with self.assertRaisesRegex(
            RuntimeError,
            r"Model API request failed \(HTTP 404\): ModelNotOpen",
        ):
            model.complete([], [])


if __name__ == "__main__":
    unittest.main()

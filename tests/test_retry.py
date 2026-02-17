"""Tests for LLM error recovery with retry logic."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

# Ensure project root is importable
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from english_compiler.frontend.base import BaseFrontend, _build_user_message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_COREIL = {
    "version": "coreil-1.9",
    "body": [
        {"type": "Print", "args": [{"type": "Literal", "value": "hello"}]}
    ],
}

INVALID_COREIL = {
    "version": "coreil-1.9",
    "body": [
        {"type": "Print"}  # missing "args"
    ],
}


class _StubFrontend(BaseFrontend):
    """Stub frontend that returns canned responses in sequence."""

    def __init__(self, responses: list[dict]) -> None:
        super().__init__()
        self._responses = list(responses)
        self._call_count = 0

    def _call_api(self, user_message: str) -> dict:
        resp = self._responses[min(self._call_count, len(self._responses) - 1)]
        self._call_count += 1
        return resp

    def _call_api_text(self, user_message: str, system_prompt: str) -> str:
        return ""

    def get_model_name(self) -> str:
        return "stub"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_valid_on_first_try():
    """No retry needed when the first response is valid."""
    fe = _StubFrontend([VALID_COREIL])
    result = fe.generate_coreil_from_text("print hello")
    assert result == VALID_COREIL
    assert fe._call_count == 1
    print("  PASS test_valid_on_first_try")


def test_retry_succeeds_on_second_try():
    """Retry once: first response invalid, second valid."""
    fe = _StubFrontend([INVALID_COREIL, VALID_COREIL])
    result = fe.generate_coreil_from_text("print hello")
    assert result == VALID_COREIL
    assert fe._call_count == 2
    print("  PASS test_retry_succeeds_on_second_try")


def test_retry_succeeds_on_third_try():
    """Retry twice: first two invalid, third valid."""
    fe = _StubFrontend([INVALID_COREIL, INVALID_COREIL, VALID_COREIL])
    result = fe.generate_coreil_from_text("print hello")
    assert result == VALID_COREIL
    assert fe._call_count == 3
    print("  PASS test_retry_succeeds_on_third_try")


def test_exhausts_all_retries():
    """All retries fail — should raise RuntimeError."""
    fe = _StubFrontend([INVALID_COREIL])
    try:
        fe.generate_coreil_from_text("print hello", max_retries=2)
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "2 retries" in str(exc)
        assert fe._call_count == 3  # 1 initial + 2 retries
    print("  PASS test_exhausts_all_retries")


def test_max_retries_one():
    """max_retries=1 behaves like the old single-retry logic."""
    fe = _StubFrontend([INVALID_COREIL, VALID_COREIL])
    result = fe.generate_coreil_from_text("print hello", max_retries=1)
    assert result == VALID_COREIL
    assert fe._call_count == 2
    print("  PASS test_max_retries_one")


def test_retry_message_includes_previous_output():
    """Retry message should include the failed Core IL and errors."""
    errors = [{"message": "missing args", "path": "$.body[0]"}]
    msg = _build_user_message("print hello", errors, previous_output=INVALID_COREIL)
    assert "Your previous Core IL output:" in msg
    assert '"type": "Print"' in msg
    assert "missing args" in msg
    print("  PASS test_retry_message_includes_previous_output")


def test_retry_message_no_previous_output():
    """Without previous_output, retry message still includes errors."""
    errors = [{"message": "missing args", "path": "$.body[0]"}]
    msg = _build_user_message("print hello", errors)
    assert "missing args" in msg
    assert "Your previous Core IL output:" not in msg
    print("  PASS test_retry_message_no_previous_output")


def test_retry_message_truncates_large_coreil():
    """Very large Core IL is truncated in the retry message."""
    huge_coreil = {"version": "coreil-1.9", "body": [{"x": "A" * 50_000}]}
    errors = [{"message": "bad", "path": "$"}]
    msg = _build_user_message("test", errors, previous_output=huge_coreil)
    assert "... (truncated)" in msg
    print("  PASS test_retry_message_truncates_large_coreil")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running retry tests...")
    test_valid_on_first_try()
    test_retry_succeeds_on_second_try()
    test_retry_succeeds_on_third_try()
    test_exhausts_all_retries()
    test_max_retries_one()
    test_retry_message_includes_previous_output()
    test_retry_message_no_previous_output()
    test_retry_message_truncates_large_coreil()
    print("\nAll retry tests passed!")

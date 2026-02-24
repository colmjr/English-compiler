"""Unit tests for extracted CLI helper modules."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock

from english_compiler.cli.config_flow import parse_bool_setting
from english_compiler.cli.emit_helpers import (
    is_tier2_unsupported_error,
    run_tier2_fallback,
)
from english_compiler.cli.io_utils import load_json, sha256_bytes, write_json


def test_parse_bool_setting_accepts_expected_values() -> None:
    assert parse_bool_setting("true") is True
    assert parse_bool_setting("YES") is True
    assert parse_bool_setting("0") is False
    assert parse_bool_setting("Off") is False
    assert parse_bool_setting("maybe") is None


def test_load_and_write_json_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        path = root / "doc.json"
        data = {"version": "coreil-1.8", "body": []}

        assert write_json(path, data) is True
        loaded = load_json(path)
        assert loaded == data


def test_load_json_rejects_non_object() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "list.json"
        path.write_text('["not", "an", "object"]', encoding="utf-8")
        assert load_json(path) is None


def test_is_tier2_unsupported_error_marker_detection() -> None:
    assert is_tier2_unsupported_error(ValueError("unsupported ExternalCall")) is True
    assert is_tier2_unsupported_error(ValueError("unsupported MethodCall")) is True
    assert is_tier2_unsupported_error(ValueError("different error")) is False


def test_run_tier2_fallback_dispatches_python_runner() -> None:
    source_path = Path("examples/hello.txt")
    python_output = Path("examples/output/py/hello.py")

    with (
        mock.patch(
            "english_compiler.cli.emit_helpers.get_output_path",
            return_value=python_output,
        ) as get_output_path,
        mock.patch(
            "english_compiler.cli.emit_helpers.run_python_file",
            return_value=7,
        ) as run_python_file,
    ):
        rc = run_tier2_fallback(source_path, "python", supported_targets=("python",))

    assert rc == 7
    get_output_path.assert_called_once_with(source_path, "py", ".py")
    run_python_file.assert_called_once_with(python_output)


def test_run_tier2_fallback_respects_supported_targets() -> None:
    source_path = Path("examples/hello.txt")

    with (
        mock.patch(
            "english_compiler.cli.emit_helpers.get_output_path"
        ) as get_output_path,
        mock.patch(
            "english_compiler.cli.emit_helpers.run_python_file"
        ) as run_python_file,
    ):
        rc = run_tier2_fallback(
            source_path, "python", supported_targets=("javascript",)
        )

    assert rc is None
    get_output_path.assert_not_called()
    run_python_file.assert_not_called()


def test_sha256_bytes_matches_known_value() -> None:
    assert (
        sha256_bytes(b"abc")
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


if __name__ == "__main__":
    test_parse_bool_setting_accepts_expected_values()
    test_load_and_write_json_roundtrip()
    test_load_json_rejects_non_object()
    test_is_tier2_unsupported_error_marker_detection()
    test_run_tier2_fallback_dispatches_python_runner()
    test_run_tier2_fallback_respects_supported_targets()
    test_sha256_bytes_matches_known_value()
    print("All CLI helper tests passed.")

"""Unit tests for extracted CLI helper modules."""

from __future__ import annotations

import tempfile
from pathlib import Path

from english_compiler.cli.config_flow import parse_bool_setting
from english_compiler.cli.emit_helpers import is_tier2_unsupported_error
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
    test_sha256_bytes_matches_known_value()
    print("All CLI helper tests passed.")


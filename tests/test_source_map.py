"""Tests for source map functionality.

Tests cover:
- source_map validation (valid, missing, invalid cases)
- Mock frontend includes source_map
- compose_source_maps function
- Python emitter coreil_line_map tracking
- Round-trip composition
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from english_compiler.coreil.validate import validate_coreil
from english_compiler.coreil.emit import emit_python
from english_compiler.coreil.source_map import compose_source_maps
from english_compiler.frontend.mock_llm import MockFrontend


def _prog(body, source_map=None):
    """Build a minimal Core IL document."""
    doc = {"version": "coreil-1.9", "body": body}
    if source_map is not None:
        doc["source_map"] = source_map
    return doc


def _lit(val):
    return {"type": "Literal", "value": val}


def _var(name):
    return {"type": "Var", "name": name}


# ========== Validation Tests ==========

def test_valid_source_map():
    """Valid source_map passes validation."""
    doc = _prog(
        [
            {"type": "Let", "name": "x", "value": _lit(1)},
            {"type": "Let", "name": "y", "value": _lit(2)},
            {"type": "Print", "args": [_var("x")]},
        ],
        source_map={"1": [0, 1], "2": [2]},
    )
    errors = validate_coreil(doc)
    assert errors == [], f"Expected no errors, got {errors}"
    print("  test_valid_source_map: passed")


def test_missing_source_map():
    """Missing source_map is still valid (backward compat)."""
    doc = _prog([{"type": "Print", "args": [_lit("hi")]}])
    assert "source_map" not in doc
    errors = validate_coreil(doc)
    assert errors == [], f"Expected no errors, got {errors}"
    print("  test_missing_source_map: passed")


def test_source_map_bad_key():
    """Non-integer string key is rejected."""
    doc = _prog(
        [{"type": "Print", "args": [_lit("hi")]}],
        source_map={"abc": [0]},
    )
    errors = validate_coreil(doc)
    assert any("string integer" in e["message"] for e in errors), f"Expected key error, got {errors}"
    print("  test_source_map_bad_key: passed")


def test_source_map_zero_key():
    """Key '0' is rejected (must be positive)."""
    doc = _prog(
        [{"type": "Print", "args": [_lit("hi")]}],
        source_map={"0": [0]},
    )
    errors = validate_coreil(doc)
    assert any("positive integer" in e["message"] for e in errors), f"Expected positive key error, got {errors}"
    print("  test_source_map_zero_key: passed")


def test_source_map_out_of_range():
    """Index beyond body length is rejected."""
    doc = _prog(
        [{"type": "Print", "args": [_lit("hi")]}],
        source_map={"1": [0, 5]},
    )
    errors = validate_coreil(doc)
    assert any("out of range" in e["message"] for e in errors), f"Expected range error, got {errors}"
    print("  test_source_map_out_of_range: passed")


def test_source_map_duplicate_index():
    """Same body index in multiple entries is rejected."""
    doc = _prog(
        [
            {"type": "Let", "name": "x", "value": _lit(1)},
            {"type": "Print", "args": [_var("x")]},
        ],
        source_map={"1": [0, 1], "2": [1]},
    )
    errors = validate_coreil(doc)
    assert any("appears in multiple" in e["message"] for e in errors), f"Expected duplicate error, got {errors}"
    print("  test_source_map_duplicate_index: passed")


def test_source_map_negative_index():
    """Negative index is rejected."""
    doc = _prog(
        [{"type": "Print", "args": [_lit("hi")]}],
        source_map={"1": [-1]},
    )
    errors = validate_coreil(doc)
    assert any("non-negative" in e["message"] for e in errors), f"Expected non-negative error, got {errors}"
    print("  test_source_map_negative_index: passed")


def test_source_map_not_dict():
    """source_map must be an object."""
    doc = _prog(
        [{"type": "Print", "args": [_lit("hi")]}],
        source_map=[0],
    )
    errors = validate_coreil(doc)
    assert any("must be an object" in e["message"] for e in errors), f"Expected type error, got {errors}"
    print("  test_source_map_not_dict: passed")


# ========== Mock Frontend Test ==========

def test_mock_includes_source_map():
    """Mock frontend includes source_map in output."""
    frontend = MockFrontend()
    doc = frontend.generate_coreil_from_text("print hello")
    assert "source_map" in doc, "Mock frontend should include source_map"
    assert doc["source_map"] == {"1": [0]}, f"Expected {{\"1\": [0]}}, got {doc['source_map']}"
    # Validate the output
    errors = validate_coreil(doc)
    assert errors == [], f"Mock output should be valid, got {errors}"
    print("  test_mock_includes_source_map: passed")


# ========== Compose Function Tests ==========

def test_compose_basic():
    """Basic composition of two source maps."""
    english_to_coreil = {"1": [0, 1], "3": [2]}
    coreil_to_target = {0: [1, 2], 1: [3], 2: [4, 5]}
    result = compose_source_maps(english_to_coreil, coreil_to_target)
    assert result == {"1": [1, 2, 3], "3": [4, 5]}, f"Got {result}"
    print("  test_compose_basic: passed")


def test_compose_missing_coreil_index():
    """Compose handles missing Core IL indices gracefully."""
    english_to_coreil = {"1": [0, 1]}
    coreil_to_target = {0: [1, 2]}  # index 1 not present
    result = compose_source_maps(english_to_coreil, coreil_to_target)
    assert result == {"1": [1, 2]}, f"Got {result}"
    print("  test_compose_missing_coreil_index: passed")


def test_compose_empty():
    """Compose with empty maps."""
    result = compose_source_maps({}, {})
    assert result == {}, f"Got {result}"
    print("  test_compose_empty: passed")


def test_compose_sorts_output():
    """Composed target lines are sorted."""
    english_to_coreil = {"1": [1, 0]}
    coreil_to_target = {0: [5, 6], 1: [1, 2]}
    result = compose_source_maps(english_to_coreil, coreil_to_target)
    assert result == {"1": [1, 2, 5, 6]}, f"Got {result}"
    print("  test_compose_sorts_output: passed")


# ========== Python Emitter Line Map Tests ==========

def test_python_emitter_line_map():
    """Python emitter produces coreil_line_map for simple program."""
    doc = _prog([
        {"type": "Let", "name": "x", "value": _lit(1)},
        {"type": "Print", "args": [_var("x")]},
    ])
    code, line_map = emit_python(doc)
    # line_map should have entries for stmt 0 and 1
    assert 0 in line_map, f"Expected stmt 0 in line_map, got {line_map}"
    assert 1 in line_map, f"Expected stmt 1 in line_map, got {line_map}"
    # Lines should be valid indices into the output
    lines = code.split("\n")
    for stmt_idx, line_nums in line_map.items():
        for ln in line_nums:
            assert 0 <= ln < len(lines), f"Line {ln} out of range for stmt {stmt_idx}"
    print("  test_python_emitter_line_map: passed")


def test_python_emitter_line_map_with_imports():
    """Python emitter adjusts line_map when imports are prepended."""
    # Use a program that triggers an import (e.g., math)
    doc = _prog([
        {"type": "Let", "name": "x", "value": {"type": "Math", "op": "sqrt", "arg": _lit(4)}},
        {"type": "Print", "args": [_var("x")]},
    ])
    code, line_map = emit_python(doc)
    # Should have import math at the top
    lines = code.split("\n")
    assert lines[0] == "import math", f"Expected 'import math', got '{lines[0]}'"
    # Line map entries should be offset past the import + blank line
    for stmt_idx, line_nums in line_map.items():
        for ln in line_nums:
            assert ln >= 2, f"Expected line >= 2 (after imports), got {ln} for stmt {stmt_idx}"
    print("  test_python_emitter_line_map_with_imports: passed")


# ========== Round-Trip Test ==========

def test_round_trip_composition():
    """English→CoreIL source_map + emitter line_map compose correctly."""
    doc = _prog(
        [
            {"type": "Let", "name": "x", "value": _lit(42)},
            {"type": "Print", "args": [_var("x")]},
        ],
        source_map={"1": [0], "2": [1]},
    )
    code, coreil_line_map = emit_python(doc)
    english_to_coreil = doc["source_map"]
    english_to_target = compose_source_maps(english_to_coreil, coreil_line_map)

    # Both English lines should map to some target lines
    assert "1" in english_to_target, f"Expected line 1 in result, got {english_to_target}"
    assert "2" in english_to_target, f"Expected line 2 in result, got {english_to_target}"

    # Verify the target lines reference actual code
    lines = code.split("\n")
    for eng_line, target_lines in english_to_target.items():
        for ln in target_lines:
            assert 0 <= ln < len(lines), f"Line {ln} out of range for English line {eng_line}"
            assert lines[ln].strip(), f"Expected non-empty line at {ln} for English line {eng_line}"

    print("  test_round_trip_composition: passed")


def main():
    print("Running source map tests...\n")

    # Validation tests
    test_valid_source_map()
    test_missing_source_map()
    test_source_map_bad_key()
    test_source_map_zero_key()
    test_source_map_out_of_range()
    test_source_map_duplicate_index()
    test_source_map_negative_index()
    test_source_map_not_dict()

    # Mock frontend
    test_mock_includes_source_map()

    # Compose function
    test_compose_basic()
    test_compose_missing_coreil_index()
    test_compose_empty()
    test_compose_sorts_output()

    # Emitter line map
    test_python_emitter_line_map()
    test_python_emitter_line_map_with_imports()

    # Round-trip
    test_round_trip_composition()

    print(f"\nAll 16 source map tests passed!")


if __name__ == "__main__":
    main()

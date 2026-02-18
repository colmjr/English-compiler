"""Tests for Core IL static analysis (linter).

Tests the 4 lint rules in english_compiler/coreil/lint.py:
- unused-variable
- unreachable-code
- empty-body
- variable-shadowing

Run with: python -m tests.test_lint
"""

from __future__ import annotations

import sys

from english_compiler.coreil.lint import lint_coreil


def _make_doc(body: list) -> dict:
    return {"version": "coreil-1.8", "body": body}


def _warnings_for_rule(diagnostics: list[dict], rule: str) -> list[dict]:
    return [d for d in diagnostics if d["rule"] == rule]


def test_unused_variable():
    """Let declaration with no subsequent Var reference triggers unused-variable."""
    doc = _make_doc([
        {"type": "Let", "name": "x", "value": {"type": "Literal", "value": 42}},
        {"type": "Print", "args": [{"type": "Literal", "value": "done"}]},
    ])
    warnings = lint_coreil(doc)
    unused = _warnings_for_rule(warnings, "unused-variable")
    assert len(unused) == 1, f"expected 1 unused-variable warning, got {len(unused)}"
    assert "x" in unused[0]["message"]


def test_used_variable():
    """Variable that is referenced should not trigger unused-variable."""
    doc = _make_doc([
        {"type": "Let", "name": "x", "value": {"type": "Literal", "value": 42}},
        {"type": "Print", "args": [{"type": "Var", "name": "x"}]},
    ])
    warnings = lint_coreil(doc)
    unused = _warnings_for_rule(warnings, "unused-variable")
    assert len(unused) == 0, f"expected 0 unused-variable warnings, got {len(unused)}"


def test_unreachable_after_return():
    """Statements after Return in same block trigger unreachable-code."""
    doc = _make_doc([
        {"type": "FuncDef", "name": "f", "params": [], "body": [
            {"type": "Return", "value": {"type": "Literal", "value": 1}},
            {"type": "Print", "args": [{"type": "Literal", "value": "unreachable"}]},
        ]},
        {"type": "Print", "args": [{"type": "Call", "name": "f", "args": []}]},
    ])
    warnings = lint_coreil(doc)
    unreachable = _warnings_for_rule(warnings, "unreachable-code")
    assert len(unreachable) == 1, f"expected 1 unreachable-code warning, got {len(unreachable)}"


def test_unreachable_after_break():
    """Statements after Break trigger unreachable-code."""
    doc = _make_doc([
        {"type": "Let", "name": "i", "value": {"type": "Literal", "value": 0}},
        {"type": "While", "test": {"type": "Literal", "value": True}, "body": [
            {"type": "Break"},
            {"type": "Print", "args": [{"type": "Literal", "value": "unreachable"}]},
        ]},
        {"type": "Print", "args": [{"type": "Var", "name": "i"}]},
    ])
    warnings = lint_coreil(doc)
    unreachable = _warnings_for_rule(warnings, "unreachable-code")
    assert len(unreachable) == 1, f"expected 1 unreachable-code warning, got {len(unreachable)}"


def test_unreachable_after_throw():
    """Statements after Throw trigger unreachable-code."""
    doc = _make_doc([
        {"type": "Throw", "message": {"type": "Literal", "value": "error"}},
        {"type": "Print", "args": [{"type": "Literal", "value": "unreachable"}]},
    ])
    warnings = lint_coreil(doc)
    unreachable = _warnings_for_rule(warnings, "unreachable-code")
    assert len(unreachable) == 1, f"expected 1 unreachable-code warning, got {len(unreachable)}"


def test_empty_body_if():
    """If with empty then body triggers empty-body."""
    doc = _make_doc([
        {"type": "If", "test": {"type": "Literal", "value": True}, "then": []},
    ])
    warnings = lint_coreil(doc)
    empty = _warnings_for_rule(warnings, "empty-body")
    assert len(empty) == 1, f"expected 1 empty-body warning, got {len(empty)}"
    assert "then" in empty[0]["message"]


def test_empty_body_while():
    """While with empty body triggers empty-body."""
    doc = _make_doc([
        {"type": "While", "test": {"type": "Literal", "value": False}, "body": []},
    ])
    warnings = lint_coreil(doc)
    empty = _warnings_for_rule(warnings, "empty-body")
    assert len(empty) == 1, f"expected 1 empty-body warning, got {len(empty)}"
    assert "body" in empty[0]["message"]


def test_variable_shadowing():
    """Double Let on same name triggers variable-shadowing."""
    doc = _make_doc([
        {"type": "Let", "name": "x", "value": {"type": "Literal", "value": 1}},
        {"type": "Let", "name": "x", "value": {"type": "Literal", "value": 2}},
        {"type": "Print", "args": [{"type": "Var", "name": "x"}]},
    ])
    warnings = lint_coreil(doc)
    shadow = _warnings_for_rule(warnings, "variable-shadowing")
    assert len(shadow) == 1, f"expected 1 variable-shadowing warning, got {len(shadow)}"
    assert "x" in shadow[0]["message"]


def test_no_shadowing_with_assign():
    """Assign after Let should not trigger variable-shadowing."""
    doc = _make_doc([
        {"type": "Let", "name": "x", "value": {"type": "Literal", "value": 1}},
        {"type": "Assign", "name": "x", "value": {"type": "Literal", "value": 2}},
        {"type": "Print", "args": [{"type": "Var", "name": "x"}]},
    ])
    warnings = lint_coreil(doc)
    shadow = _warnings_for_rule(warnings, "variable-shadowing")
    assert len(shadow) == 0, f"expected 0 variable-shadowing warnings, got {len(shadow)}"


def test_clean_program():
    """A well-formed program should produce 0 warnings."""
    doc = _make_doc([
        {"type": "Let", "name": "x", "value": {"type": "Literal", "value": 10}},
        {"type": "Let", "name": "y", "value": {
            "type": "Binary", "op": "+",
            "left": {"type": "Var", "name": "x"},
            "right": {"type": "Literal", "value": 5},
        }},
        {"type": "Print", "args": [{"type": "Var", "name": "y"}]},
    ])
    warnings = lint_coreil(doc)
    assert len(warnings) == 0, f"expected 0 warnings, got {len(warnings)}: {warnings}"


def test_func_unused_top_level():
    """FuncDef at top level should not trigger unused-variable (may be entry point)."""
    doc = _make_doc([
        {"type": "FuncDef", "name": "helper", "params": ["a"], "body": [
            {"type": "Return", "value": {"type": "Var", "name": "a"}},
        ]},
    ])
    warnings = lint_coreil(doc)
    unused = _warnings_for_rule(warnings, "unused-variable")
    assert len(unused) == 0, f"expected 0 unused-variable warnings for top-level FuncDef, got {len(unused)}"


def test_multiple_rules():
    """A single document can trigger multiple different rules."""
    doc = _make_doc([
        # unused-variable: unused_var is never referenced
        {"type": "Let", "name": "unused_var", "value": {"type": "Literal", "value": 1}},
        # empty-body: If with empty then
        {"type": "If", "test": {"type": "Literal", "value": True}, "then": []},
    ])
    warnings = lint_coreil(doc)
    rules_triggered = {w["rule"] for w in warnings}
    assert "unused-variable" in rules_triggered, "expected unused-variable warning"
    assert "empty-body" in rules_triggered, "expected empty-body warning"
    assert len(warnings) >= 2, f"expected at least 2 warnings, got {len(warnings)}"


def test_used_variable_in_switch_case_value():
    """Var references in Switch case values should count as usage."""
    doc = _make_doc([
        {"type": "Let", "name": "x", "value": {"type": "Literal", "value": 2}},
        {
            "type": "Switch",
            "test": {"type": "Literal", "value": 1},
            "cases": [
                {
                    "value": {"type": "Var", "name": "x"},
                    "body": [{"type": "Print", "args": [{"type": "Literal", "value": "hit"}]}],
                },
            ],
        },
    ])
    warnings = lint_coreil(doc)
    unused = _warnings_for_rule(warnings, "unused-variable")
    assert len(unused) == 0, f"expected 0 unused-variable warnings, got {len(unused)}"


def main() -> int:
    print("Running lint tests...\n")

    tests = [
        test_unused_variable,
        test_used_variable,
        test_unreachable_after_return,
        test_unreachable_after_break,
        test_unreachable_after_throw,
        test_empty_body_if,
        test_empty_body_while,
        test_variable_shadowing,
        test_no_shadowing_with_assign,
        test_clean_program,
        test_func_unused_top_level,
        test_multiple_rules,
        test_used_variable_in_switch_case_value,
    ]

    failures = []
    for test in tests:
        try:
            test()
            print(f"  {test.__name__}: \u2713")
        except AssertionError as e:
            failures.append(f"{test.__name__}: {e}")
            print(f"  {test.__name__}: \u2717 ({e})")
        except Exception as e:
            failures.append(f"{test.__name__}: {e}")
            print(f"  {test.__name__}: \u2717 ({e})")

    print()
    if failures:
        print(f"{len(failures)}/{len(tests)} tests failed")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"All {len(tests)} lint tests passed! \u2713")
    return 0


if __name__ == "__main__":
    sys.exit(main())

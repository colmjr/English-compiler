"""Tests for Core IL lowering pass.

Note: As of v1.7, For/ForEach loops are preserved (not lowered to While)
to properly support Break and Continue statements. The lowering pass
only lowers expressions inside the loops.
"""

from __future__ import annotations

from english_compiler.coreil.lower import lower_coreil


def test_for_range_preserved() -> None:
    """Test that For loops with Range are preserved (not lowered to While)."""
    doc = {
        "version": "coreil-1.7",
        "body": [
            {
                "type": "For",
                "var": "i",
                "iter": {
                    "type": "Range",
                    "from": {"type": "Literal", "value": 0},
                    "to": {"type": "Literal", "value": 5},
                },
                "body": [
                    {
                        "type": "Print",
                        "args": [{"type": "Var", "name": "i"}],
                    }
                ],
            }
        ],
    }

    lowered = lower_coreil(doc)
    body = lowered["body"]

    # For loop should be preserved, not converted to While
    assert len(body) == 1
    assert body[0]["type"] == "For"
    assert body[0]["var"] == "i"
    assert body[0]["iter"]["type"] == "Range"
    assert body[0]["iter"]["from"]["value"] == 0
    assert body[0]["iter"]["to"]["value"] == 5


def test_for_range_inclusive_preserved() -> None:
    """Test For loop with inclusive Range is preserved."""
    doc = {
        "version": "coreil-1.7",
        "body": [
            {
                "type": "For",
                "var": "x",
                "iter": {
                    "type": "Range",
                    "from": {"type": "Literal", "value": 1},
                    "to": {"type": "Literal", "value": 10},
                    "inclusive": True,
                },
                "body": [],
            }
        ],
    }

    lowered = lower_coreil(doc)
    body = lowered["body"]

    # For loop should be preserved with inclusive flag
    assert body[0]["type"] == "For"
    assert body[0]["iter"]["inclusive"] is True


def test_nested_for_loops_preserved() -> None:
    """Test nested For loops are both preserved."""
    doc = {
        "version": "coreil-1.7",
        "body": [
            {
                "type": "For",
                "var": "i",
                "iter": {
                    "type": "Range",
                    "from": {"type": "Literal", "value": 0},
                    "to": {"type": "Literal", "value": 3},
                },
                "body": [
                    {
                        "type": "For",
                        "var": "j",
                        "iter": {
                            "type": "Range",
                            "from": {"type": "Literal", "value": 0},
                            "to": {"type": "Literal", "value": 2},
                        },
                        "body": [],
                    }
                ],
            }
        ],
    }

    lowered = lower_coreil(doc)
    body = lowered["body"]

    # Outer For loop preserved
    assert body[0]["type"] == "For"
    assert body[0]["var"] == "i"

    # Inner For loop also preserved
    inner_body = body[0]["body"]
    assert len(inner_body) == 1
    assert inner_body[0]["type"] == "For"
    assert inner_body[0]["var"] == "j"


def test_for_in_function_preserved() -> None:
    """Test For loops inside function definitions are preserved."""
    doc = {
        "version": "coreil-1.7",
        "body": [
            {
                "type": "FuncDef",
                "name": "loop_func",
                "params": [],
                "body": [
                    {
                        "type": "For",
                        "var": "i",
                        "iter": {
                            "type": "Range",
                            "from": {"type": "Literal", "value": 0},
                            "to": {"type": "Literal", "value": 5},
                        },
                        "body": [],
                    }
                ],
            }
        ],
    }

    lowered = lower_coreil(doc)
    func = lowered["body"][0]

    assert func["type"] == "FuncDef"
    func_body = func["body"]

    # For loop inside function should be preserved
    assert len(func_body) == 1
    assert func_body[0]["type"] == "For"
    assert func_body[0]["var"] == "i"


def test_foreach_preserved() -> None:
    """Test ForEach loops are preserved."""
    doc = {
        "version": "coreil-1.7",
        "body": [
            {
                "type": "ForEach",
                "var": "x",
                "iter": {"type": "Var", "name": "arr"},
                "body": [
                    {"type": "Print", "args": [{"type": "Var", "name": "x"}]}
                ],
            }
        ],
    }

    lowered = lower_coreil(doc)
    body = lowered["body"]

    # ForEach should be preserved
    assert len(body) == 1
    assert body[0]["type"] == "ForEach"
    assert body[0]["var"] == "x"


def test_expressions_still_lowered() -> None:
    """Test that expressions inside For loops are still lowered."""
    # Note: Currently the main expression lowering is for Range inside For,
    # which is now preserved. This test verifies the structure is maintained.
    doc = {
        "version": "coreil-1.7",
        "body": [
            {
                "type": "For",
                "var": "i",
                "iter": {
                    "type": "Range",
                    "from": {"type": "Binary", "op": "+", "left": {"type": "Literal", "value": 0}, "right": {"type": "Literal", "value": 1}},
                    "to": {"type": "Literal", "value": 5},
                },
                "body": [
                    {
                        "type": "Let",
                        "name": "x",
                        "value": {"type": "Binary", "op": "*", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 2}},
                    }
                ],
            }
        ],
    }

    lowered = lower_coreil(doc)
    body = lowered["body"]

    # Structure should be preserved with lowered expressions
    assert body[0]["type"] == "For"
    # The Range and its from/to should be preserved and lowered
    assert body[0]["iter"]["type"] == "Range"
    assert body[0]["iter"]["from"]["type"] == "Binary"


def main() -> None:
    test_for_range_preserved()
    test_for_range_inclusive_preserved()
    test_nested_for_loops_preserved()
    test_for_in_function_preserved()
    test_foreach_preserved()
    test_expressions_still_lowered()
    print("All lowering tests passed.")


if __name__ == "__main__":
    main()

"""Tests for Core IL lowering pass."""

from __future__ import annotations

from english_compiler.coreil.lower import lower_coreil


def test_for_range_basic() -> None:
    """Test basic For loop with Range lowering."""
    doc = {
        "version": "coreil-0.3",
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

    # Should produce: Let i = 0; While i < 5: Print(i); i = i + 1
    assert len(body) == 2
    assert body[0]["type"] == "Let"
    assert body[0]["name"] == "i"
    assert body[0]["value"]["value"] == 0

    assert body[1]["type"] == "While"
    assert body[1]["test"]["op"] == "<"
    assert body[1]["test"]["left"]["name"] == "i"
    assert body[1]["test"]["right"]["value"] == 5


def test_for_range_inclusive() -> None:
    """Test For loop with inclusive Range."""
    doc = {
        "version": "coreil-0.3",
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

    # Should use <= instead of <
    assert body[1]["type"] == "While"
    assert body[1]["test"]["op"] == "<="


def test_nested_for_loops() -> None:
    """Test nested For loops are properly lowered."""
    doc = {
        "version": "coreil-0.3",
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

    # Outer loop: Let i = 0; While ...
    assert body[0]["type"] == "Let"
    assert body[0]["name"] == "i"
    assert body[1]["type"] == "While"

    # Inner loop should also be lowered
    inner_body = body[1]["body"]
    # Inner body should have: Let j = 0; While ...; i = i + 1
    assert inner_body[0]["type"] == "Let"
    assert inner_body[0]["name"] == "j"
    assert inner_body[1]["type"] == "While"


def test_for_in_function() -> None:
    """Test For loops inside function definitions are lowered."""
    doc = {
        "version": "coreil-0.3",
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

    # Function body should have lowered For loop
    assert func_body[0]["type"] == "Let"
    assert func_body[1]["type"] == "While"


def main() -> None:
    test_for_range_basic()
    test_for_range_inclusive()
    test_nested_for_loops()
    test_for_in_function()
    print("All lowering tests passed.")


if __name__ == "__main__":
    main()

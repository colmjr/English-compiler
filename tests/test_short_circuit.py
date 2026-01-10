"""Test short-circuit evaluation for 'and' and 'or' operators."""

from english_compiler.coreil.interp import run_coreil


def test_and_short_circuit():
    """Test that 'and' operator short-circuits and doesn't evaluate right side when left is false."""
    # This should not raise an error because 'and' should short-circuit
    # When i >= len(arr), the right side (arr[i]) should not be evaluated
    doc = {
        "version": "coreil-0.5",
        "ambiguities": [],
        "body": [
            {
                "type": "Let",
                "name": "arr",
                "value": {"type": "Array", "items": [
                    {"type": "Literal", "value": 1},
                    {"type": "Literal", "value": 2},
                    {"type": "Literal", "value": 3}
                ]}
            },
            {
                "type": "Let",
                "name": "i",
                "value": {"type": "Literal", "value": 3}
            },
            {
                "type": "Let",
                "name": "result",
                "value": {
                    "type": "Binary",
                    "op": "and",
                    "left": {
                        "type": "Binary",
                        "op": "<",
                        "left": {"type": "Var", "name": "i"},
                        "right": {
                            "type": "Length",
                            "base": {"type": "Var", "name": "arr"}
                        }
                    },
                    "right": {
                        "type": "Binary",
                        "op": ">",
                        "left": {
                            "type": "Index",
                            "base": {"type": "Var", "name": "arr"},
                            "index": {"type": "Var", "name": "i"}
                        },
                        "right": {"type": "Literal", "value": 0}
                    }
                }
            },
            {
                "type": "Print",
                "args": [{"type": "Var", "name": "result"}]
            }
        ]
    }

    # This should work without raising "Index out of range" error
    # The fact that run_coreil completes without exception means short-circuit worked
    run_coreil(doc)


def test_or_short_circuit():
    """Test that 'or' operator short-circuits and doesn't evaluate right side when left is true."""
    doc = {
        "version": "coreil-0.5",
        "ambiguities": [],
        "body": [
            {
                "type": "Let",
                "name": "arr",
                "value": {"type": "Array", "items": [
                    {"type": "Literal", "value": 1},
                    {"type": "Literal", "value": 2}
                ]}
            },
            {
                "type": "Let",
                "name": "i",
                "value": {"type": "Literal", "value": 5}
            },
            {
                "type": "Let",
                "name": "result",
                "value": {
                    "type": "Binary",
                    "op": "or",
                    "left": {
                        "type": "Binary",
                        "op": ">=",
                        "left": {"type": "Var", "name": "i"},
                        "right": {
                            "type": "Length",
                            "base": {"type": "Var", "name": "arr"}
                        }
                    },
                    "right": {
                        "type": "Binary",
                        "op": ">",
                        "left": {
                            "type": "Index",
                            "base": {"type": "Var", "name": "arr"},
                            "index": {"type": "Var", "name": "i"}
                        },
                        "right": {"type": "Literal", "value": 0}
                    }
                }
            },
            {
                "type": "Print",
                "args": [{"type": "Var", "name": "result"}]
            }
        ]
    }

    # This should work without raising "Index out of range" error
    # The fact that run_coreil completes without exception means short-circuit worked
    run_coreil(doc)


if __name__ == "__main__":
    test_and_short_circuit()
    print("✓ test_and_short_circuit passed")
    test_or_short_circuit()
    print("✓ test_or_short_circuit passed")
    print("\nAll short-circuit tests passed!")

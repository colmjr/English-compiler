"""JavaScript backend edge case tests.

Tests for JavaScript-specific behaviors and edge cases in the emit_javascript module.
Run with: python -m tests.test_javascript
"""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from english_compiler.coreil.emit_javascript import emit_javascript
from english_compiler.coreil.interp import run_coreil


# Check if Node.js is available
_NODE_AVAILABLE = shutil.which("node") is not None


def _run_js(code: str) -> str:
    """Execute JavaScript code and return stdout."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["node", tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(f"JavaScript execution failed: {result.stderr}")
        return result.stdout
    finally:
        Path(tmp_path).unlink()


def _run_interp(doc: dict) -> str:
    """Run Core IL interpreter and return stdout."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        run_coreil(doc)
    return buf.getvalue()


def _test_parity(doc: dict, test_name: str) -> None:
    """Test that interpreter and JavaScript produce identical output."""
    interp_output = _run_interp(doc)
    js_code = emit_javascript(doc)
    js_output = _run_js(js_code)
    if interp_output != js_output:
        print(f"FAILED: {test_name}")
        print(f"  Interpreter: {interp_output!r}")
        print(f"  JavaScript:  {js_output!r}")
        raise AssertionError(f"Output mismatch in {test_name}")
    print(f"  {test_name}: ✓")


def test_literals():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Print", "args": [{"type": "Literal", "value": 42}]},
            {"type": "Print", "args": [{"type": "Literal", "value": "hello"}]},
            {"type": "Print", "args": [{"type": "Literal", "value": True}]},
            {"type": "Print", "args": [{"type": "Literal", "value": False}]},
            {"type": "Print", "args": [{"type": "Literal", "value": None}]},
        ]
    }
    _test_parity(doc, "literals")


def test_string_escapes():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Print", "args": [{"type": "Literal", "value": "line1\nline2"}]},
            {"type": "Print", "args": [{"type": "Literal", "value": "tab\there"}]},
            {"type": "Print", "args": [{"type": "Literal", "value": 'quote"inside'}]},
        ]
    }
    _test_parity(doc, "string_escapes")


def test_binary_operators():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Print", "args": [
                {"type": "Binary", "op": "+", "left": {"type": "Literal", "value": 1}, "right": {"type": "Literal", "value": 2}}
            ]},
            {"type": "Print", "args": [
                {"type": "Binary", "op": "*", "left": {"type": "Literal", "value": 3}, "right": {"type": "Literal", "value": 4}}
            ]},
            {"type": "Print", "args": [
                {"type": "Binary", "op": "==", "left": {"type": "Literal", "value": 5}, "right": {"type": "Literal", "value": 5}}
            ]},
            {"type": "Print", "args": [
                {"type": "Binary", "op": "!=", "left": {"type": "Literal", "value": 1}, "right": {"type": "Literal", "value": 2}}
            ]},
        ]
    }
    _test_parity(doc, "binary_operators")


def test_short_circuit():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Print", "args": [
                {"type": "Binary", "op": "and",
                 "left": {"type": "Literal", "value": False},
                 "right": {"type": "Literal", "value": True}}
            ]},
            {"type": "Print", "args": [
                {"type": "Binary", "op": "or",
                 "left": {"type": "Literal", "value": True},
                 "right": {"type": "Literal", "value": False}}
            ]},
        ]
    }
    _test_parity(doc, "short_circuit")


def test_array_basic():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Let", "name": "arr", "value": {"type": "Array", "items": [
                {"type": "Literal", "value": 1},
                {"type": "Literal", "value": 2},
                {"type": "Literal", "value": 3},
            ]}},
            {"type": "Print", "args": [{"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {"type": "Literal", "value": 0}}]},
            {"type": "Print", "args": [{"type": "Length", "base": {"type": "Var", "name": "arr"}}]},
        ]
    }
    _test_parity(doc, "array_basic")


def test_array_push():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Let", "name": "arr", "value": {"type": "Array", "items": []}},
            {"type": "Push", "base": {"type": "Var", "name": "arr"}, "value": {"type": "Literal", "value": 42}},
            {"type": "Print", "args": [{"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {"type": "Literal", "value": 0}}]},
        ]
    }
    _test_parity(doc, "array_push")


def test_map_basic():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Let", "name": "m", "value": {"type": "Map", "items": [
                {"key": {"type": "Literal", "value": "a"}, "value": {"type": "Literal", "value": 1}},
                {"key": {"type": "Literal", "value": "b"}, "value": {"type": "Literal", "value": 2}},
            ]}},
            {"type": "Print", "args": [{"type": "Get", "base": {"type": "Var", "name": "m"}, "key": {"type": "Literal", "value": "a"}}]},
            {"type": "Print", "args": [{"type": "GetDefault", "base": {"type": "Var", "name": "m"}, "key": {"type": "Literal", "value": "c"}, "default": {"type": "Literal", "value": 99}}]},
        ]
    }
    _test_parity(doc, "map_basic")


def test_set_basic():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Let", "name": "s", "value": {"type": "Set", "items": [
                {"type": "Literal", "value": 1},
                {"type": "Literal", "value": 2},
            ]}},
            {"type": "Print", "args": [{"type": "SetHas", "base": {"type": "Var", "name": "s"}, "value": {"type": "Literal", "value": 1}}]},
            {"type": "Print", "args": [{"type": "SetHas", "base": {"type": "Var", "name": "s"}, "value": {"type": "Literal", "value": 3}}]},
            {"type": "Print", "args": [{"type": "SetSize", "base": {"type": "Var", "name": "s"}}]},
        ]
    }
    _test_parity(doc, "set_basic")


def test_deque():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Let", "name": "d", "value": {"type": "DequeNew"}},
            {"type": "PushBack", "base": {"type": "Var", "name": "d"}, "value": {"type": "Literal", "value": 1}},
            {"type": "PushBack", "base": {"type": "Var", "name": "d"}, "value": {"type": "Literal", "value": 2}},
            {"type": "PushFront", "base": {"type": "Var", "name": "d"}, "value": {"type": "Literal", "value": 0}},
            {"type": "Print", "args": [{"type": "DequeSize", "base": {"type": "Var", "name": "d"}}]},
            {"type": "PopFront", "base": {"type": "Var", "name": "d"}, "target": "x"},
            {"type": "Print", "args": [{"type": "Var", "name": "x"}]},
            {"type": "PopBack", "base": {"type": "Var", "name": "d"}, "target": "y"},
            {"type": "Print", "args": [{"type": "Var", "name": "y"}]},
        ]
    }
    _test_parity(doc, "deque")


def test_heap():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Let", "name": "h", "value": {"type": "HeapNew"}},
            {"type": "HeapPush", "base": {"type": "Var", "name": "h"}, "priority": {"type": "Literal", "value": 3}, "value": {"type": "Literal", "value": "three"}},
            {"type": "HeapPush", "base": {"type": "Var", "name": "h"}, "priority": {"type": "Literal", "value": 1}, "value": {"type": "Literal", "value": "one"}},
            {"type": "HeapPush", "base": {"type": "Var", "name": "h"}, "priority": {"type": "Literal", "value": 2}, "value": {"type": "Literal", "value": "two"}},
            {"type": "Print", "args": [{"type": "HeapSize", "base": {"type": "Var", "name": "h"}}]},
            {"type": "Print", "args": [{"type": "HeapPeek", "base": {"type": "Var", "name": "h"}}]},
            {"type": "HeapPop", "base": {"type": "Var", "name": "h"}, "target": "x"},
            {"type": "Print", "args": [{"type": "Var", "name": "x"}]},
            {"type": "HeapPop", "base": {"type": "Var", "name": "h"}, "target": "y"},
            {"type": "Print", "args": [{"type": "Var", "name": "y"}]},
        ]
    }
    _test_parity(doc, "heap")


def test_heap_stable_ordering():
    """Test that equal priorities maintain insertion order."""
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Let", "name": "h", "value": {"type": "HeapNew"}},
            {"type": "HeapPush", "base": {"type": "Var", "name": "h"}, "priority": {"type": "Literal", "value": 1}, "value": {"type": "Literal", "value": "first"}},
            {"type": "HeapPush", "base": {"type": "Var", "name": "h"}, "priority": {"type": "Literal", "value": 1}, "value": {"type": "Literal", "value": "second"}},
            {"type": "HeapPush", "base": {"type": "Var", "name": "h"}, "priority": {"type": "Literal", "value": 1}, "value": {"type": "Literal", "value": "third"}},
            {"type": "HeapPop", "base": {"type": "Var", "name": "h"}, "target": "a"},
            {"type": "HeapPop", "base": {"type": "Var", "name": "h"}, "target": "b"},
            {"type": "HeapPop", "base": {"type": "Var", "name": "h"}, "target": "c"},
            {"type": "Print", "args": [{"type": "Var", "name": "a"}]},
            {"type": "Print", "args": [{"type": "Var", "name": "b"}]},
            {"type": "Print", "args": [{"type": "Var", "name": "c"}]},
        ]
    }
    _test_parity(doc, "heap_stable_ordering")


def test_math():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Print", "args": [{"type": "Math", "op": "abs", "arg": {"type": "Literal", "value": -5}}]},
            {"type": "Print", "args": [{"type": "Math", "op": "floor", "arg": {"type": "Literal", "value": 3.7}}]},
            {"type": "Print", "args": [{"type": "Math", "op": "ceil", "arg": {"type": "Literal", "value": 3.2}}]},
            {"type": "Print", "args": [{"type": "Math", "op": "sqrt", "arg": {"type": "Literal", "value": 16}}]},
        ]
    }
    _test_parity(doc, "math")


def test_math_pow():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Print", "args": [{"type": "MathPow", "base": {"type": "Literal", "value": 2}, "exponent": {"type": "Literal", "value": 10}}]},
        ]
    }
    _test_parity(doc, "math_pow")


def test_strings():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Let", "name": "s", "value": {"type": "Literal", "value": "hello"}},
            {"type": "Print", "args": [{"type": "StringLength", "base": {"type": "Var", "name": "s"}}]},
            {"type": "Print", "args": [{"type": "CharAt", "base": {"type": "Var", "name": "s"}, "index": {"type": "Literal", "value": 1}}]},
            {"type": "Print", "args": [{"type": "Substring", "base": {"type": "Var", "name": "s"}, "start": {"type": "Literal", "value": 1}, "end": {"type": "Literal", "value": 4}}]},
        ]
    }
    _test_parity(doc, "strings")


def test_string_operations():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Print", "args": [{"type": "StringUpper", "base": {"type": "Literal", "value": "hello"}}]},
            {"type": "Print", "args": [{"type": "StringLower", "base": {"type": "Literal", "value": "HELLO"}}]},
            {"type": "Print", "args": [{"type": "StringTrim", "base": {"type": "Literal", "value": "  hello  "}}]},
            {"type": "Print", "args": [{"type": "StringStartsWith", "base": {"type": "Literal", "value": "hello"}, "prefix": {"type": "Literal", "value": "he"}}]},
            {"type": "Print", "args": [{"type": "StringEndsWith", "base": {"type": "Literal", "value": "hello"}, "suffix": {"type": "Literal", "value": "lo"}}]},
            {"type": "Print", "args": [{"type": "StringContains", "base": {"type": "Literal", "value": "hello"}, "substring": {"type": "Literal", "value": "ell"}}]},
        ]
    }
    _test_parity(doc, "string_operations")


def test_join():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Print", "args": [{"type": "Join", "sep": {"type": "Literal", "value": ", "}, "items": {"type": "Array", "items": [
                {"type": "Literal", "value": "a"},
                {"type": "Literal", "value": "b"},
                {"type": "Literal", "value": "c"},
            ]}}]},
        ]
    }
    _test_parity(doc, "join")


def test_regex_match():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Print", "args": [{"type": "RegexMatch", "string": {"type": "Literal", "value": "hello world"}, "pattern": {"type": "Literal", "value": "world"}}]},
            {"type": "Print", "args": [{"type": "RegexMatch", "string": {"type": "Literal", "value": "hello world"}, "pattern": {"type": "Literal", "value": "xyz"}}]},
        ]
    }
    _test_parity(doc, "regex_match")


def test_regex_replace():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Print", "args": [{"type": "RegexReplace", "string": {"type": "Literal", "value": "hello world"}, "pattern": {"type": "Literal", "value": "o"}, "replacement": {"type": "Literal", "value": "0"}}]},
        ]
    }
    _test_parity(doc, "regex_replace")


def test_if_else():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "If",
             "test": {"type": "Binary", "op": ">", "left": {"type": "Literal", "value": 5}, "right": {"type": "Literal", "value": 3}},
             "then": [{"type": "Print", "args": [{"type": "Literal", "value": "yes"}]}],
             "else": [{"type": "Print", "args": [{"type": "Literal", "value": "no"}]}]},
        ]
    }
    _test_parity(doc, "if_else")


def test_while_loop():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Let", "name": "i", "value": {"type": "Literal", "value": 0}},
            {"type": "While",
             "test": {"type": "Binary", "op": "<", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 3}},
             "body": [
                 {"type": "Print", "args": [{"type": "Var", "name": "i"}]},
                 {"type": "Assign", "name": "i", "value": {"type": "Binary", "op": "+", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 1}}},
             ]},
        ]
    }
    _test_parity(doc, "while_loop")


def test_function():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "FuncDef", "name": "double", "params": ["x"], "body": [
                {"type": "Return", "value": {"type": "Binary", "op": "*", "left": {"type": "Var", "name": "x"}, "right": {"type": "Literal", "value": 2}}},
            ]},
            {"type": "Print", "args": [{"type": "Call", "name": "double", "args": [{"type": "Literal", "value": 21}]}]},
        ]
    }
    _test_parity(doc, "function")


def test_recursive_function():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "FuncDef", "name": "factorial", "params": ["n"], "body": [
                {"type": "If",
                 "test": {"type": "Binary", "op": "<=", "left": {"type": "Var", "name": "n"}, "right": {"type": "Literal", "value": 1}},
                 "then": [{"type": "Return", "value": {"type": "Literal", "value": 1}}]},
                {"type": "Return", "value": {"type": "Binary", "op": "*",
                                              "left": {"type": "Var", "name": "n"},
                                              "right": {"type": "Call", "name": "factorial", "args": [
                                                  {"type": "Binary", "op": "-", "left": {"type": "Var", "name": "n"}, "right": {"type": "Literal", "value": 1}}
                                              ]}}},
            ]},
            {"type": "Print", "args": [{"type": "Call", "name": "factorial", "args": [{"type": "Literal", "value": 5}]}]},
        ]
    }
    _test_parity(doc, "recursive_function")


def test_record():
    doc = {
        "version": "coreil-1.4",
        "body": [
            {"type": "Let", "name": "r", "value": {"type": "Record", "fields": [
                {"name": "x", "value": {"type": "Literal", "value": 1}},
                {"name": "y", "value": {"type": "Literal", "value": 2}},
            ]}},
            {"type": "Print", "args": [{"type": "GetField", "base": {"type": "Var", "name": "r"}, "name": "x"}]},
            {"type": "SetField", "base": {"type": "Var", "name": "r"}, "name": "x", "value": {"type": "Literal", "value": 10}},
            {"type": "Print", "args": [{"type": "GetField", "base": {"type": "Var", "name": "r"}, "name": "x"}]},
        ]
    }
    _test_parity(doc, "record")


def main() -> int:
    if not _NODE_AVAILABLE:
        print("Node.js not available - skipping JavaScript tests")
        return 0

    print("Running JavaScript edge case tests...\n")

    tests = [
        test_literals,
        test_string_escapes,
        test_binary_operators,
        test_short_circuit,
        test_array_basic,
        test_array_push,
        test_map_basic,
        test_set_basic,
        test_deque,
        test_heap,
        test_heap_stable_ordering,
        test_math,
        test_math_pow,
        test_strings,
        test_string_operations,
        test_join,
        test_regex_match,
        test_regex_replace,
        test_if_else,
        test_while_loop,
        test_function,
        test_recursive_function,
        test_record,
    ]

    failures = []
    for test in tests:
        try:
            test()
        except AssertionError as e:
            failures.append(str(e))
        except Exception as e:
            failures.append(f"{test.__name__}: {e}")
            print(f"  {test.__name__}: ✗ ({e})")

    print()
    if failures:
        print(f"{len(failures)}/{len(tests)} tests failed")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"All {len(tests)} JavaScript edge case tests passed! ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())

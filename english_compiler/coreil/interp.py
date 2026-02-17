"""Core IL interpreter.

This file implements Core IL v1.8 semantics interpreter.
Core IL v1.8 adds TryCatch and Throw for exception handling.

Key features:
- Short-circuit evaluation for 'and' and 'or' operators
- Tuple indexing and length support
- Dictionary insertion order preservation
- Record support (mutable named fields)
- Set operations (membership, add, remove, size)
- Deque operations (double-ended queue)
- Heap operations (min-heap priority queue)
- Math operations (sin, cos, tan, sqrt, floor, ceil, abs, log, exp, pow, pi, e)
- JSON operations (parse, stringify)
- Regex operations (match, findall, replace, split)
- Array slicing (Slice)
- Unary not (Not)
- Break and Continue loop control
- TryCatch and Throw exception handling
- Recursion limit: 100 calls

Version history:
- v1.8: Added TryCatch and Throw for exception handling
- v1.7: Added Break and Continue loop control statements
- v1.6: Added MethodCall and PropertyGet for OOP-style APIs (Tier 2, non-portable)
- v1.5: Added Slice for array/list slicing, Not for logical negation
- v1.4: Consolidated Math, JSON, and Regex operations
- v1.3: Added JsonParse, JsonStringify, RegexMatch, RegexFindAll, RegexReplace, RegexSplit
- v1.2: Added Math, MathPow, MathConst for portable math operations
- v1.1: Added Record, GetField, SetField, Set, Deque operations, String operations, Heap operations
- v1.0: Stable release (frozen)

Backward compatibility: Accepts v0.1 through v1.8 programs.
"""

from __future__ import annotations

import heapq
import json
import math
import re
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

from .constants import BINARY_OPS, MAX_CALL_DEPTH
from .emit_utils import parse_regex_flags
from .versions import SUPPORTED_VERSIONS, get_version_error_message


@dataclass
class _ReturnSignal(Exception):
    value: Any


class _BreakSignal(Exception):
    """Signal to break out of a loop."""
    pass


class _ContinueSignal(Exception):
    """Signal to continue to the next iteration of a loop."""
    pass


@dataclass
class _ThrowSignal(Exception):
    """Signal for explicit Throw statements."""
    message: str


def run_coreil(
    doc: dict,
    error_callback: Callable[[str], None] | None = None,
    step_callback: Callable | None = None,
) -> int:
    # Note: For/ForEach are handled natively (no lowering needed)
    # This ensures Continue works correctly in for loops

    global_env: dict[str, Any] = {}
    functions: dict[str, dict] = {}

    def lookup_var(name: str, local_env: dict[str, Any] | None) -> Any:
        if local_env is not None and name in local_env:
            return local_env[name]
        if name in global_env:
            return global_env[name]
        raise ValueError(f"variable '{name}' used before definition")

    def eval_expr(node: Any, local_env: dict[str, Any] | None, call_depth: int) -> Any:
        if not isinstance(node, dict):
            raise ValueError("expression must be an object")
        node_type = node.get("type")
        if node_type is None:
            raise ValueError("expression missing type")

        if node_type == "Literal":
            if "value" not in node:
                raise ValueError("Literal missing value")
            return node["value"]

        if node_type == "Var":
            name = node.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError("Var missing name")
            return lookup_var(name, local_env)

        if node_type == "Binary":
            op = node.get("op")
            if op not in BINARY_OPS:
                raise ValueError("Binary missing or invalid op")

            # Implement short-circuit evaluation for 'and' and 'or'
            if op == "and":
                left = eval_expr(node.get("left"), local_env, call_depth)
                if not left:
                    return False
                right = eval_expr(node.get("right"), local_env, call_depth)
                return bool(right)

            if op == "or":
                left = eval_expr(node.get("left"), local_env, call_depth)
                if left:
                    return True
                right = eval_expr(node.get("right"), local_env, call_depth)
                return bool(right)

            # For all other operators, evaluate both operands first
            left = eval_expr(node.get("left"), local_env, call_depth)
            right = eval_expr(node.get("right"), local_env, call_depth)
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                return left / right
            if op == "%":
                return left % right
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            if op == "<":
                return left < right
            if op == "<=":
                return left <= right
            if op == ">":
                return left > right
            if op == ">=":
                return left >= right
            raise ValueError("unsupported binary op")

        if node_type == "Array":
            items = node.get("items")
            if not isinstance(items, list):
                raise ValueError("Array items must be a list")
            return [eval_expr(item, local_env, call_depth) for item in items]

        if node_type == "Index":
            base = eval_expr(node.get("base"), local_env, call_depth)
            index = eval_expr(node.get("index"), local_env, call_depth)
            if not isinstance(index, int):
                raise ValueError("Index must be an integer")
            # Allow indexing into both arrays (lists) and tuples
            if not isinstance(base, (list, tuple)):
                raise ValueError("Index base must be an array or tuple")
            # Support negative indexing (Python-style: -1 = last element)
            if index < -len(base) or index >= len(base):
                raise ValueError("Index out of range")
            return base[index]

        if node_type == "Slice":
            base = eval_expr(node.get("base"), local_env, call_depth)
            if not isinstance(base, (list, tuple)):
                raise ValueError(f"runtime error: Slice base must be an array or tuple, got {type(base).__name__}")
            start = eval_expr(node["start"], local_env, call_depth)
            end = eval_expr(node["end"], local_env, call_depth)
            if not isinstance(start, int):
                raise ValueError(f"runtime error: Slice start must be an integer, got {start}")
            if not isinstance(end, int):
                raise ValueError(f"runtime error: Slice end must be an integer, got {end}")
            # Support negative indexing (Python-style: -1 = last element)
            n = len(base)
            if start < 0:
                start = n + start
            if end < 0:
                end = n + end
            if start < 0 or start > n or end < 0 or end > n:
                raise ValueError(f"runtime error: Slice range [{start}:{end}) out of bounds for array of length {n}")
            return list(base[start:end])

        if node_type == "Not":
            arg = eval_expr(node.get("arg"), local_env, call_depth)
            return not arg

        if node_type == "Length":
            base = eval_expr(node.get("base"), local_env, call_depth)
            # Allow length of both arrays (lists) and tuples
            if not isinstance(base, (list, tuple)):
                raise ValueError("Length base must be an array or tuple")
            return len(base)

        if node_type == "Map":
            items = node.get("items")
            if not isinstance(items, list):
                raise ValueError("Map items must be a list")
            result = {}
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError("Map item must be an object")
                key = eval_expr(item.get("key"), local_env, call_depth)
                # v0.4 backward compatibility: convert list keys to tuples (hashable)
                if isinstance(key, list):
                    key = tuple(key)
                # Allow tuples as keys (hashable)
                if not isinstance(key, (str, int, tuple)):
                    raise ValueError("Map key must be a string, integer, or tuple")
                value = eval_expr(item.get("value"), local_env, call_depth)
                result[key] = value
            return result

        if node_type == "Get":
            base = eval_expr(node.get("base"), local_env, call_depth)
            key = eval_expr(node.get("key"), local_env, call_depth)
            if not isinstance(base, dict):
                raise ValueError("Get base must be a map")
            # v0.4 backward compatibility: convert list keys to tuples
            if isinstance(key, list):
                key = tuple(key)
            if not isinstance(key, (str, int, tuple)):
                raise ValueError("Get key must be a string, integer, or tuple")
            return base.get(key)

        if node_type == "GetDefault":
            base = eval_expr(node.get("base"), local_env, call_depth)
            key = eval_expr(node.get("key"), local_env, call_depth)
            default = eval_expr(node.get("default"), local_env, call_depth)
            if not isinstance(base, dict):
                raise ValueError("GetDefault base must be a map")
            # v0.4 backward compatibility: convert list keys to tuples
            if isinstance(key, list):
                key = tuple(key)
            if not isinstance(key, (str, int, tuple)):
                raise ValueError("GetDefault key must be a string, integer, or tuple")
            return base.get(key, default)

        if node_type == "Keys":
            base = eval_expr(node.get("base"), local_env, call_depth)
            if not isinstance(base, dict):
                raise ValueError("Keys base must be a map")
            # Return keys sorted for determinism (if comparable)
            try:
                # For tuples with mixed types, compare as tuples
                return sorted(base.keys())
            except TypeError:
                # Mixed types or uncomparable types - preserve insertion order
                return list(base.keys())

        if node_type == "Tuple":
            items = node.get("items")
            if not isinstance(items, list):
                raise ValueError("Tuple items must be a list")
            return tuple(eval_expr(item, local_env, call_depth) for item in items)

        if node_type == "Record":
            fields = node.get("fields")
            if not isinstance(fields, list):
                raise ValueError("Record fields must be a list")
            record = {}
            for field in fields:
                if not isinstance(field, dict):
                    raise ValueError("Record field must be an object")
                name = field.get("name")
                if not isinstance(name, str):
                    raise ValueError("Record field name must be a string")
                value = eval_expr(field["value"], local_env, call_depth)
                record[name] = value
            return record

        if node_type == "GetField":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, dict):
                raise ValueError(f"runtime error: GetField base must be a record, got {type(base).__name__}")
            name = node.get("name")
            if not isinstance(name, str):
                raise ValueError("GetField name must be a string")
            if name not in base:
                raise ValueError(f"runtime error: field '{name}' not found in record")
            return base[name]

        if node_type == "StringLength":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, str):
                raise ValueError(f"runtime error: StringLength base must be a string, got {type(base).__name__}")
            return len(base)

        if node_type == "Substring":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, str):
                raise ValueError(f"runtime error: Substring base must be a string, got {type(base).__name__}")
            start = eval_expr(node["start"], local_env, call_depth)
            end = eval_expr(node["end"], local_env, call_depth)
            if not isinstance(start, int) or start < 0:
                raise ValueError(f"runtime error: Substring start must be a non-negative integer, got {start}")
            if not isinstance(end, int) or end < 0:
                raise ValueError(f"runtime error: Substring end must be a non-negative integer, got {end}")
            # Python slicing automatically clamps, but we raise error for out-of-range
            if start > len(base) or end > len(base):
                raise ValueError(f"runtime error: Substring range [{start}:{end}) out of bounds for string of length {len(base)}")
            return base[start:end]

        if node_type == "CharAt":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, str):
                raise ValueError(f"runtime error: CharAt base must be a string, got {type(base).__name__}")
            index = eval_expr(node["index"], local_env, call_depth)
            if not isinstance(index, int) or index < 0:
                raise ValueError(f"runtime error: CharAt index must be a non-negative integer, got {index}")
            if index >= len(base):
                raise ValueError(f"runtime error: CharAt index {index} out of bounds for string of length {len(base)}")
            return base[index]

        if node_type == "Join":
            sep = eval_expr(node["sep"], local_env, call_depth)
            if not isinstance(sep, str):
                raise ValueError(f"runtime error: Join separator must be a string, got {type(sep).__name__}")
            items = eval_expr(node["items"], local_env, call_depth)
            if not isinstance(items, list):
                raise ValueError(f"runtime error: Join items must be an array, got {type(items).__name__}")
            # Convert all items to strings
            str_items = [str(item) for item in items]
            return sep.join(str_items)

        # String operations (v1.4)
        if node_type == "StringSplit":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, str):
                raise ValueError(f"runtime error: StringSplit base must be a string, got {type(base).__name__}")
            delimiter = eval_expr(node["delimiter"], local_env, call_depth)
            if not isinstance(delimiter, str):
                raise ValueError(f"runtime error: StringSplit delimiter must be a string, got {type(delimiter).__name__}")
            return base.split(delimiter)

        if node_type == "StringTrim":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, str):
                raise ValueError(f"runtime error: StringTrim base must be a string, got {type(base).__name__}")
            return base.strip()

        if node_type == "StringUpper":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, str):
                raise ValueError(f"runtime error: StringUpper base must be a string, got {type(base).__name__}")
            return base.upper()

        if node_type == "StringLower":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, str):
                raise ValueError(f"runtime error: StringLower base must be a string, got {type(base).__name__}")
            return base.lower()

        if node_type == "StringStartsWith":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, str):
                raise ValueError(f"runtime error: StringStartsWith base must be a string, got {type(base).__name__}")
            prefix = eval_expr(node["prefix"], local_env, call_depth)
            if not isinstance(prefix, str):
                raise ValueError(f"runtime error: StringStartsWith prefix must be a string, got {type(prefix).__name__}")
            return base.startswith(prefix)

        if node_type == "StringEndsWith":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, str):
                raise ValueError(f"runtime error: StringEndsWith base must be a string, got {type(base).__name__}")
            suffix = eval_expr(node["suffix"], local_env, call_depth)
            if not isinstance(suffix, str):
                raise ValueError(f"runtime error: StringEndsWith suffix must be a string, got {type(suffix).__name__}")
            return base.endswith(suffix)

        if node_type == "StringContains":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, str):
                raise ValueError(f"runtime error: StringContains base must be a string, got {type(base).__name__}")
            substring = eval_expr(node["substring"], local_env, call_depth)
            if not isinstance(substring, str):
                raise ValueError(f"runtime error: StringContains substring must be a string, got {type(substring).__name__}")
            return substring in base

        if node_type == "StringReplace":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, str):
                raise ValueError(f"runtime error: StringReplace base must be a string, got {type(base).__name__}")
            old = eval_expr(node["old"], local_env, call_depth)
            if not isinstance(old, str):
                raise ValueError(f"runtime error: StringReplace old must be a string, got {type(old).__name__}")
            new = eval_expr(node["new"], local_env, call_depth)
            if not isinstance(new, str):
                raise ValueError(f"runtime error: StringReplace new must be a string, got {type(new).__name__}")
            return base.replace(old, new)

        if node_type == "Set":
            items = node.get("items", [])
            result_set = set()
            for item_node in items:
                item_value = eval_expr(item_node, local_env, call_depth)
                # Check if value is hashable (numbers, strings, tuples)
                if not isinstance(item_value, (int, float, str, bool, tuple)):
                    raise ValueError(f"runtime error: Set items must be hashable (numbers, strings, tuples), got {type(item_value).__name__}")
                result_set.add(item_value)
            return result_set

        if node_type == "SetHas":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, set):
                raise ValueError(f"runtime error: SetHas base must be a set, got {type(base).__name__}")
            value = eval_expr(node["value"], local_env, call_depth)
            return value in base

        if node_type == "SetSize":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, set):
                raise ValueError(f"runtime error: SetSize base must be a set, got {type(base).__name__}")
            return len(base)

        if node_type == "DequeNew":
            return deque()

        if node_type == "DequeSize":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, deque):
                raise ValueError(f"runtime error: DequeSize base must be a deque, got {type(base).__name__}")
            return len(base)

        if node_type == "HeapNew":
            # Return a dict with items list and counter for stable ordering
            return {"_heap_items": [], "_heap_counter": 0}

        if node_type == "HeapSize":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, dict) or "_heap_items" not in base:
                raise ValueError(f"runtime error: HeapSize base must be a heap, got {type(base).__name__}")
            return len(base["_heap_items"])

        if node_type == "HeapPeek":
            base = eval_expr(node["base"], local_env, call_depth)
            if not isinstance(base, dict) or "_heap_items" not in base:
                raise ValueError(f"runtime error: HeapPeek base must be a heap, got {type(base).__name__}")
            if len(base["_heap_items"]) == 0:
                raise ValueError("runtime error: cannot peek from empty heap")
            # Return the value (third element of the tuple: priority, counter, value)
            return base["_heap_items"][0][2]

        if node_type == "Call":
            return call_any(node, local_env, call_depth)

        # Type conversions (v1.9)
        if node_type == "ToInt":
            value = eval_expr(node.get("value"), local_env, call_depth)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
            if isinstance(value, float):
                return int(value)
            if isinstance(value, str):
                try:
                    return int(value)
                except ValueError:
                    raise ValueError(f"runtime error: cannot convert string '{value}' to int")
            raise ValueError(f"runtime error: cannot convert {type(value).__name__} to int")

        if node_type == "ToFloat":
            value = eval_expr(node.get("value"), local_env, call_depth)
            if isinstance(value, float):
                return value
            if isinstance(value, int) and not isinstance(value, bool):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    raise ValueError(f"runtime error: cannot convert string '{value}' to float")
            raise ValueError(f"runtime error: cannot convert {type(value).__name__} to float")

        if node_type == "ToString":
            value = eval_expr(node.get("value"), local_env, call_depth)
            if isinstance(value, bool):
                return "True" if value else "False"
            if value is None:
                return "None"
            return str(value)

        # Math operations (v1.2)
        if node_type == "Math":
            op = node.get("op")
            arg = eval_expr(node.get("arg"), local_env, call_depth)
            ops = {
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "sqrt": math.sqrt,
                "floor": math.floor,
                "ceil": math.ceil,
                "abs": abs,
                "log": math.log,
                "exp": math.exp,
            }
            if op not in ops:
                raise ValueError(f"unknown math op '{op}'")
            return ops[op](arg)

        if node_type == "MathPow":
            base = eval_expr(node.get("base"), local_env, call_depth)
            exponent = eval_expr(node.get("exponent"), local_env, call_depth)
            return math.pow(base, exponent)

        if node_type == "MathConst":
            name = node.get("name")
            if name == "pi":
                return math.pi
            elif name == "e":
                return math.e
            else:
                raise ValueError(f"unknown math constant '{name}'")

        # JSON operations (v1.3)
        if node_type == "JsonParse":
            source = eval_expr(node.get("source"), local_env, call_depth)
            if not isinstance(source, str):
                raise ValueError(f"runtime error: JsonParse source must be a string, got {type(source).__name__}")
            try:
                return json.loads(source)
            except json.JSONDecodeError as e:
                raise ValueError(f"runtime error: invalid JSON: {e}")

        if node_type == "JsonStringify":
            value = eval_expr(node.get("value"), local_env, call_depth)
            pretty = node.get("pretty")
            indent = None
            if pretty:
                pretty_val = eval_expr(pretty, local_env, call_depth)
                if pretty_val:
                    indent = 2
            # Handle non-serializable types
            def default_serializer(obj):
                if isinstance(obj, set):
                    return list(obj)
                if isinstance(obj, deque):
                    return list(obj)
                if hasattr(obj, '__iter__') and not isinstance(obj, (str, dict, list)):
                    return list(obj)
                raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
            return json.dumps(value, indent=indent, default=default_serializer)

        # Regex operations (v1.3)
        def _eval_regex_args(node, op_name):
            """Evaluate common regex arguments: string, pattern, flags."""
            string = eval_expr(node.get("string"), local_env, call_depth)
            if not isinstance(string, str):
                raise ValueError(f"runtime error: {op_name} string must be a string, got {type(string).__name__}")
            pattern = eval_expr(node.get("pattern"), local_env, call_depth)
            if not isinstance(pattern, str):
                raise ValueError(f"runtime error: {op_name} pattern must be a string, got {type(pattern).__name__}")
            flags_node = node.get("flags")
            flags_str = ""
            if flags_node:
                flags_str = eval_expr(flags_node, local_env, call_depth) or ""
            flags = parse_regex_flags(flags_str)
            return string, pattern, flags

        if node_type == "RegexMatch":
            string, pattern, flags = _eval_regex_args(node, "RegexMatch")
            try:
                match = re.search(pattern, string, flags)
                return match is not None
            except re.error as e:
                raise ValueError(f"runtime error: invalid regex pattern: {e}")

        if node_type == "RegexFindAll":
            string, pattern, flags = _eval_regex_args(node, "RegexFindAll")
            try:
                return re.findall(pattern, string, flags)
            except re.error as e:
                raise ValueError(f"runtime error: invalid regex pattern: {e}")

        if node_type == "RegexReplace":
            string, pattern, flags = _eval_regex_args(node, "RegexReplace")
            replacement = eval_expr(node.get("replacement"), local_env, call_depth)
            if not isinstance(replacement, str):
                raise ValueError(f"runtime error: RegexReplace replacement must be a string, got {type(replacement).__name__}")
            try:
                return re.sub(pattern, replacement, string, flags=flags)
            except re.error as e:
                raise ValueError(f"runtime error: invalid regex pattern: {e}")

        if node_type == "RegexSplit":
            string, pattern, flags = _eval_regex_args(node, "RegexSplit")
            maxsplit_node = node.get("maxsplit")
            maxsplit = 0  # 0 means no limit in re.split
            if maxsplit_node:
                maxsplit = eval_expr(maxsplit_node, local_env, call_depth)
                if not isinstance(maxsplit, int) or maxsplit < 0:
                    raise ValueError(f"runtime error: RegexSplit maxsplit must be a non-negative integer, got {maxsplit}")
            try:
                return re.split(pattern, string, maxsplit=maxsplit, flags=flags)
            except re.error as e:
                raise ValueError(f"runtime error: invalid regex pattern: {e}")

        # External call (Tier 2, non-portable)
        if node_type == "ExternalCall":
            module = node.get("module")
            function = node.get("function")
            # Evaluate args but don't execute - just raise error for now
            args = node.get("args", [])
            _ = [eval_expr(arg, local_env, call_depth) for arg in args]
            raise ValueError(
                f"runtime error: ExternalCall to {module}.{function} is not supported in interpreter. "
                f"External calls are platform-specific and require a compatible backend."
            )

        # MethodCall (Tier 2, non-portable, v1.6)
        if node_type == "MethodCall":
            _ = eval_expr(node.get("object"), local_env, call_depth)
            method = node.get("method")
            args = node.get("args", [])
            _ = [eval_expr(arg, local_env, call_depth) for arg in args]
            raise ValueError(
                f"runtime error: MethodCall to {method} is not supported in interpreter. "
                f"Method calls are platform-specific and require a compatible backend."
            )

        # PropertyGet (Tier 2, non-portable, v1.6)
        if node_type == "PropertyGet":
            _ = eval_expr(node.get("object"), local_env, call_depth)
            prop = node.get("property")
            raise ValueError(
                f"runtime error: PropertyGet for {prop} is not supported in interpreter. "
                f"Property access is platform-specific and requires a compatible backend."
            )

        raise ValueError(f"unexpected expression type '{node_type}'")

    def call_builtin(name: str, args: list[Any]) -> Any:
        if name == "print":
            print(" ".join(str(value) for value in args))
            return None
        if name == "input":
            prompt = ""
            if args:
                prompt = str(args[0])
            return input(prompt)
        # v0.4 backward compatibility: support helper functions as builtins
        if name == "get_or_default":
            if len(args) != 3:
                raise ValueError("get_or_default expects 3 arguments")
            d, key, default = args
            if not isinstance(d, dict):
                raise ValueError("get_or_default base must be a map")
            return d.get(key, default)
        if name == "entries":
            if len(args) != 1:
                raise ValueError("entries expects 1 argument")
            d = args[0]
            if not isinstance(d, dict):
                raise ValueError("entries base must be a map")
            return list(d.items())
        if name == "append":
            if len(args) != 2:
                raise ValueError("append expects 2 arguments")
            lst, value = args
            if not isinstance(lst, list):
                raise ValueError("append base must be an array")
            lst.append(value)
            return None
        raise ValueError(f"unknown builtin '{name}'")

    def call_function(name: str, args: list[Any], call_depth: int) -> Any:
        if call_depth >= MAX_CALL_DEPTH:
            raise ValueError("maximum call depth exceeded")
        func = functions.get(name)
        if func is None:
            raise ValueError(f"unknown function '{name}'")
        params = func.get("params", [])
        if len(args) != len(params):
            raise ValueError("argument count mismatch")
        local_env = dict(zip(params, args))
        try:
            exec_block(func.get("body", []), local_env, True, call_depth + 1)
        except _ReturnSignal as signal:
            return signal.value
        return None

    def call_any(node: dict, local_env: dict[str, Any] | None, call_depth: int) -> Any:
        name = node.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("Call missing name")
        args = node.get("args")
        if not isinstance(args, list):
            raise ValueError("Call missing args")
        values = [eval_expr(arg, local_env, call_depth) for arg in args]
        # Check builtins (including v0.4 compatibility helpers)
        if name in {"print", "input", "get_or_default", "entries", "append"}:
            return call_builtin(name, values)
        return call_function(name, values, call_depth)

    def exec_stmt(
        node: Any,
        local_env: dict[str, Any] | None,
        in_func: bool,
        call_depth: int,
    ) -> None:
        if not isinstance(node, dict):
            raise ValueError("statement must be an object")
        node_type = node.get("type")
        if node_type is None:
            raise ValueError("statement missing type")

        if node_type == "Let":
            name = node.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError("Let missing name")
            value = eval_expr(node.get("value"), local_env, call_depth)
            if in_func and local_env is not None:
                local_env[name] = value
            else:
                global_env[name] = value
            return

        if node_type == "Assign":
            name = node.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError("Assign missing name")
            value = eval_expr(node.get("value"), local_env, call_depth)
            if in_func and local_env is not None:
                local_env[name] = value
            else:
                global_env[name] = value
            return

        if node_type == "If":
            test = eval_expr(node.get("test"), local_env, call_depth)
            branch = node.get("then") if test else node.get("else", [])
            if not isinstance(branch, list):
                raise ValueError("If branch must be a list")
            exec_block(branch, local_env, in_func, call_depth)
            return

        if node_type == "Switch":
            test_val = eval_expr(node.get("test"), local_env, call_depth)
            matched = False
            for case in node.get("cases", []):
                case_val = eval_expr(case["value"], local_env, call_depth)
                if test_val == case_val:
                    exec_block(case["body"], local_env, in_func, call_depth)
                    matched = True
                    break
            if not matched:
                default = node.get("default")
                if default is not None:
                    exec_block(default, local_env, in_func, call_depth)
            return

        if node_type == "While":
            body = node.get("body")
            if not isinstance(body, list):
                raise ValueError("While body must be a list")
            while eval_expr(node.get("test"), local_env, call_depth):
                try:
                    exec_block(body, local_env, in_func, call_depth)
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    break
            return

        if node_type == "For":
            var = node.get("var")
            if not isinstance(var, str):
                raise ValueError("For var must be a string")
            iter_expr = node.get("iter")
            body = node.get("body")
            if not isinstance(body, list):
                raise ValueError("For body must be a list")

            # Determine where to store loop variable
            env = local_env if (in_func and local_env is not None) else global_env

            # Evaluate iterator
            if isinstance(iter_expr, dict) and iter_expr.get("type") == "Range":
                from_val = eval_expr(iter_expr.get("from"), local_env, call_depth)
                to_val = eval_expr(iter_expr.get("to"), local_env, call_depth)
                inclusive = iter_expr.get("inclusive", False)
                if not isinstance(from_val, int) or not isinstance(to_val, int):
                    raise ValueError("Range bounds must be integers")
                end = to_val + 1 if inclusive else to_val
                iterator = range(from_val, end)
            else:
                iterator = eval_expr(iter_expr, local_env, call_depth)
                if not isinstance(iterator, (list, tuple)):
                    raise ValueError("For iterator must be an array or tuple")

            for val in iterator:
                env[var] = val
                try:
                    exec_block(body, local_env, in_func, call_depth)
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    break
            return

        if node_type == "ForEach":
            var = node.get("var")
            if not isinstance(var, str):
                raise ValueError("ForEach var must be a string")
            iter_expr = node.get("iter")
            body = node.get("body")
            if not isinstance(body, list):
                raise ValueError("ForEach body must be a list")

            # Determine where to store loop variable
            env = local_env if (in_func and local_env is not None) else global_env

            # Evaluate iterator
            iterator = eval_expr(iter_expr, local_env, call_depth)
            if not isinstance(iterator, (list, tuple)):
                raise ValueError("ForEach iterator must be an array or tuple")

            for val in iterator:
                env[var] = val
                try:
                    exec_block(body, local_env, in_func, call_depth)
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    break
            return

        if node_type == "Call":
            call_any(node, local_env, call_depth)
            return

        if node_type == "Print":
            args = node.get("args")
            if not isinstance(args, list):
                raise ValueError("Print args must be a list")
            values = [eval_expr(arg, local_env, call_depth) for arg in args]
            print(" ".join(str(value) for value in values))
            return

        if node_type == "SetIndex":
            base = eval_expr(node.get("base"), local_env, call_depth)
            index = eval_expr(node.get("index"), local_env, call_depth)
            value = eval_expr(node.get("value"), local_env, call_depth)
            if not isinstance(index, int):
                raise ValueError("SetIndex index must be an integer")
            if not isinstance(base, list):
                raise ValueError("SetIndex base must be an array")
            # Support negative indexing (Python-style: -1 = last element)
            if index < -len(base) or index >= len(base):
                raise ValueError("SetIndex index out of range")
            base[index] = value
            return

        if node_type == "Set":
            base = eval_expr(node.get("base"), local_env, call_depth)
            key = eval_expr(node.get("key"), local_env, call_depth)
            value = eval_expr(node.get("value"), local_env, call_depth)
            if not isinstance(base, dict):
                raise ValueError("Set base must be a map")
            # v0.4 backward compatibility: convert list keys to tuples
            if isinstance(key, list):
                key = tuple(key)
            if not isinstance(key, (str, int, tuple)):
                raise ValueError("Set key must be a string, integer, or tuple")
            base[key] = value
            return

        if node_type == "Push":
            base = eval_expr(node.get("base"), local_env, call_depth)
            value = eval_expr(node.get("value"), local_env, call_depth)
            if not isinstance(base, list):
                raise ValueError("Push base must be an array")
            base.append(value)
            return

        if node_type == "SetField":
            base = eval_expr(node.get("base"), local_env, call_depth)
            if not isinstance(base, dict):
                raise ValueError(f"runtime error: SetField base must be a record, got {type(base).__name__}")
            name = node.get("name")
            if not isinstance(name, str):
                raise ValueError("SetField name must be a string")
            value = eval_expr(node.get("value"), local_env, call_depth)
            base[name] = value
            return

        if node_type == "SetAdd":
            base = eval_expr(node.get("base"), local_env, call_depth)
            if not isinstance(base, set):
                raise ValueError(f"runtime error: SetAdd base must be a set, got {type(base).__name__}")
            value = eval_expr(node.get("value"), local_env, call_depth)
            # Check if value is hashable (numbers, strings, tuples)
            if not isinstance(value, (int, float, str, bool, tuple)):
                raise ValueError(f"runtime error: SetAdd value must be hashable (numbers, strings, tuples), got {type(value).__name__}")
            base.add(value)
            return

        if node_type == "SetRemove":
            base = eval_expr(node.get("base"), local_env, call_depth)
            if not isinstance(base, set):
                raise ValueError(f"runtime error: SetRemove base must be a set, got {type(base).__name__}")
            value = eval_expr(node.get("value"), local_env, call_depth)
            # Use discard for no-op semantics (doesn't error if value not present)
            base.discard(value)
            return

        if node_type == "PushBack":
            base = eval_expr(node.get("base"), local_env, call_depth)
            if not isinstance(base, deque):
                raise ValueError(f"runtime error: PushBack base must be a deque, got {type(base).__name__}")
            value = eval_expr(node.get("value"), local_env, call_depth)
            base.append(value)
            return

        if node_type == "PushFront":
            base = eval_expr(node.get("base"), local_env, call_depth)
            if not isinstance(base, deque):
                raise ValueError(f"runtime error: PushFront base must be a deque, got {type(base).__name__}")
            value = eval_expr(node.get("value"), local_env, call_depth)
            base.appendleft(value)
            return

        if node_type == "PopFront":
            base = eval_expr(node.get("base"), local_env, call_depth)
            if not isinstance(base, deque):
                raise ValueError(f"runtime error: PopFront base must be a deque, got {type(base).__name__}")
            if len(base) == 0:
                raise ValueError("runtime error: cannot pop from empty deque")
            target = node.get("target")
            if not isinstance(target, str):
                raise ValueError("PopFront target must be a variable name")
            popped_value = base.popleft()
            if local_env is not None:
                local_env[target] = popped_value
            else:
                global_env[target] = popped_value
            return

        if node_type == "PopBack":
            base = eval_expr(node.get("base"), local_env, call_depth)
            if not isinstance(base, deque):
                raise ValueError(f"runtime error: PopBack base must be a deque, got {type(base).__name__}")
            if len(base) == 0:
                raise ValueError("runtime error: cannot pop from empty deque")
            target = node.get("target")
            if not isinstance(target, str):
                raise ValueError("PopBack target must be a variable name")
            popped_value = base.pop()
            if local_env is not None:
                local_env[target] = popped_value
            else:
                global_env[target] = popped_value
            return

        if node_type == "HeapPush":
            base = eval_expr(node.get("base"), local_env, call_depth)
            if not isinstance(base, dict) or "_heap_items" not in base:
                raise ValueError(f"runtime error: HeapPush base must be a heap, got {type(base).__name__}")
            priority = eval_expr(node.get("priority"), local_env, call_depth)
            value = eval_expr(node.get("value"), local_env, call_depth)
            # Use counter for stable ordering
            counter = base["_heap_counter"]
            base["_heap_counter"] = counter + 1
            heapq.heappush(base["_heap_items"], (priority, counter, value))
            return

        if node_type == "HeapPop":
            base = eval_expr(node.get("base"), local_env, call_depth)
            if not isinstance(base, dict) or "_heap_items" not in base:
                raise ValueError(f"runtime error: HeapPop base must be a heap, got {type(base).__name__}")
            if len(base["_heap_items"]) == 0:
                raise ValueError("runtime error: cannot pop from empty heap")
            target = node.get("target")
            if not isinstance(target, str):
                raise ValueError("HeapPop target must be a variable name")
            # Pop the min element and extract the value (third element)
            _, _, popped_value = heapq.heappop(base["_heap_items"])
            if local_env is not None:
                local_env[target] = popped_value
            else:
                global_env[target] = popped_value
            return

        if node_type == "FuncDef":
            name = node.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError("FuncDef missing name")
            functions[name] = node
            return

        if node_type == "Return":
            if not in_func:
                raise ValueError("Return outside function")
            if "value" in node:
                value = eval_expr(node.get("value"), local_env, call_depth)
            else:
                value = None
            raise _ReturnSignal(value)

        if node_type == "Break":
            raise _BreakSignal()

        if node_type == "Continue":
            raise _ContinueSignal()

        if node_type == "Throw":
            message = eval_expr(node.get("message"), local_env, call_depth)
            raise _ThrowSignal(str(message))

        if node_type == "TryCatch":
            catch_var = node.get("catch_var")
            finally_body = node.get("finally_body")
            try:
                exec_block(node.get("body", []), local_env, in_func, call_depth)
            except (_ReturnSignal, _BreakSignal, _ContinueSignal):
                raise
            except _ThrowSignal as e:
                env = local_env if (in_func and local_env is not None) else global_env
                env[catch_var] = e.message
                exec_block(node.get("catch_body", []), local_env, in_func, call_depth)
            except Exception as e:
                env = local_env if (in_func and local_env is not None) else global_env
                env[catch_var] = str(e)
                exec_block(node.get("catch_body", []), local_env, in_func, call_depth)
            finally:
                if finally_body:
                    exec_block(finally_body, local_env, in_func, call_depth)
            return

        raise ValueError(f"unexpected statement type '{node_type}'")

    def exec_block(
        body: list[Any],
        local_env: dict[str, Any] | None,
        in_func: bool,
        call_depth: int,
    ) -> None:
        for i, stmt in enumerate(body):
            if step_callback is not None:
                step_callback(stmt, i, local_env, global_env, functions, call_depth)
            exec_stmt(stmt, local_env, in_func, call_depth)

    try:
        if not isinstance(doc, dict):
            raise ValueError("document must be an object")

        # Core IL Version Check (uses SUPPORTED_VERSIONS from versions.py as single source of truth)
        if doc.get("version") not in SUPPORTED_VERSIONS:
            raise ValueError(get_version_error_message())
        body = doc.get("body")
        if not isinstance(body, list):
            raise ValueError("body must be a list")
        exec_block(body, None, False, 0)
    except ValueError as exc:
        # Re-raise Tier 2 (non-portable) errors so caller can handle them
        if "ExternalCall" in str(exc) or "MethodCall" in str(exc) or "PropertyGet" in str(exc):
            raise
        error_msg = f"runtime error: {exc}"
        if error_callback:
            error_callback(error_msg)
        else:
            print(error_msg)
        return 1
    except Exception as exc:
        error_msg = f"runtime error: {exc}"
        if error_callback:
            error_callback(error_msg)
        else:
            print(error_msg)
        return 1

    return 0

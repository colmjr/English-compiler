"""Core IL interpreter.

This file implements Core IL v1.1 semantics interpreter.
Core IL v1.1 adds Record support for algorithm-friendly structured data.

Key features:
- Short-circuit evaluation for 'and' and 'or' operators
- Tuple indexing and length support
- Dictionary insertion order preservation
- Record support (mutable named fields)
- Recursion limit: 100 calls

Version history:
- v1.1: Added Record, GetField, SetField
- v1.0: Stable release (frozen)

Backward compatibility: Accepts v0.1 through v1.1 programs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_BINARY_OPS = {
    "+",
    "-",
    "*",
    "/",
    "%",
    "==",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    "and",
    "or",
}

_MAX_CALL_DEPTH = 1000


@dataclass
class _ReturnSignal(Exception):
    value: Any


def run_coreil(doc: dict) -> int:
    from english_compiler.coreil.lower import lower_coreil

    # Lower syntax sugar (For/Range) to core constructs (While)
    doc = lower_coreil(doc)

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
            if op not in _BINARY_OPS:
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
            if not isinstance(index, int) or index < 0:
                raise ValueError("Index must be a non-negative integer")
            # Allow indexing into both arrays (lists) and tuples
            if not isinstance(base, (list, tuple)):
                raise ValueError("Index base must be an array or tuple")
            if index >= len(base):
                raise ValueError("Index out of range")
            return base[index]

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

        if node_type == "Call":
            return call_any(node, local_env, call_depth)

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
        if call_depth >= _MAX_CALL_DEPTH:
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

        if node_type == "While":
            body = node.get("body")
            if not isinstance(body, list):
                raise ValueError("While body must be a list")
            while eval_expr(node.get("test"), local_env, call_depth):
                exec_block(body, local_env, in_func, call_depth)
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
            if not isinstance(index, int) or index < 0:
                raise ValueError("SetIndex index must be a non-negative integer")
            if not isinstance(base, list):
                raise ValueError("SetIndex base must be an array")
            if index >= len(base):
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

        raise ValueError(f"unexpected statement type '{node_type}'")

    def exec_block(
        body: list[Any],
        local_env: dict[str, Any] | None,
        in_func: bool,
        call_depth: int,
    ) -> None:
        for stmt in body:
            exec_stmt(stmt, local_env, in_func, call_depth)

    try:
        if not isinstance(doc, dict):
            raise ValueError("document must be an object")

        # Core IL Version Check
        # v1.1 is the current version (adds Record support)
        # v1.0 is stable and frozen
        # v0.1-v0.5 are accepted for backward compatibility
        if doc.get("version") not in {"coreil-0.1", "coreil-0.2", "coreil-0.3", "coreil-0.4", "coreil-0.5", "coreil-1.0", "coreil-1.1"}:
            raise ValueError("version must be 'coreil-0.1', 'coreil-0.2', 'coreil-0.3', 'coreil-0.4', 'coreil-0.5', 'coreil-1.0', or 'coreil-1.1'")
        body = doc.get("body")
        if not isinstance(body, list):
            raise ValueError("body must be a list")
        exec_block(body, None, False, 0)
    except Exception as exc:
        print(f"runtime error: {exc}")
        return 1

    return 0

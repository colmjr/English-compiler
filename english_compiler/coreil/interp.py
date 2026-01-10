"""Core IL interpreter."""

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
            if op == "and":
                return bool(left) and bool(right)
            if op == "or":
                return bool(left) or bool(right)
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
            if not isinstance(base, list):
                raise ValueError("Index base must be an array")
            if index >= len(base):
                raise ValueError("Index out of range")
            return base[index]

        if node_type == "Length":
            base = eval_expr(node.get("base"), local_env, call_depth)
            if not isinstance(base, list):
                raise ValueError("Length base must be an array")
            return len(base)

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
        if name in {"print", "input"}:
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
        if doc.get("version") not in {"coreil-0.1", "coreil-0.2", "coreil-0.3"}:
            raise ValueError("version must be 'coreil-0.1', 'coreil-0.2', or 'coreil-0.3'")
        body = doc.get("body")
        if not isinstance(body, list):
            raise ValueError("body must be a list")
        exec_block(body, None, False, 0)
    except Exception as exc:
        print(f"runtime error: {exc}")
        return 1

    return 0

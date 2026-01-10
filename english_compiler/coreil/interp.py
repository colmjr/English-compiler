"""Core IL interpreter."""

from __future__ import annotations

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


def run_coreil(doc: dict) -> int:
    env: dict[str, Any] = {}

    def eval_expr(node: Any) -> Any:
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
            if name not in env:
                raise ValueError(f"variable '{name}' used before definition")
            return env[name]

        if node_type == "Binary":
            op = node.get("op")
            if op not in _BINARY_OPS:
                raise ValueError("Binary missing or invalid op")
            left = eval_expr(node.get("left"))
            right = eval_expr(node.get("right"))
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
            return [eval_expr(item) for item in items]

        if node_type == "Index":
            base = eval_expr(node.get("base"))
            index = eval_expr(node.get("index"))
            if not isinstance(index, int) or index < 0:
                raise ValueError("Index must be a non-negative integer")
            if not isinstance(base, list):
                raise ValueError("Index base must be an array")
            if index >= len(base):
                raise ValueError("Index out of range")
            return base[index]

        if node_type == "Length":
            base = eval_expr(node.get("base"))
            if not isinstance(base, list):
                raise ValueError("Length base must be an array")
            return len(base)

        if node_type == "Call":
            return call_builtin(node)

        raise ValueError(f"unexpected expression type '{node_type}'")

    def call_builtin(node: dict) -> Any:
        name = node.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("Call missing name")
        args = node.get("args")
        if not isinstance(args, list):
            raise ValueError("Call missing args")
        values = [eval_expr(arg) for arg in args]
        if name == "print":
            print(" ".join(str(value) for value in values))
            return None
        if name == "input":
            prompt = ""
            if values:
                prompt = str(values[0])
            return input(prompt)
        raise ValueError(f"unknown builtin '{name}'")

    def exec_stmt(node: Any) -> None:
        if not isinstance(node, dict):
            raise ValueError("statement must be an object")
        node_type = node.get("type")
        if node_type is None:
            raise ValueError("statement missing type")

        if node_type == "Let":
            name = node.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError("Let missing name")
            env[name] = eval_expr(node.get("value"))
            return

        if node_type == "Assign":
            name = node.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError("Assign missing name")
            env[name] = eval_expr(node.get("value"))
            return

        if node_type == "If":
            test = eval_expr(node.get("test"))
            branch = node.get("then") if test else node.get("else", [])
            if not isinstance(branch, list):
                raise ValueError("If branch must be a list")
            for stmt in branch:
                exec_stmt(stmt)
            return

        if node_type == "While":
            body = node.get("body")
            if not isinstance(body, list):
                raise ValueError("While body must be a list")
            while eval_expr(node.get("test")):
                for stmt in body:
                    exec_stmt(stmt)
            return

        if node_type == "Call":
            call_builtin(node)
            return

        if node_type == "Print":
            args = node.get("args")
            if not isinstance(args, list):
                raise ValueError("Print args must be a list")
            values = [eval_expr(arg) for arg in args]
            print(" ".join(str(value) for value in values))
            return

        if node_type == "SetIndex":
            base = eval_expr(node.get("base"))
            index = eval_expr(node.get("index"))
            value = eval_expr(node.get("value"))
            if not isinstance(index, int) or index < 0:
                raise ValueError("SetIndex index must be a non-negative integer")
            if not isinstance(base, list):
                raise ValueError("SetIndex base must be an array")
            if index >= len(base):
                raise ValueError("SetIndex index out of range")
            base[index] = value
            return

        raise ValueError(f"unexpected statement type '{node_type}'")

    try:
        if not isinstance(doc, dict):
            raise ValueError("document must be an object")
        if doc.get("version") not in {"coreil-0.1", "coreil-0.2"}:
            raise ValueError("version must be 'coreil-0.1' or 'coreil-0.2'")
        body = doc.get("body")
        if not isinstance(body, list):
            raise ValueError("body must be a list")
        for stmt in body:
            exec_stmt(stmt)
    except Exception as exc:
        print(f"runtime error: {exc}")
        return 1

    return 0

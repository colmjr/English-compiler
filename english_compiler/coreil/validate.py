"""Core IL validation."""

from __future__ import annotations

from typing import Any


_ALLOWED_NODE_TYPES = {
    "Let",
    "Assign",
    "If",
    "While",
    "Call",
    "Print",
    "SetIndex",
    "FuncDef",
    "Return",
    "Literal",
    "Var",
    "Binary",
    "Array",
    "Index",
    "Length",
}

_ALLOWED_BINARY_OPS = {
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

_ALLOWED_VERSIONS = {"coreil-0.1", "coreil-0.2", "coreil-0.3"}


def validate_coreil(doc: dict) -> list[dict]:
    errors: list[dict] = []

    def add_error(path: str, message: str) -> None:
        errors.append({"message": message, "path": path})

    def expect_type(node: Any, path: str) -> str | None:
        if not isinstance(node, dict):
            add_error(path, "node must be an object")
            return None
        node_type = node.get("type")
        if node_type is None:
            add_error(f"{path}.type", "missing type")
            return None
        if node_type not in _ALLOWED_NODE_TYPES:
            add_error(f"{path}.type", f"unknown type '{node_type}'")
            return None
        return node_type

    def validate_expr(node: Any, path: str, defined: set[str]) -> None:
        node_type = expect_type(node, path)
        if node_type is None:
            return

        if node_type == "Literal":
            if "value" not in node:
                add_error(f"{path}.value", "missing value")
            return

        if node_type == "Var":
            name = node.get("name")
            if not isinstance(name, str) or not name:
                add_error(f"{path}.name", "missing or invalid name")
                return
            if name not in defined:
                add_error(path, f"variable '{name}' used before definition")
            return

        if node_type == "Binary":
            op = node.get("op")
            if op not in _ALLOWED_BINARY_OPS:
                add_error(f"{path}.op", "missing or invalid op")
            if "left" not in node:
                add_error(f"{path}.left", "missing left")
            else:
                validate_expr(node["left"], f"{path}.left", defined)
            if "right" not in node:
                add_error(f"{path}.right", "missing right")
            else:
                validate_expr(node["right"], f"{path}.right", defined)
            return

        if node_type == "Call":
            name = node.get("name")
            if not isinstance(name, str) or not name:
                add_error(f"{path}.name", "missing or invalid name")
            args = node.get("args")
            if not isinstance(args, list):
                add_error(f"{path}.args", "missing or invalid args")
                return
            for i, arg in enumerate(args):
                validate_expr(arg, f"{path}.args[{i}]", defined)
            return

        if node_type == "Print":
            args = node.get("args")
            if not isinstance(args, list):
                add_error(f"{path}.args", "missing or invalid args")
                return
            for i, arg in enumerate(args):
                validate_expr(arg, f"{path}.args[{i}]", defined)
            return

        if node_type == "Array":
            items = node.get("items")
            if not isinstance(items, list):
                add_error(f"{path}.items", "missing or invalid items")
                return
            for i, item in enumerate(items):
                validate_expr(item, f"{path}.items[{i}]", defined)
            return

        if node_type == "Index":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "index" not in node:
                add_error(f"{path}.index", "missing index")
            else:
                validate_expr(node["index"], f"{path}.index", defined)
                if isinstance(node["index"], dict) and node["index"].get("type") == "Literal":
                    value = node["index"].get("value")
                    if not isinstance(value, int) or value < 0:
                        add_error(f"{path}.index", "index must be a non-negative integer")
            return

        if node_type == "Length":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            return

        add_error(path, f"unexpected expression type '{node_type}'")

    def validate_stmt(
        node: Any, path: str, defined: set[str], in_func: bool
    ) -> None:
        node_type = expect_type(node, path)
        if node_type is None:
            return

        if node_type == "Let":
            name = node.get("name")
            if not isinstance(name, str) or not name:
                add_error(f"{path}.name", "missing or invalid name")
            if "value" not in node:
                add_error(f"{path}.value", "missing value")
            else:
                validate_expr(node["value"], f"{path}.value", defined)
            if isinstance(name, str) and name:
                defined.add(name)
            return

        if node_type == "Assign":
            name = node.get("name")
            if not isinstance(name, str) or not name:
                add_error(f"{path}.name", "missing or invalid name")
            if "value" not in node:
                add_error(f"{path}.value", "missing value")
            else:
                validate_expr(node["value"], f"{path}.value", defined)
            if isinstance(name, str) and name:
                defined.add(name)
            return

        if node_type == "If":
            if "test" not in node:
                add_error(f"{path}.test", "missing test")
            else:
                validate_expr(node["test"], f"{path}.test", defined)
            then_body = node.get("then")
            if not isinstance(then_body, list):
                add_error(f"{path}.then", "missing or invalid then")
            else:
                for i, stmt in enumerate(then_body):
                    validate_stmt(stmt, f"{path}.then[{i}]", defined, in_func)
            else_body = node.get("else")
            if else_body is not None:
                if not isinstance(else_body, list):
                    add_error(f"{path}.else", "invalid else")
                else:
                    for i, stmt in enumerate(else_body):
                        validate_stmt(stmt, f"{path}.else[{i}]", defined, in_func)
            return

        if node_type == "While":
            if "test" not in node:
                add_error(f"{path}.test", "missing test")
            else:
                validate_expr(node["test"], f"{path}.test", defined)
            body = node.get("body")
            if not isinstance(body, list):
                add_error(f"{path}.body", "missing or invalid body")
            else:
                for i, stmt in enumerate(body):
                    validate_stmt(stmt, f"{path}.body[{i}]", defined, in_func)
            return

        if node_type == "Call":
            validate_expr(node, path, defined)
            return

        if node_type == "Print":
            validate_expr(node, path, defined)
            return

        if node_type == "SetIndex":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "index" not in node:
                add_error(f"{path}.index", "missing index")
            else:
                validate_expr(node["index"], f"{path}.index", defined)
                if isinstance(node["index"], dict) and node["index"].get("type") == "Literal":
                    value = node["index"].get("value")
                    if not isinstance(value, int) or value < 0:
                        add_error(f"{path}.index", "index must be a non-negative integer")
            if "value" not in node:
                add_error(f"{path}.value", "missing value")
            else:
                validate_expr(node["value"], f"{path}.value", defined)
            return

        if node_type == "FuncDef":
            name = node.get("name")
            if not isinstance(name, str) or not name:
                add_error(f"{path}.name", "missing or invalid name")
            params = node.get("params")
            if not isinstance(params, list):
                add_error(f"{path}.params", "missing or invalid params")
            else:
                for i, param in enumerate(params):
                    if not isinstance(param, str) or not param:
                        add_error(f"{path}.params[{i}]", "param must be a non-empty string")
            body = node.get("body")
            if not isinstance(body, list):
                add_error(f"{path}.body", "missing or invalid body")
            else:
                for i, stmt in enumerate(body):
                    validate_stmt(stmt, f"{path}.body[{i}]", defined, True)
            return

        if node_type == "Return":
            if not in_func:
                add_error(path, "Return is only allowed inside FuncDef")
            if "value" in node:
                validate_expr(node["value"], f"{path}.value", defined)
            return

        add_error(path, f"unexpected statement type '{node_type}'")

    if not isinstance(doc, dict):
        add_error("$", "document must be an object")
        return errors

    version = doc.get("version")
    if version not in _ALLOWED_VERSIONS:
        add_error("$.version", "version must be 'coreil-0.1', 'coreil-0.2', or 'coreil-0.3'")

    ambiguities = doc.get("ambiguities")
    if ambiguities is not None:
        if not isinstance(ambiguities, list):
            add_error("$.ambiguities", "ambiguities must be a list")
        else:
            for i, item in enumerate(ambiguities):
                item_path = f"$.ambiguities[{i}]"
                if not isinstance(item, dict):
                    add_error(item_path, "ambiguity item must be an object")
                    continue
                question = item.get("question")
                options = item.get("options")
                default = item.get("default")
                if not isinstance(question, str) or not question:
                    add_error(f"{item_path}.question", "missing or invalid question")
                if not isinstance(options, list) or not options:
                    add_error(f"{item_path}.options", "missing or invalid options")
                else:
                    for j, opt in enumerate(options):
                        if not isinstance(opt, str) or not opt:
                            add_error(
                                f"{item_path}.options[{j}]",
                                "option must be a non-empty string",
                            )
                if not isinstance(default, int):
                    add_error(f"{item_path}.default", "missing or invalid default")
                elif isinstance(options, list) and options:
                    if default < 0 or default >= len(options):
                        add_error(
                            f"{item_path}.default",
                            "default must be a valid option index",
                        )

    body = doc.get("body")
    if not isinstance(body, list):
        add_error("$.body", "body must be a list")
        return errors

    defined: set[str] = set()
    for i, stmt in enumerate(body):
        validate_stmt(stmt, f"$.body[{i}]", defined, False)

    return errors

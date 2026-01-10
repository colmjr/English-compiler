"""Core IL validation.

This file implements Core IL v1.1 semantics validation.
Core IL v1.1 adds Record support for algorithm-friendly structured data.

Version history:
- v1.1: Added Record, GetField, SetField
- v1.0: Stable release (frozen)

Backward compatibility: Accepts v0.1 through v1.1 programs.
"""

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
    "For",
    "ForEach",
    "Set",
    "Push",
    "Literal",
    "Var",
    "Binary",
    "Array",
    "Index",
    "Length",
    "Range",
    "Map",
    "Get",
    "GetDefault",
    "Keys",
    "Tuple",
    "Record",
    "GetField",
    "SetField",
    "StringLength",
    "Substring",
    "CharAt",
    "Join",
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

# Core IL Version Support
# v1.1 is the current version (adds Record support)
# v1.0 is stable and frozen
# v0.1-v0.5 are accepted for backward compatibility
_ALLOWED_VERSIONS = {"coreil-0.1", "coreil-0.2", "coreil-0.3", "coreil-0.4", "coreil-0.5", "coreil-1.0", "coreil-1.1"}

# Helper functions that are disallowed in v0.5+ and v1.0+ (must use explicit primitives)
# This ensures Core IL remains a closed specification
_DISALLOWED_HELPER_CALLS = {"get_or_default", "keys", "append", "entries"}


def validate_coreil(doc: dict) -> list[dict]:
    errors: list[dict] = []

    # Track version for Call validation
    version = doc.get("version", "coreil-0.1")

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
            else:
                # In v0.5+ and v1.0+, disallow helper function calls
                if version in ("coreil-0.5", "coreil-1.0", "coreil-1.1") and name in _DISALLOWED_HELPER_CALLS:
                    add_error(
                        f"{path}.name",
                        f"helper function '{name}' is not allowed in v0.5; "
                        f"use explicit primitives (GetDefault, Keys, Push, Tuple)",
                    )
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

        if node_type == "Range":
            if "from" not in node:
                add_error(f"{path}.from", "missing from")
            else:
                validate_expr(node["from"], f"{path}.from", defined)
            if "to" not in node:
                add_error(f"{path}.to", "missing to")
            else:
                validate_expr(node["to"], f"{path}.to", defined)
            inclusive = node.get("inclusive")
            if inclusive is not None and not isinstance(inclusive, bool):
                add_error(f"{path}.inclusive", "inclusive must be a boolean")
            return

        if node_type == "Map":
            items = node.get("items")
            if not isinstance(items, list):
                add_error(f"{path}.items", "missing or invalid items")
                return
            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    add_error(f"{path}.items[{i}]", "item must be an object")
                    continue
                if "key" not in item:
                    add_error(f"{path}.items[{i}].key", "missing key")
                else:
                    validate_expr(item["key"], f"{path}.items[{i}].key", defined)
                if "value" not in item:
                    add_error(f"{path}.items[{i}].value", "missing value")
                else:
                    validate_expr(item["value"], f"{path}.items[{i}].value", defined)
            return

        if node_type == "Get":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "key" not in node:
                add_error(f"{path}.key", "missing key")
            else:
                validate_expr(node["key"], f"{path}.key", defined)
            return

        if node_type == "GetDefault":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "key" not in node:
                add_error(f"{path}.key", "missing key")
            else:
                validate_expr(node["key"], f"{path}.key", defined)
            if "default" not in node:
                add_error(f"{path}.default", "missing default")
            else:
                validate_expr(node["default"], f"{path}.default", defined)
            return

        if node_type == "Keys":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            return

        if node_type == "Tuple":
            items = node.get("items")
            if not isinstance(items, list):
                add_error(f"{path}.items", "missing or invalid items")
                return
            for i, item in enumerate(items):
                validate_expr(item, f"{path}.items[{i}]", defined)
            return

        if node_type == "Record":
            fields = node.get("fields")
            if not isinstance(fields, list):
                add_error(f"{path}.fields", "missing or invalid fields")
                return
            for i, field in enumerate(fields):
                if not isinstance(field, dict):
                    add_error(f"{path}.fields[{i}]", "field must be an object")
                    continue
                name = field.get("name")
                if not isinstance(name, str) or not name:
                    add_error(f"{path}.fields[{i}].name", "missing or invalid field name")
                if "value" not in field:
                    add_error(f"{path}.fields[{i}].value", "missing value")
                else:
                    validate_expr(field["value"], f"{path}.fields[{i}].value", defined)
            return

        if node_type == "GetField":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            name = node.get("name")
            if not isinstance(name, str) or not name:
                add_error(f"{path}.name", "missing or invalid field name")
            return

        if node_type == "StringLength":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            return

        if node_type == "Substring":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "start" not in node:
                add_error(f"{path}.start", "missing start")
            else:
                validate_expr(node["start"], f"{path}.start", defined)
            if "end" not in node:
                add_error(f"{path}.end", "missing end")
            else:
                validate_expr(node["end"], f"{path}.end", defined)
            return

        if node_type == "CharAt":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "index" not in node:
                add_error(f"{path}.index", "missing index")
            else:
                validate_expr(node["index"], f"{path}.index", defined)
            return

        if node_type == "Join":
            if "sep" not in node:
                add_error(f"{path}.sep", "missing sep")
            else:
                validate_expr(node["sep"], f"{path}.sep", defined)
            if "items" not in node:
                add_error(f"{path}.items", "missing items")
            else:
                validate_expr(node["items"], f"{path}.items", defined)
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

        if node_type == "Set":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "key" not in node:
                add_error(f"{path}.key", "missing key")
            else:
                validate_expr(node["key"], f"{path}.key", defined)
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
                original_defined = defined.copy()
                for i, param in enumerate(params):
                    if not isinstance(param, str) or not param:
                        add_error(f"{path}.params[{i}]", "param must be a non-empty string")
                    elif param:
                        defined.add(param)
            body = node.get("body")
            if not isinstance(body, list):
                add_error(f"{path}.body", "missing or invalid body")
            else:
                for i, stmt in enumerate(body):
                    validate_stmt(stmt, f"{path}.body[{i}]", defined, True)
            defined.clear()
            defined.update(original_defined)
            return

        if node_type == "Return":
            if not in_func:
                add_error(path, "Return is only allowed inside FuncDef")
            if "value" in node:
                validate_expr(node["value"], f"{path}.value", defined)
            return

        if node_type == "For":
            var_name = node.get("var")
            if not isinstance(var_name, str) or not var_name:
                add_error(f"{path}.var", "missing or invalid var")
            iter_expr = node.get("iter")
            if iter_expr is None:
                add_error(f"{path}.iter", "missing iter")
            else:
                validate_expr(iter_expr, f"{path}.iter", defined)
            # Add loop variable to defined set for body validation
            if isinstance(var_name, str) and var_name:
                defined.add(var_name)
            body = node.get("body")
            if not isinstance(body, list):
                add_error(f"{path}.body", "missing or invalid body")
            else:
                for i, stmt in enumerate(body):
                    validate_stmt(stmt, f"{path}.body[{i}]", defined, in_func)
            return

        if node_type == "ForEach":
            var_name = node.get("var")
            if not isinstance(var_name, str) or not var_name:
                add_error(f"{path}.var", "missing or invalid var")
            iter_expr = node.get("iter")
            if iter_expr is None:
                add_error(f"{path}.iter", "missing iter")
            else:
                validate_expr(iter_expr, f"{path}.iter", defined)
            # Add loop variable to defined set for body validation
            if isinstance(var_name, str) and var_name:
                defined.add(var_name)
            body = node.get("body")
            if not isinstance(body, list):
                add_error(f"{path}.body", "missing or invalid body")
            else:
                for i, stmt in enumerate(body):
                    validate_stmt(stmt, f"{path}.body[{i}]", defined, in_func)
            return

        if node_type == "Push":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "value" not in node:
                add_error(f"{path}.value", "missing value")
            else:
                validate_expr(node["value"], f"{path}.value", defined)
            return

        if node_type == "SetField":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            name = node.get("name")
            if not isinstance(name, str) or not name:
                add_error(f"{path}.name", "missing or invalid field name")
            if "value" not in node:
                add_error(f"{path}.value", "missing value")
            else:
                validate_expr(node["value"], f"{path}.value", defined)
            return

        add_error(path, f"unexpected statement type '{node_type}'")

    if not isinstance(doc, dict):
        add_error("$", "document must be an object")
        return errors

    version = doc.get("version")
    if version not in _ALLOWED_VERSIONS:
        add_error("$.version", "version must be 'coreil-0.1', 'coreil-0.2', 'coreil-0.3', 'coreil-0.4', 'coreil-0.5', 'coreil-1.0', or 'coreil-1.1'")

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

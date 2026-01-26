"""Core IL validation.

This file implements Core IL v1.5 semantics validation.
Core IL v1.5 adds array/list slicing and unary not operations.

Version history:
- v1.5: Added Slice for array/list slicing, Not for logical negation
- v1.4: Consolidated Math, JSON, and Regex operations
- v1.3: Added JsonParse, JsonStringify, RegexMatch, RegexFindAll, RegexReplace, RegexSplit
- v1.2: Added Math, MathPow, MathConst for portable math operations
- v1.1: Added Record, GetField, SetField, Set, Deque operations, String operations, Heap operations
- v1.0: Stable release (frozen)

Backward compatibility: Accepts v0.1 through v1.5 programs.
"""

from __future__ import annotations

from typing import Any

from .versions import SUPPORTED_VERSIONS, get_version_error_message, is_sealed_version


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
    "SetHas",
    "SetSize",
    "SetAdd",
    "SetRemove",
    "DequeNew",
    "DequeSize",
    "PushBack",
    "PushFront",
    "PopFront",
    "PopBack",
    "HeapNew",
    "HeapSize",
    "HeapPeek",
    "HeapPush",
    "HeapPop",
    # Math operations (v1.2)
    "Math",
    "MathPow",
    "MathConst",
    # JSON operations (v1.3)
    "JsonParse",
    "JsonStringify",
    # Regex operations (v1.3)
    "RegexMatch",
    "RegexFindAll",
    "RegexReplace",
    "RegexSplit",
    # String operations (v1.4)
    "StringSplit",
    "StringTrim",
    "StringUpper",
    "StringLower",
    "StringStartsWith",
    "StringEndsWith",
    "StringContains",
    "StringReplace",
    # External call (Tier 2, non-portable)
    "ExternalCall",
    # Array slicing (v1.5)
    "Slice",
    # Unary not (v1.5)
    "Not",
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

# Note: Version support is defined in versions.py (single source of truth)

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
                # In sealed versions (v0.5+), disallow helper function calls
                if is_sealed_version(version) and name in _DISALLOWED_HELPER_CALLS:
                    add_error(
                        f"{path}.name",
                        f"helper function '{name}' is not allowed in sealed versions (v0.5+); "
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

        # String operations (v1.4)
        if node_type == "StringSplit":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "delimiter" not in node:
                add_error(f"{path}.delimiter", "missing delimiter")
            else:
                validate_expr(node["delimiter"], f"{path}.delimiter", defined)
            return

        if node_type == "StringTrim":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            return

        if node_type == "StringUpper":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            return

        if node_type == "StringLower":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            return

        if node_type == "StringStartsWith":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "prefix" not in node:
                add_error(f"{path}.prefix", "missing prefix")
            else:
                validate_expr(node["prefix"], f"{path}.prefix", defined)
            return

        if node_type == "StringEndsWith":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "suffix" not in node:
                add_error(f"{path}.suffix", "missing suffix")
            else:
                validate_expr(node["suffix"], f"{path}.suffix", defined)
            return

        if node_type == "StringContains":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "substring" not in node:
                add_error(f"{path}.substring", "missing substring")
            else:
                validate_expr(node["substring"], f"{path}.substring", defined)
            return

        if node_type == "StringReplace":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "old" not in node:
                add_error(f"{path}.old", "missing old")
            else:
                validate_expr(node["old"], f"{path}.old", defined)
            if "new" not in node:
                add_error(f"{path}.new", "missing new")
            else:
                validate_expr(node["new"], f"{path}.new", defined)
            return

        if node_type == "Set":
            if "items" not in node:
                add_error(f"{path}.items", "missing items")
            else:
                items = node.get("items")
                if not isinstance(items, list):
                    add_error(f"{path}.items", "items must be an array")
                else:
                    for i, item in enumerate(items):
                        validate_expr(item, f"{path}.items[{i}]", defined)
            return

        if node_type == "SetHas":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "value" not in node:
                add_error(f"{path}.value", "missing value")
            else:
                validate_expr(node["value"], f"{path}.value", defined)
            return

        if node_type == "SetSize":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            return

        if node_type == "DequeNew":
            # DequeNew takes no arguments
            return

        if node_type == "DequeSize":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            return

        if node_type == "HeapNew":
            # HeapNew takes no arguments
            return

        if node_type == "HeapSize":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            return

        if node_type == "HeapPeek":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            return

        # Math operations (v1.2)
        if node_type == "Math":
            valid_ops = {"sin", "cos", "tan", "sqrt", "floor", "ceil", "abs", "log", "exp"}
            op = node.get("op")
            if op not in valid_ops:
                add_error(f"{path}.op", f"invalid math op '{op}', must be one of {valid_ops}")
            if "arg" not in node:
                add_error(f"{path}.arg", "missing arg")
            else:
                validate_expr(node["arg"], f"{path}.arg", defined)
            return

        if node_type == "MathPow":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "exponent" not in node:
                add_error(f"{path}.exponent", "missing exponent")
            else:
                validate_expr(node["exponent"], f"{path}.exponent", defined)
            return

        if node_type == "MathConst":
            name = node.get("name")
            if name not in {"pi", "e"}:
                add_error(f"{path}.name", f"invalid math constant '{name}', must be 'pi' or 'e'")
            return

        # JSON operations (v1.3)
        if node_type == "JsonParse":
            if "source" not in node:
                add_error(f"{path}.source", "missing source")
            else:
                validate_expr(node["source"], f"{path}.source", defined)
            return

        if node_type == "JsonStringify":
            if "value" not in node:
                add_error(f"{path}.value", "missing value")
            else:
                validate_expr(node["value"], f"{path}.value", defined)
            if "pretty" in node:
                validate_expr(node["pretty"], f"{path}.pretty", defined)
            return

        # Regex operations (v1.3)
        if node_type == "RegexMatch":
            if "string" not in node:
                add_error(f"{path}.string", "missing string")
            else:
                validate_expr(node["string"], f"{path}.string", defined)
            if "pattern" not in node:
                add_error(f"{path}.pattern", "missing pattern")
            else:
                validate_expr(node["pattern"], f"{path}.pattern", defined)
            if "flags" in node:
                validate_expr(node["flags"], f"{path}.flags", defined)
            return

        if node_type == "RegexFindAll":
            if "string" not in node:
                add_error(f"{path}.string", "missing string")
            else:
                validate_expr(node["string"], f"{path}.string", defined)
            if "pattern" not in node:
                add_error(f"{path}.pattern", "missing pattern")
            else:
                validate_expr(node["pattern"], f"{path}.pattern", defined)
            if "flags" in node:
                validate_expr(node["flags"], f"{path}.flags", defined)
            return

        if node_type == "RegexReplace":
            if "string" not in node:
                add_error(f"{path}.string", "missing string")
            else:
                validate_expr(node["string"], f"{path}.string", defined)
            if "pattern" not in node:
                add_error(f"{path}.pattern", "missing pattern")
            else:
                validate_expr(node["pattern"], f"{path}.pattern", defined)
            if "replacement" not in node:
                add_error(f"{path}.replacement", "missing replacement")
            else:
                validate_expr(node["replacement"], f"{path}.replacement", defined)
            if "flags" in node:
                validate_expr(node["flags"], f"{path}.flags", defined)
            return

        if node_type == "RegexSplit":
            if "string" not in node:
                add_error(f"{path}.string", "missing string")
            else:
                validate_expr(node["string"], f"{path}.string", defined)
            if "pattern" not in node:
                add_error(f"{path}.pattern", "missing pattern")
            else:
                validate_expr(node["pattern"], f"{path}.pattern", defined)
            if "flags" in node:
                validate_expr(node["flags"], f"{path}.flags", defined)
            if "maxsplit" in node:
                validate_expr(node["maxsplit"], f"{path}.maxsplit", defined)
            return

        # External call (Tier 2, non-portable)
        if node_type == "ExternalCall":
            module = node.get("module")
            if not isinstance(module, str) or not module:
                add_error(f"{path}.module", "missing or invalid module name")
            function = node.get("function")
            if not isinstance(function, str) or not function:
                add_error(f"{path}.function", "missing or invalid function name")
            args = node.get("args")
            if not isinstance(args, list):
                add_error(f"{path}.args", "missing or invalid args")
            else:
                for i, arg in enumerate(args):
                    validate_expr(arg, f"{path}.args[{i}]", defined)
            return

        # Array slicing (v1.5)
        if node_type == "Slice":
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

        # Unary not (v1.5)
        if node_type == "Not":
            if "arg" not in node:
                add_error(f"{path}.arg", "missing arg")
            else:
                validate_expr(node["arg"], f"{path}.arg", defined)
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

        if node_type == "SetAdd":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "value" not in node:
                add_error(f"{path}.value", "missing value")
            else:
                validate_expr(node["value"], f"{path}.value", defined)
            return

        if node_type == "SetRemove":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "value" not in node:
                add_error(f"{path}.value", "missing value")
            else:
                validate_expr(node["value"], f"{path}.value", defined)
            return

        if node_type == "PushBack":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "value" not in node:
                add_error(f"{path}.value", "missing value")
            else:
                validate_expr(node["value"], f"{path}.value", defined)
            return

        if node_type == "PushFront":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "value" not in node:
                add_error(f"{path}.value", "missing value")
            else:
                validate_expr(node["value"], f"{path}.value", defined)
            return

        if node_type == "PopFront":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            target = node.get("target")
            if not isinstance(target, str) or not target:
                add_error(f"{path}.target", "missing or invalid target variable name")
            else:
                defined.add(target)
            return

        if node_type == "PopBack":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            target = node.get("target")
            if not isinstance(target, str) or not target:
                add_error(f"{path}.target", "missing or invalid target variable name")
            else:
                defined.add(target)
            return

        if node_type == "HeapPush":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            if "priority" not in node:
                add_error(f"{path}.priority", "missing priority")
            else:
                validate_expr(node["priority"], f"{path}.priority", defined)
            if "value" not in node:
                add_error(f"{path}.value", "missing value")
            else:
                validate_expr(node["value"], f"{path}.value", defined)
            return

        if node_type == "HeapPop":
            if "base" not in node:
                add_error(f"{path}.base", "missing base")
            else:
                validate_expr(node["base"], f"{path}.base", defined)
            target = node.get("target")
            if not isinstance(target, str) or not target:
                add_error(f"{path}.target", "missing or invalid target variable name")
            else:
                defined.add(target)
            return

        add_error(path, f"unexpected statement type '{node_type}'")

    if not isinstance(doc, dict):
        add_error("$", "document must be an object")
        return errors

    version = doc.get("version")
    if version not in SUPPORTED_VERSIONS:
        add_error("$.version", get_version_error_message())

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

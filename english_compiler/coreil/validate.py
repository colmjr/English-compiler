"""Core IL validation.

This file implements Core IL v1.8 semantics validation.
Core IL v1.8 adds TryCatch and Throw for exception handling.

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

from typing import Any, Callable

from .constants import BINARY_OPS, DISALLOWED_HELPER_CALLS, MATH_CONSTANTS, MATH_OPS
from .versions import SUPPORTED_VERSIONS, get_version_error_message, is_sealed_version


_ALLOWED_NODE_TYPES = {
    "Let", "Assign", "If", "While", "Call", "Print", "SetIndex", "FuncDef", "Return",
    "For", "ForEach", "Set", "Push", "Literal", "Var", "Binary", "Array", "Index",
    "Length", "Range", "Map", "Get", "GetDefault", "Keys", "Tuple", "Record", "GetField",
    "SetField", "StringLength", "Substring", "CharAt", "Join", "SetHas", "SetSize",
    "SetAdd", "SetRemove", "DequeNew", "DequeSize", "PushBack", "PushFront", "PopFront",
    "PopBack", "HeapNew", "HeapSize", "HeapPeek", "HeapPush", "HeapPop", "Math", "MathPow",
    "MathConst", "JsonParse", "JsonStringify", "RegexMatch", "RegexFindAll", "RegexReplace",
    "RegexSplit", "StringSplit", "StringTrim", "StringUpper", "StringLower",
    "StringStartsWith", "StringEndsWith", "StringContains", "StringReplace", "ExternalCall",
    "Slice", "Not", "MethodCall", "PropertyGet", "Break", "Continue",
    "Throw", "TryCatch",
    "ToInt", "ToFloat", "ToString",
    "Switch",
}


# Type alias for validator functions
ValidatorFunc = Callable[
    [dict, str, set[str], Callable[[str, str], None], "Callable[[Any, str, set[str]], None]"],
    None
]


def _require_expr(
    node: dict, key: str, path: str, defined: set[str],
    add_error: Callable[[str, str], None], validate_expr: Callable[[Any, str, set[str]], None]
) -> None:
    """Require an expression field and validate it."""
    if key not in node:
        add_error(f"{path}.{key}", f"missing {key}")
    else:
        validate_expr(node[key], f"{path}.{key}", defined)


def _require_string(
    node: dict, key: str, path: str, add_error: Callable[[str, str], None], label: str | None = None
) -> str | None:
    """Require a non-empty string field."""
    label = label or key
    value = node.get(key)
    if not isinstance(value, str) or not value:
        add_error(f"{path}.{key}", f"missing or invalid {label}")
        return None
    return value


def _validate_args_list(
    node: dict, path: str, defined: set[str],
    add_error: Callable[[str, str], None], validate_expr: Callable[[Any, str, set[str]], None]
) -> None:
    """Validate an args field that must be a list of expressions."""
    args = node.get("args")
    if not isinstance(args, list):
        add_error(f"{path}.args", "missing or invalid args")
    else:
        for i, arg in enumerate(args):
            validate_expr(arg, f"{path}.args[{i}]", defined)


def _validate_items_list(
    node: dict, path: str, defined: set[str],
    add_error: Callable[[str, str], None], validate_expr: Callable[[Any, str, set[str]], None]
) -> None:
    """Validate an items field that must be a list of expressions."""
    items = node.get("items")
    if not isinstance(items, list):
        add_error(f"{path}.items", "missing or invalid items")
    else:
        for i, item in enumerate(items):
            validate_expr(item, f"{path}.items[{i}]", defined)


# -- Expression Validators --

def _validate_literal(node, path, defined, add_error, validate_expr):
    if "value" not in node:
        add_error(f"{path}.value", "missing value")


def _validate_var(node, path, defined, add_error, validate_expr):
    name = node.get("name")
    if not isinstance(name, str) or not name:
        add_error(f"{path}.name", "missing or invalid name")
        return
    if name not in defined:
        add_error(path, f"variable '{name}' used before definition")


def _validate_binary(node, path, defined, add_error, validate_expr):
    op = node.get("op")
    if op not in BINARY_OPS:
        add_error(f"{path}.op", "missing or invalid op")
    _require_expr(node, "left", path, defined, add_error, validate_expr)
    _require_expr(node, "right", path, defined, add_error, validate_expr)


def _validate_call_expr(node, path, defined, add_error, validate_expr, version):
    name = node.get("name")
    if not isinstance(name, str) or not name:
        add_error(f"{path}.name", "missing or invalid name")
    elif is_sealed_version(version) and name in DISALLOWED_HELPER_CALLS:
        add_error(
            f"{path}.name",
            f"helper function '{name}' is not allowed in sealed versions (v0.5+); "
            f"use explicit primitives (GetDefault, Keys, Push, Tuple)",
        )
    _validate_args_list(node, path, defined, add_error, validate_expr)


def _validate_print_expr(node, path, defined, add_error, validate_expr):
    _validate_args_list(node, path, defined, add_error, validate_expr)


def _validate_array(node, path, defined, add_error, validate_expr):
    _validate_items_list(node, path, defined, add_error, validate_expr)


def _validate_index(node, path, defined, add_error, validate_expr):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    if "index" not in node:
        add_error(f"{path}.index", "missing index")
    else:
        validate_expr(node["index"], f"{path}.index", defined)
        # Validate literal indices are integers (negative values allowed for Python-style indexing)
        if isinstance(node["index"], dict) and node["index"].get("type") == "Literal":
            value = node["index"].get("value")
            if not isinstance(value, int):
                add_error(f"{path}.index", "index must be an integer")


def _validate_base_only(node, path, defined, add_error, validate_expr):
    """Validator for expressions that only need 'base' validated."""
    _require_expr(node, "base", path, defined, add_error, validate_expr)


def _validate_range(node, path, defined, add_error, validate_expr):
    _require_expr(node, "from", path, defined, add_error, validate_expr)
    _require_expr(node, "to", path, defined, add_error, validate_expr)
    inclusive = node.get("inclusive")
    if inclusive is not None and not isinstance(inclusive, bool):
        add_error(f"{path}.inclusive", "inclusive must be a boolean")


def _validate_map(node, path, defined, add_error, validate_expr):
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


def _validate_get(node, path, defined, add_error, validate_expr):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "key", path, defined, add_error, validate_expr)


def _validate_get_default(node, path, defined, add_error, validate_expr):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "key", path, defined, add_error, validate_expr)
    _require_expr(node, "default", path, defined, add_error, validate_expr)


def _validate_tuple(node, path, defined, add_error, validate_expr):
    _validate_items_list(node, path, defined, add_error, validate_expr)


def _validate_record(node, path, defined, add_error, validate_expr):
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


def _validate_get_field(node, path, defined, add_error, validate_expr):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_string(node, "name", path, add_error, "field name")


def _validate_substring(node, path, defined, add_error, validate_expr):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "start", path, defined, add_error, validate_expr)
    _require_expr(node, "end", path, defined, add_error, validate_expr)


def _validate_char_at(node, path, defined, add_error, validate_expr):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "index", path, defined, add_error, validate_expr)


def _validate_join(node, path, defined, add_error, validate_expr):
    _require_expr(node, "sep", path, defined, add_error, validate_expr)
    _require_expr(node, "items", path, defined, add_error, validate_expr)


def _validate_string_split(node, path, defined, add_error, validate_expr):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "delimiter", path, defined, add_error, validate_expr)


def _validate_string_prefix(node, path, defined, add_error, validate_expr):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "prefix", path, defined, add_error, validate_expr)


def _validate_string_suffix(node, path, defined, add_error, validate_expr):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "suffix", path, defined, add_error, validate_expr)


def _validate_string_contains(node, path, defined, add_error, validate_expr):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "substring", path, defined, add_error, validate_expr)


def _validate_string_replace(node, path, defined, add_error, validate_expr):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "old", path, defined, add_error, validate_expr)
    _require_expr(node, "new", path, defined, add_error, validate_expr)


def _validate_set_expr(node, path, defined, add_error, validate_expr):
    if "items" not in node:
        add_error(f"{path}.items", "missing items")
    else:
        items = node.get("items")
        if not isinstance(items, list):
            add_error(f"{path}.items", "items must be an array")
        else:
            for i, item in enumerate(items):
                validate_expr(item, f"{path}.items[{i}]", defined)


def _validate_set_has(node, path, defined, add_error, validate_expr):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "value", path, defined, add_error, validate_expr)


def _validate_no_args(node, path, defined, add_error, validate_expr):
    """Validator for expressions with no required arguments (DequeNew, HeapNew)."""
    pass


def _validate_math(node, path, defined, add_error, validate_expr):
    op = node.get("op")
    if op not in MATH_OPS:
        add_error(f"{path}.op", f"invalid math op '{op}', must be one of {set(MATH_OPS)}")
    _require_expr(node, "arg", path, defined, add_error, validate_expr)


def _validate_math_pow(node, path, defined, add_error, validate_expr):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "exponent", path, defined, add_error, validate_expr)


def _validate_math_const(node, path, defined, add_error, validate_expr):
    name = node.get("name")
    if name not in MATH_CONSTANTS:
        add_error(f"{path}.name", f"invalid math constant '{name}', must be one of {set(MATH_CONSTANTS)}")


def _validate_json_parse(node, path, defined, add_error, validate_expr):
    _require_expr(node, "source", path, defined, add_error, validate_expr)


def _validate_json_stringify(node, path, defined, add_error, validate_expr):
    _require_expr(node, "value", path, defined, add_error, validate_expr)
    if "pretty" in node:
        validate_expr(node["pretty"], f"{path}.pretty", defined)


def _validate_regex_base(node, path, defined, add_error, validate_expr):
    """Base validator for regex operations with string, pattern, and optional flags."""
    _require_expr(node, "string", path, defined, add_error, validate_expr)
    _require_expr(node, "pattern", path, defined, add_error, validate_expr)
    if "flags" in node:
        validate_expr(node["flags"], f"{path}.flags", defined)


def _validate_regex_replace(node, path, defined, add_error, validate_expr):
    _validate_regex_base(node, path, defined, add_error, validate_expr)
    _require_expr(node, "replacement", path, defined, add_error, validate_expr)


def _validate_regex_split(node, path, defined, add_error, validate_expr):
    _validate_regex_base(node, path, defined, add_error, validate_expr)
    if "maxsplit" in node:
        validate_expr(node["maxsplit"], f"{path}.maxsplit", defined)


def _validate_external_call(node, path, defined, add_error, validate_expr):
    _require_string(node, "module", path, add_error, "module name")
    _require_string(node, "function", path, add_error, "function name")
    _validate_args_list(node, path, defined, add_error, validate_expr)


def _validate_method_call(node, path, defined, add_error, validate_expr):
    _require_expr(node, "object", path, defined, add_error, validate_expr)
    _require_string(node, "method", path, add_error, "method name")
    _validate_args_list(node, path, defined, add_error, validate_expr)


def _validate_property_get(node, path, defined, add_error, validate_expr):
    _require_expr(node, "object", path, defined, add_error, validate_expr)
    _require_string(node, "property", path, add_error, "property name")


def _validate_slice(node, path, defined, add_error, validate_expr):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "start", path, defined, add_error, validate_expr)
    _require_expr(node, "end", path, defined, add_error, validate_expr)


def _validate_not(node, path, defined, add_error, validate_expr):
    _require_expr(node, "arg", path, defined, add_error, validate_expr)


def _validate_value_only(node, path, defined, add_error, validate_expr):
    """Validator for expressions that only need 'value' validated (ToInt, ToFloat, ToString)."""
    _require_expr(node, "value", path, defined, add_error, validate_expr)


# Expression validator dispatch table
_EXPR_VALIDATORS: dict[str, ValidatorFunc] = {
    "Literal": _validate_literal,
    "Var": _validate_var,
    "Binary": _validate_binary,
    "Print": _validate_print_expr,
    "Array": _validate_array,
    "Index": _validate_index,
    "Length": _validate_base_only,
    "Range": _validate_range,
    "Map": _validate_map,
    "Get": _validate_get,
    "GetDefault": _validate_get_default,
    "Keys": _validate_base_only,
    "Tuple": _validate_tuple,
    "Record": _validate_record,
    "GetField": _validate_get_field,
    "StringLength": _validate_base_only,
    "Substring": _validate_substring,
    "CharAt": _validate_char_at,
    "Join": _validate_join,
    "StringSplit": _validate_string_split,
    "StringTrim": _validate_base_only,
    "StringUpper": _validate_base_only,
    "StringLower": _validate_base_only,
    "StringStartsWith": _validate_string_prefix,
    "StringEndsWith": _validate_string_suffix,
    "StringContains": _validate_string_contains,
    "StringReplace": _validate_string_replace,
    "Set": _validate_set_expr,
    "SetHas": _validate_set_has,
    "SetSize": _validate_base_only,
    "DequeNew": _validate_no_args,
    "DequeSize": _validate_base_only,
    "HeapNew": _validate_no_args,
    "HeapSize": _validate_base_only,
    "HeapPeek": _validate_base_only,
    "Math": _validate_math,
    "MathPow": _validate_math_pow,
    "MathConst": _validate_math_const,
    "JsonParse": _validate_json_parse,
    "JsonStringify": _validate_json_stringify,
    "RegexMatch": _validate_regex_base,
    "RegexFindAll": _validate_regex_base,
    "RegexReplace": _validate_regex_replace,
    "RegexSplit": _validate_regex_split,
    "ExternalCall": _validate_external_call,
    "MethodCall": _validate_method_call,
    "PropertyGet": _validate_property_get,
    "Slice": _validate_slice,
    "Not": _validate_not,
    "ToInt": _validate_value_only,
    "ToFloat": _validate_value_only,
    "ToString": _validate_value_only,
}


# -- Statement Validators --

def _validate_let(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    name = node.get("name")
    if not isinstance(name, str) or not name:
        add_error(f"{path}.name", "missing or invalid name")
    _require_expr(node, "value", path, defined, add_error, validate_expr)
    if isinstance(name, str) and name:
        defined.add(name)


def _validate_assign(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    name = node.get("name")
    if not isinstance(name, str) or not name:
        add_error(f"{path}.name", "missing or invalid name")
    _require_expr(node, "value", path, defined, add_error, validate_expr)
    if isinstance(name, str) and name:
        defined.add(name)


def _validate_if(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "test", path, defined, add_error, validate_expr)
    then_body = node.get("then")
    if not isinstance(then_body, list):
        add_error(f"{path}.then", "missing or invalid then")
    else:
        for i, stmt in enumerate(then_body):
            validate_stmt(stmt, f"{path}.then[{i}]", defined, in_func, in_loop)
    else_body = node.get("else")
    if else_body is not None:
        if not isinstance(else_body, list):
            add_error(f"{path}.else", "invalid else")
        else:
            for i, stmt in enumerate(else_body):
                validate_stmt(stmt, f"{path}.else[{i}]", defined, in_func, in_loop)


def _validate_while(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "test", path, defined, add_error, validate_expr)
    body = node.get("body")
    if not isinstance(body, list):
        add_error(f"{path}.body", "missing or invalid body")
    else:
        for i, stmt in enumerate(body):
            # Loop body is in_loop=True
            validate_stmt(stmt, f"{path}.body[{i}]", defined, in_func, True)


def _validate_call_stmt(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt, version):
    _validate_call_expr(node, path, defined, add_error, validate_expr, version)


def _validate_print_stmt(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _validate_print_expr(node, path, defined, add_error, validate_expr)


def _validate_set_index(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    if "index" not in node:
        add_error(f"{path}.index", "missing index")
    else:
        validate_expr(node["index"], f"{path}.index", defined)
        # Validate literal indices are integers (negative values allowed for Python-style indexing)
        if isinstance(node["index"], dict) and node["index"].get("type") == "Literal":
            value = node["index"].get("value")
            if not isinstance(value, int):
                add_error(f"{path}.index", "index must be an integer")
    _require_expr(node, "value", path, defined, add_error, validate_expr)


def _validate_set_stmt(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "key", path, defined, add_error, validate_expr)
    _require_expr(node, "value", path, defined, add_error, validate_expr)


def _validate_func_def(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
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
            # Reset in_loop to False when entering function body
            validate_stmt(stmt, f"{path}.body[{i}]", defined, True, False)
    defined.clear()
    defined.update(original_defined)


def _validate_return(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    if not in_func:
        add_error(path, "Return is only allowed inside FuncDef")
    if "value" in node:
        validate_expr(node["value"], f"{path}.value", defined)


def _validate_for(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
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
            # Loop body is in_loop=True
            validate_stmt(stmt, f"{path}.body[{i}]", defined, in_func, True)


def _validate_for_each(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
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
            # Loop body is in_loop=True
            validate_stmt(stmt, f"{path}.body[{i}]", defined, in_func, True)


def _validate_push(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "value", path, defined, add_error, validate_expr)


def _validate_set_field(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_string(node, "name", path, add_error, "field name")
    _require_expr(node, "value", path, defined, add_error, validate_expr)


def _validate_set_add(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "value", path, defined, add_error, validate_expr)


def _validate_set_remove(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "value", path, defined, add_error, validate_expr)


def _validate_push_back(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "value", path, defined, add_error, validate_expr)


def _validate_push_front(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "value", path, defined, add_error, validate_expr)


def _validate_pop_front(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    target = node.get("target")
    if not isinstance(target, str) or not target:
        add_error(f"{path}.target", "missing or invalid target variable name")
    else:
        defined.add(target)


def _validate_pop_back(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    target = node.get("target")
    if not isinstance(target, str) or not target:
        add_error(f"{path}.target", "missing or invalid target variable name")
    else:
        defined.add(target)


def _validate_heap_push(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    _require_expr(node, "priority", path, defined, add_error, validate_expr)
    _require_expr(node, "value", path, defined, add_error, validate_expr)


def _validate_heap_pop(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "base", path, defined, add_error, validate_expr)
    target = node.get("target")
    if not isinstance(target, str) or not target:
        add_error(f"{path}.target", "missing or invalid target variable name")
    else:
        defined.add(target)


def _validate_break(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    if not in_loop:
        add_error(path, "Break is only allowed inside a loop (While, For, ForEach)")


def _validate_continue(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    if not in_loop:
        add_error(path, "Continue is only allowed inside a loop (While, For, ForEach)")


def _validate_throw(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "message", path, defined, add_error, validate_expr)


def _validate_switch(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    _require_expr(node, "test", path, defined, add_error, validate_expr)
    cases = node.get("cases")
    if not isinstance(cases, list) or len(cases) == 0:
        add_error(f"{path}.cases", "missing or invalid cases (must be non-empty list)")
    else:
        for i, case in enumerate(cases):
            case_path = f"{path}.cases[{i}]"
            if not isinstance(case, dict):
                add_error(case_path, "case must be an object")
                continue
            if "value" not in case:
                add_error(f"{case_path}.value", "missing case value")
            else:
                validate_expr(case["value"], f"{case_path}.value", defined)
            case_body = case.get("body")
            if not isinstance(case_body, list):
                add_error(f"{case_path}.body", "missing or invalid case body")
            else:
                for j, stmt in enumerate(case_body):
                    validate_stmt(stmt, f"{case_path}.body[{j}]", defined, in_func, in_loop)
    default = node.get("default")
    if default is not None:
        if not isinstance(default, list):
            add_error(f"{path}.default", "invalid default")
        else:
            for i, stmt in enumerate(default):
                validate_stmt(stmt, f"{path}.default[{i}]", defined, in_func, in_loop)


def _validate_try_catch(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt):
    body = node.get("body")
    if not isinstance(body, list):
        add_error(f"{path}.body", "missing or invalid body")
    else:
        for i, stmt in enumerate(body):
            validate_stmt(stmt, f"{path}.body[{i}]", defined, in_func, in_loop)

    catch_var = node.get("catch_var")
    if not isinstance(catch_var, str) or not catch_var:
        add_error(f"{path}.catch_var", "missing or invalid catch_var")

    catch_body = node.get("catch_body")
    if not isinstance(catch_body, list):
        add_error(f"{path}.catch_body", "missing or invalid catch_body")
    else:
        # Add catch_var to defined set for catch_body scope
        catch_defined = defined.copy()
        if isinstance(catch_var, str) and catch_var:
            catch_defined.add(catch_var)
        for i, stmt in enumerate(catch_body):
            validate_stmt(stmt, f"{path}.catch_body[{i}]", catch_defined, in_func, in_loop)
        # Propagate any new definitions back
        defined.update(catch_defined)

    finally_body = node.get("finally_body")
    if finally_body is not None:
        if not isinstance(finally_body, list):
            add_error(f"{path}.finally_body", "invalid finally_body")
        else:
            for i, stmt in enumerate(finally_body):
                validate_stmt(stmt, f"{path}.finally_body[{i}]", defined, in_func, in_loop)


# Statement validator dispatch table (version-independent statements)
_STMT_VALIDATORS = {
    "Let": _validate_let,
    "Assign": _validate_assign,
    "If": _validate_if,
    "While": _validate_while,
    "Print": _validate_print_stmt,
    "SetIndex": _validate_set_index,
    "Set": _validate_set_stmt,
    "FuncDef": _validate_func_def,
    "Return": _validate_return,
    "For": _validate_for,
    "ForEach": _validate_for_each,
    "Push": _validate_push,
    "SetField": _validate_set_field,
    "SetAdd": _validate_set_add,
    "SetRemove": _validate_set_remove,
    "PushBack": _validate_push_back,
    "PushFront": _validate_push_front,
    "PopFront": _validate_pop_front,
    "PopBack": _validate_pop_back,
    "HeapPush": _validate_heap_push,
    "HeapPop": _validate_heap_pop,
    "Break": _validate_break,
    "Continue": _validate_continue,
    "Throw": _validate_throw,
    "TryCatch": _validate_try_catch,
    "Switch": _validate_switch,
}


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

        # Special case: Call needs version for validation
        if node_type == "Call":
            _validate_call_expr(node, path, defined, add_error, validate_expr, version)
            return

        validator = _EXPR_VALIDATORS.get(node_type)
        if validator:
            validator(node, path, defined, add_error, validate_expr)
        else:
            add_error(path, f"unexpected expression type '{node_type}'")

    def validate_stmt(
        node: Any, path: str, defined: set[str], in_func: bool, in_loop: bool = False
    ) -> None:
        node_type = expect_type(node, path)
        if node_type is None:
            return

        # Special case: Call needs version for validation
        if node_type == "Call":
            _validate_call_stmt(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt, version)
            return

        validator = _STMT_VALIDATORS.get(node_type)
        if validator:
            validator(node, path, defined, add_error, validate_expr, in_func, in_loop, validate_stmt)
        else:
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

    # Validate optional source_map
    source_map = doc.get("source_map")
    if source_map is not None:
        if not isinstance(source_map, dict):
            add_error("$.source_map", "source_map must be an object")
        else:
            seen_indices: set[int] = set()
            body_len = len(body)
            for key, indices in source_map.items():
                sm_path = f"$.source_map[{key}]"
                # Keys must be string representations of positive integers
                if not isinstance(key, str):
                    add_error(sm_path, "source_map key must be a string")
                    continue
                try:
                    line_num = int(key)
                except ValueError:
                    add_error(sm_path, f"source_map key '{key}' must be a string integer")
                    continue
                if line_num < 1:
                    add_error(sm_path, f"source_map key '{key}' must be a positive integer")
                # Values must be arrays of non-negative ints within body range
                if not isinstance(indices, list):
                    add_error(sm_path, "source_map value must be an array")
                    continue
                for j, idx in enumerate(indices):
                    if not isinstance(idx, int) or idx < 0:
                        add_error(f"{sm_path}[{j}]", "source_map index must be a non-negative integer")
                    elif idx >= body_len:
                        add_error(f"{sm_path}[{j}]", f"source_map index {idx} out of range (body has {body_len} statements)")
                    elif idx in seen_indices:
                        add_error(f"{sm_path}[{j}]", f"source_map index {idx} appears in multiple entries")
                    else:
                        seen_indices.add(idx)

    return errors

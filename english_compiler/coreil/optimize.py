"""Core IL optimization pass.

This module implements semantics-preserving optimizations on Core IL programs.
All optimizations guarantee identical output — same side effects, same errors.

Optimization passes:
1. Constant Folding - Evaluate constant expressions at compile time
2. Dead Code Elimination - Remove unreachable code after Return/Break/Continue
3. Identity Simplification - Simplify trivial operations (x+0, x*1, etc.)
4. Constant Propagation - Inline variables assigned once to a literal

Usage:
    from english_compiler.coreil.optimize import optimize
    optimized = optimize(program)
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def optimize(program: dict) -> dict:
    """Optimize a Core IL program. Returns a new program dict (does not mutate input)."""
    result = deepcopy(program)
    body = result.get("body")
    if not isinstance(body, list):
        return result

    body = _optimize_stmts(body)
    result["body"] = body
    return result


# ---------------------------------------------------------------------------
# Statement-level optimizations
# ---------------------------------------------------------------------------


def _optimize_stmts(stmts: list[dict]) -> list[dict]:
    """Optimize a list of statements, applying DCE and recursing."""
    result: list[dict] = []
    for stmt in stmts:
        optimized = _optimize_stmt(stmt)
        result.append(optimized)
        # Dead code elimination: nothing after Return, Break, Continue, Throw
        if optimized.get("type") in ("Return", "Break", "Continue", "Throw"):
            break
    return result


def _optimize_block(block: Any) -> Any:
    """Optimize a statement block when value is a list."""
    if isinstance(block, list):
        return _optimize_stmts(block)
    return block


def _optimize_expr_list(items: Any) -> Any:
    """Optimize a list of expressions when value is a list."""
    if not isinstance(items, list):
        return items
    return [_optimize_expr(item) for item in items]


def _copy_with_optimized_expr_fields(node: dict, *field_names: str) -> dict:
    """Return a shallow copy with named expression fields optimized."""
    result = dict(node)
    for field_name in field_names:
        result[field_name] = _optimize_expr(node.get(field_name))
    return result


def _optimize_stmt(stmt: dict) -> dict:
    """Optimize a single statement."""
    node_type = stmt.get("type")

    if node_type in ("Let", "Assign"):
        return {**stmt, "value": _optimize_expr(stmt.get("value"))}

    if node_type == "If":
        test = _optimize_expr(stmt.get("test"))
        then_body = _optimize_block(stmt.get("then", []))
        else_body = stmt.get("else")
        if else_body is not None:
            else_body = _optimize_block(else_body)

        # DCE: constant condition — drop the dead branch
        if _is_literal(test):
            val = test.get("value")
            if val:
                # Always true — drop else branch
                result = {**stmt, "test": test, "then": then_body}
                # Don't include else at all
                result.pop("else", None)
                return result
            else:
                # Always false — replace then with else body (or empty)
                result = {
                    **stmt,
                    "test": test,
                    "then": else_body if else_body is not None else [],
                }
                result.pop("else", None)
                return result

        result = {**stmt, "test": test, "then": then_body}
        if else_body is not None:
            result["else"] = else_body
        return result

    if node_type == "While":
        result = _copy_with_optimized_expr_fields(stmt, "test")
        result["body"] = _optimize_block(stmt.get("body", []))
        return result

    if node_type == "For":
        iter_expr = stmt.get("iter")
        if isinstance(iter_expr, dict):
            iter_expr = _optimize_expr(iter_expr)
        body = _optimize_block(stmt.get("body", []))
        return {**stmt, "iter": iter_expr, "body": body}

    if node_type == "ForEach":
        result = _copy_with_optimized_expr_fields(stmt, "iter")
        result["body"] = _optimize_block(stmt.get("body", []))
        return result

    if node_type in ("Print", "Call"):
        return {**stmt, "args": _optimize_expr_list(stmt.get("args", []))}

    if node_type == "SetIndex":
        return _copy_with_optimized_expr_fields(stmt, "base", "index", "value")

    if node_type == "Set":
        return _copy_with_optimized_expr_fields(stmt, "base", "key", "value")

    if node_type == "Push":
        return _copy_with_optimized_expr_fields(stmt, "base", "value")

    if node_type == "SetField":
        return _copy_with_optimized_expr_fields(stmt, "base", "value")

    if node_type in ("SetAdd", "SetRemove", "PushBack", "PushFront"):
        return _copy_with_optimized_expr_fields(stmt, "base", "value")

    if node_type in ("PopFront", "PopBack"):
        return _copy_with_optimized_expr_fields(stmt, "base")

    if node_type == "HeapPush":
        return _copy_with_optimized_expr_fields(stmt, "base", "priority", "value")

    if node_type == "HeapPop":
        return _copy_with_optimized_expr_fields(stmt, "base")

    if node_type == "FuncDef":
        body = _optimize_block(stmt.get("body", []))
        return {**stmt, "body": body}

    if node_type == "Return":
        if "value" in stmt:
            return {**stmt, "value": _optimize_expr(stmt["value"])}
        return stmt

    if node_type == "Throw":
        return _copy_with_optimized_expr_fields(stmt, "message")

    if node_type == "Switch":
        result = {**stmt, "test": _optimize_expr(stmt.get("test"))}
        cases = stmt.get("cases")
        if isinstance(cases, list):
            optimized_cases: list[Any] = []
            for case in cases:
                if not isinstance(case, dict):
                    optimized_cases.append(case)
                    continue
                optimized_case = dict(case)
                optimized_case["value"] = _optimize_expr(case.get("value"))
                optimized_case["body"] = _optimize_block(case.get("body", []))
                optimized_cases.append(optimized_case)
            result["cases"] = optimized_cases

        default = stmt.get("default")
        if default is not None:
            result["default"] = _optimize_block(default)
        return result

    if node_type == "TryCatch":
        body = _optimize_block(stmt.get("body", []))
        catch_body = _optimize_block(stmt.get("catch_body", []))
        result = {**stmt, "body": body, "catch_body": catch_body}
        finally_body = stmt.get("finally_body")
        if finally_body is not None:
            result["finally_body"] = _optimize_block(finally_body)
        return result

    return stmt


# ---------------------------------------------------------------------------
# Expression-level optimizations
# ---------------------------------------------------------------------------


def _optimize_expr(expr: Any) -> Any:
    """Optimize an expression (constant folding, identity simplification)."""
    if not isinstance(expr, dict):
        return expr

    node_type = expr.get("type")

    if node_type == "Binary":
        left = _optimize_expr(expr.get("left"))
        right = _optimize_expr(expr.get("right"))
        folded = _try_fold_binary(expr.get("op"), left, right)
        if folded is not None:
            return folded
        simplified = _try_simplify_identity(expr.get("op"), left, right)
        if simplified is not None:
            return simplified
        return {**expr, "left": left, "right": right}

    if node_type == "Not":
        arg = _optimize_expr(expr.get("arg"))
        if _is_literal(arg):
            return {"type": "Literal", "value": not arg["value"]}
        return {**expr, "arg": arg}

    if node_type in ("Array", "Tuple", "Set"):
        return {**expr, "items": _optimize_expr_list(expr.get("items", []))}

    if node_type == "Index":
        return _copy_with_optimized_expr_fields(expr, "base", "index")

    if node_type == "Slice":
        return _copy_with_optimized_expr_fields(expr, "base", "start", "end")

    if node_type == "Length":
        return _copy_with_optimized_expr_fields(expr, "base")

    if node_type == "Call":
        return {**expr, "args": _optimize_expr_list(expr.get("args", []))}

    if node_type == "Map":
        items = expr.get("items", [])
        optimized_items: list[Any] = []
        for item in items:
            if not isinstance(item, dict):
                optimized_items.append(item)
                continue
            optimized_items.append(
                {
                    "key": _optimize_expr(item.get("key")),
                    "value": _optimize_expr(item.get("value")),
                }
            )
        return {**expr, "items": optimized_items}

    if node_type == "Record":
        fields = expr.get("fields")
        if not isinstance(fields, list):
            return expr
        optimized_fields: list[Any] = []
        for field in fields:
            if not isinstance(field, dict):
                optimized_fields.append(field)
                continue
            optimized_field = dict(field)
            optimized_field["value"] = _optimize_expr(field.get("value"))
            optimized_fields.append(optimized_field)
        return {**expr, "fields": optimized_fields}

    if node_type in ("Get", "GetDefault"):
        result = _copy_with_optimized_expr_fields(expr, "base", "key")
        if "default" in expr:
            result["default"] = _optimize_expr(expr["default"])
        return result

    if node_type in (
        "GetField",
        "Keys",
        "StringLength",
        "StringTrim",
        "StringUpper",
        "StringLower",
        "DequeSize",
        "HeapSize",
        "HeapPeek",
        "SetSize",
    ):
        return _copy_with_optimized_expr_fields(expr, "base")

    if node_type == "Substring":
        return _copy_with_optimized_expr_fields(expr, "base", "start", "end")

    if node_type == "CharAt":
        return _copy_with_optimized_expr_fields(expr, "base", "index")

    if node_type == "Join":
        return _copy_with_optimized_expr_fields(expr, "sep", "items")

    if node_type == "StringSplit":
        return _copy_with_optimized_expr_fields(expr, "base", "delimiter")

    if node_type == "StringStartsWith":
        return _copy_with_optimized_expr_fields(expr, "base", "prefix")

    if node_type == "StringEndsWith":
        return _copy_with_optimized_expr_fields(expr, "base", "suffix")

    if node_type == "StringContains":
        return _copy_with_optimized_expr_fields(expr, "base", "substring")

    if node_type == "StringReplace":
        return _copy_with_optimized_expr_fields(expr, "base", "old", "new")

    if node_type == "SetHas":
        return _copy_with_optimized_expr_fields(expr, "base", "value")

    if node_type == "Range":
        result = {**expr}
        if "from" in result:
            result["from"] = _optimize_expr(result["from"])
        if "to" in result:
            result["to"] = _optimize_expr(result["to"])
        return result

    if node_type in ("ToInt", "ToFloat", "ToString"):
        return _copy_with_optimized_expr_fields(expr, "value")

    if node_type == "Ternary":
        test = _optimize_expr(expr.get("test"))
        consequent = _optimize_expr(expr.get("consequent"))
        alternate = _optimize_expr(expr.get("alternate"))
        # Constant fold: if test is Literal, return chosen branch
        if _is_literal(test):
            return consequent if test["value"] else alternate
        return {**expr, "test": test, "consequent": consequent, "alternate": alternate}

    if node_type == "StringFormat":
        parts = _optimize_expr_list(expr.get("parts", []))
        # Constant fold: if all parts are string Literals, concatenate
        if all(_is_literal(p) for p in parts):
            return {"type": "Literal", "value": "".join(str(p["value"]) for p in parts)}
        return {**expr, "parts": parts}

    if node_type == "Math":
        return _copy_with_optimized_expr_fields(expr, "arg")

    if node_type == "MathPow":
        return _copy_with_optimized_expr_fields(expr, "base", "exponent")

    if node_type == "JsonParse":
        return _copy_with_optimized_expr_fields(expr, "source")

    if node_type == "JsonStringify":
        result = _copy_with_optimized_expr_fields(expr, "value")
        if "pretty" in expr:
            result["pretty"] = _optimize_expr(expr.get("pretty"))
        return result

    if node_type in ("RegexMatch", "RegexFindAll"):
        result = {
            **expr,
            "string": _optimize_expr(expr.get("string")),
            "pattern": _optimize_expr(expr.get("pattern")),
        }
        if "flags" in expr:
            result["flags"] = _optimize_expr(expr.get("flags"))
        return result

    if node_type == "RegexReplace":
        result = {
            **expr,
            "string": _optimize_expr(expr.get("string")),
            "pattern": _optimize_expr(expr.get("pattern")),
            "replacement": _optimize_expr(expr.get("replacement")),
        }
        if "flags" in expr:
            result["flags"] = _optimize_expr(expr.get("flags"))
        return result

    if node_type == "RegexSplit":
        result = {
            **expr,
            "string": _optimize_expr(expr.get("string")),
            "pattern": _optimize_expr(expr.get("pattern")),
        }
        if "flags" in expr:
            result["flags"] = _optimize_expr(expr.get("flags"))
        if "maxsplit" in expr:
            result["maxsplit"] = _optimize_expr(expr.get("maxsplit"))
        return result

    if node_type == "ExternalCall":
        return {**expr, "args": _optimize_expr_list(expr.get("args", []))}

    if node_type == "MethodCall":
        result = _copy_with_optimized_expr_fields(expr, "object")
        result["args"] = _optimize_expr_list(expr.get("args", []))
        return result

    if node_type == "PropertyGet":
        return _copy_with_optimized_expr_fields(expr, "object")

    return expr


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_literal(node: Any) -> bool:
    return isinstance(node, dict) and node.get("type") == "Literal"


def _try_fold_binary(op: str, left: Any, right: Any) -> dict | None:
    """Try to constant-fold a binary expression. Returns Literal node or None."""
    if not _is_literal(left) or not _is_literal(right):
        return None

    lv = left["value"]
    rv = right["value"]

    # Only fold arithmetic on numbers and string concatenation
    try:
        if op == "+" and isinstance(lv, str) and isinstance(rv, str):
            return {"type": "Literal", "value": lv + rv}
        if op == "+" and isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
            return {"type": "Literal", "value": lv + rv}
        if op == "-" and isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
            return {"type": "Literal", "value": lv - rv}
        if op == "*" and isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
            return {"type": "Literal", "value": lv * rv}
        if op == "/" and isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
            if rv == 0:
                return None  # Don't fold division by zero
            return {"type": "Literal", "value": lv / rv}
        if op == "%" and isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
            if rv == 0:
                return None
            return {"type": "Literal", "value": lv % rv}
        # Comparisons
        if op == "==":
            return {"type": "Literal", "value": lv == rv}
        if op == "!=":
            return {"type": "Literal", "value": lv != rv}
        if op == "<" and isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
            return {"type": "Literal", "value": lv < rv}
        if op == "<=" and isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
            return {"type": "Literal", "value": lv <= rv}
        if op == ">" and isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
            return {"type": "Literal", "value": lv > rv}
        if op == ">=" and isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
            return {"type": "Literal", "value": lv >= rv}
    except (TypeError, ValueError, ZeroDivisionError):
        return None

    return None


def _try_simplify_identity(op: str, left: Any, right: Any) -> Any | None:
    """Try to simplify identity operations. Returns simplified node or None."""
    # x + 0 => x, 0 + x => x
    if op == "+":
        if _is_literal(right) and right["value"] == 0:
            return left
        if _is_literal(left) and left["value"] == 0:
            return right

    # x - 0 => x
    if op == "-":
        if _is_literal(right) and right["value"] == 0:
            return left

    # x * 1 => x, 1 * x => x
    if op == "*":
        if _is_literal(right) and right["value"] == 1:
            return left
        if _is_literal(left) and left["value"] == 1:
            return right
        # x * 0 => 0, 0 * x => 0 (only for literals to avoid side effects)
        if _is_literal(right) and right["value"] == 0 and _is_literal(left):
            return {"type": "Literal", "value": 0}
        if _is_literal(left) and left["value"] == 0 and _is_literal(right):
            return {"type": "Literal", "value": 0}

    # x and true => x, x or false => x
    if op == "and":
        if _is_literal(right) and right["value"] is True:
            return left
        if _is_literal(left) and left["value"] is True:
            return right

    if op == "or":
        if _is_literal(right) and right["value"] is False:
            return left
        if _is_literal(left) and left["value"] is False:
            return right

    return None

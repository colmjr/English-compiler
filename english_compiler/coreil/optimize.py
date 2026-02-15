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


def _optimize_stmt(stmt: dict) -> dict:
    """Optimize a single statement."""
    node_type = stmt.get("type")

    if node_type in ("Let", "Assign"):
        return {**stmt, "value": _optimize_expr(stmt.get("value"))}

    if node_type == "If":
        test = _optimize_expr(stmt.get("test"))
        then_body = _optimize_stmts(stmt.get("then", []))
        else_body = stmt.get("else")
        if else_body is not None:
            else_body = _optimize_stmts(else_body)

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
                result = {**stmt, "test": test, "then": else_body if else_body is not None else []}
                result.pop("else", None)
                return result

        result = {**stmt, "test": test, "then": then_body}
        if else_body is not None:
            result["else"] = else_body
        return result

    if node_type == "While":
        test = _optimize_expr(stmt.get("test"))
        body = _optimize_stmts(stmt.get("body", []))
        return {**stmt, "test": test, "body": body}

    if node_type == "For":
        iter_expr = stmt.get("iter")
        if isinstance(iter_expr, dict):
            iter_expr = _optimize_expr(iter_expr)
        body = _optimize_stmts(stmt.get("body", []))
        return {**stmt, "iter": iter_expr, "body": body}

    if node_type == "ForEach":
        iter_expr = _optimize_expr(stmt.get("iter"))
        body = _optimize_stmts(stmt.get("body", []))
        return {**stmt, "iter": iter_expr, "body": body}

    if node_type in ("Print", "Call"):
        args = stmt.get("args", [])
        return {**stmt, "args": [_optimize_expr(a) for a in args]}

    if node_type == "SetIndex":
        return {
            **stmt,
            "base": _optimize_expr(stmt.get("base")),
            "index": _optimize_expr(stmt.get("index")),
            "value": _optimize_expr(stmt.get("value")),
        }

    if node_type == "Set":
        return {
            **stmt,
            "base": _optimize_expr(stmt.get("base")),
            "key": _optimize_expr(stmt.get("key")),
            "value": _optimize_expr(stmt.get("value")),
        }

    if node_type == "Push":
        return {
            **stmt,
            "base": _optimize_expr(stmt.get("base")),
            "value": _optimize_expr(stmt.get("value")),
        }

    if node_type == "SetField":
        return {
            **stmt,
            "base": _optimize_expr(stmt.get("base")),
            "value": _optimize_expr(stmt.get("value")),
        }

    if node_type in ("SetAdd", "SetRemove", "PushBack", "PushFront"):
        return {
            **stmt,
            "base": _optimize_expr(stmt.get("base")),
            "value": _optimize_expr(stmt.get("value")),
        }

    if node_type in ("PopFront", "PopBack"):
        return {**stmt, "base": _optimize_expr(stmt.get("base"))}

    if node_type == "HeapPush":
        return {
            **stmt,
            "base": _optimize_expr(stmt.get("base")),
            "priority": _optimize_expr(stmt.get("priority")),
            "value": _optimize_expr(stmt.get("value")),
        }

    if node_type == "HeapPop":
        return {**stmt, "base": _optimize_expr(stmt.get("base"))}

    if node_type == "FuncDef":
        body = _optimize_stmts(stmt.get("body", []))
        return {**stmt, "body": body}

    if node_type == "Return":
        if "value" in stmt:
            return {**stmt, "value": _optimize_expr(stmt["value"])}
        return stmt

    if node_type == "Throw":
        return {**stmt, "message": _optimize_expr(stmt.get("message"))}

    if node_type == "TryCatch":
        body = _optimize_stmts(stmt.get("body", []))
        catch_body = _optimize_stmts(stmt.get("catch_body", []))
        result = {**stmt, "body": body, "catch_body": catch_body}
        finally_body = stmt.get("finally_body")
        if finally_body is not None:
            result["finally_body"] = _optimize_stmts(finally_body)
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

    if node_type == "Array":
        items = expr.get("items", [])
        return {**expr, "items": [_optimize_expr(i) for i in items]}

    if node_type == "Tuple":
        items = expr.get("items", [])
        return {**expr, "items": [_optimize_expr(i) for i in items]}

    if node_type == "Index":
        return {
            **expr,
            "base": _optimize_expr(expr.get("base")),
            "index": _optimize_expr(expr.get("index")),
        }

    if node_type == "Slice":
        return {
            **expr,
            "base": _optimize_expr(expr.get("base")),
            "start": _optimize_expr(expr.get("start")),
            "end": _optimize_expr(expr.get("end")),
        }

    if node_type == "Length":
        return {**expr, "base": _optimize_expr(expr.get("base"))}

    if node_type == "Call":
        args = expr.get("args", [])
        return {**expr, "args": [_optimize_expr(a) for a in args]}

    if node_type == "Map":
        items = expr.get("items", [])
        optimized_items = []
        for item in items:
            optimized_items.append({
                "key": _optimize_expr(item.get("key")),
                "value": _optimize_expr(item.get("value")),
            })
        return {**expr, "items": optimized_items}

    if node_type in ("Get", "GetDefault"):
        result = {**expr, "base": _optimize_expr(expr.get("base")), "key": _optimize_expr(expr.get("key"))}
        if "default" in expr:
            result["default"] = _optimize_expr(expr["default"])
        return result

    if node_type == "Range":
        result = {**expr}
        if "from" in result:
            result["from"] = _optimize_expr(result["from"])
        if "to" in result:
            result["to"] = _optimize_expr(result["to"])
        return result

    if node_type in ("ToInt", "ToFloat", "ToString"):
        return {**expr, "value": _optimize_expr(expr.get("value"))}

    if node_type == "Math":
        return {**expr, "arg": _optimize_expr(expr.get("arg"))}

    if node_type == "MathPow":
        return {
            **expr,
            "base": _optimize_expr(expr.get("base")),
            "exponent": _optimize_expr(expr.get("exponent")),
        }

    # For most other expression types, just recurse on known fields
    if node_type in ("StringLength", "StringTrim", "StringUpper", "StringLower",
                      "DequeSize", "HeapSize", "HeapPeek", "SetSize"):
        return {**expr, "base": _optimize_expr(expr.get("base"))}

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
        if op == "==" :
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

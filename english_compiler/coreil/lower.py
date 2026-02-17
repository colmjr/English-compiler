"""Lower Core IL syntax sugar into core constructs.

This file implements Core IL v1.8 lowering pass.
Core IL v1.8 adds TryCatch and Throw for exception handling.

Lowering transformations:
- For/ForEach loops are PRESERVED (not lowered to While) to properly
  support Break and Continue statements. Expressions inside them are lowered.
- Range expressions inside For loops are preserved.

All other nodes (including Break, Continue) pass through unchanged.

Note: Prior to v1.7, For/ForEach were lowered to While loops. This was
changed to support Continue correctly (Continue in a lowered While loop
would skip the increment, causing infinite loops).

Backward compatibility: Accepts v0.1 through v1.8 programs.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def lower_coreil(doc: dict) -> dict:
    """Lower Core IL syntax sugar into core constructs.

    Args:
        doc: Core IL document to lower.

    Returns:
        Lowered Core IL document.
    """
    if not isinstance(doc, dict):
        raise ValueError("document must be an object")

    lowered = deepcopy(doc)
    body = lowered.get("body")
    if not isinstance(body, list):
        raise ValueError("body must be a list")

    lowered["body"] = _lower_statements(body)
    return lowered


def _lower_statements(stmts: list[dict]) -> list[dict]:
    lowered: list[dict] = []
    for stmt in stmts:
        lowered.extend(_lower_statement(stmt))
    return lowered


def _lower_statement(stmt: Any) -> list[dict]:
    if not isinstance(stmt, dict):
        raise ValueError("statement must be an object")

    node_type = stmt.get("type")
    if node_type == "For":
        return _lower_for(stmt)

    if node_type == "ForEach":
        return _lower_foreach(stmt)

    if node_type in {"If", "While"}:
        lowered = dict(stmt)
        test = lowered.get("test")
        if test is not None:
            lowered["test"] = _lower_expr(test)
        body = lowered.get("body")
        if body is not None:
            lowered["body"] = _lower_statements(body)
        then_body = lowered.get("then")
        if then_body is not None:
            lowered["then"] = _lower_statements(then_body)
        else_body = lowered.get("else")
        if else_body is not None:
            lowered["else"] = _lower_statements(else_body)
        return [lowered]

    if node_type == "FuncDef":
        lowered = dict(stmt)
        body = lowered.get("body")
        if body is not None:
            lowered["body"] = _lower_statements(body)
        return [lowered]

    if node_type == "Return":
        lowered = dict(stmt)
        if "value" in lowered:
            lowered["value"] = _lower_expr(lowered.get("value"))
        return [lowered]

    if node_type in {"Let", "Assign"}:
        lowered = dict(stmt)
        lowered["value"] = _lower_expr(lowered.get("value"))
        return [lowered]

    if node_type in {"Print", "Call"}:
        lowered = dict(stmt)
        args = lowered.get("args")
        if isinstance(args, list):
            lowered["args"] = [_lower_expr(arg) for arg in args]
        return [lowered]

    if node_type == "SetIndex":
        lowered = dict(stmt)
        lowered["base"] = _lower_expr(lowered.get("base"))
        lowered["index"] = _lower_expr(lowered.get("index"))
        lowered["value"] = _lower_expr(lowered.get("value"))
        return [lowered]

    if node_type == "Set":
        lowered = dict(stmt)
        lowered["base"] = _lower_expr(lowered.get("base"))
        lowered["key"] = _lower_expr(lowered.get("key"))
        lowered["value"] = _lower_expr(lowered.get("value"))
        return [lowered]

    if node_type == "Throw":
        lowered = dict(stmt)
        lowered["message"] = _lower_expr(lowered.get("message"))
        return [lowered]

    if node_type == "TryCatch":
        lowered = dict(stmt)
        body = lowered.get("body")
        if body is not None:
            lowered["body"] = _lower_statements(body)
        catch_body = lowered.get("catch_body")
        if catch_body is not None:
            lowered["catch_body"] = _lower_statements(catch_body)
        finally_body = lowered.get("finally_body")
        if finally_body is not None:
            lowered["finally_body"] = _lower_statements(finally_body)
        return [lowered]

    if node_type == "Switch":
        lowered = dict(stmt)
        lowered["test"] = _lower_expr(lowered.get("test"))
        cases = lowered.get("cases")
        if isinstance(cases, list):
            lowered_cases = []
            for case in cases:
                lc = dict(case)
                lc["value"] = _lower_expr(lc.get("value"))
                case_body = lc.get("body")
                if isinstance(case_body, list):
                    lc["body"] = _lower_statements(case_body)
                lowered_cases.append(lc)
            lowered["cases"] = lowered_cases
        default = lowered.get("default")
        if isinstance(default, list):
            lowered["default"] = _lower_statements(default)
        return [lowered]

    return [stmt]


def _lower_for(stmt: dict) -> list[dict]:
    """Preserve For statement but lower expressions inside it.

    For/ForEach are kept as-is (not lowered to While) to properly support
    Continue statements. The backends emit native for loops.
    """
    var = stmt.get("var")
    if not isinstance(var, str) or not var:
        raise ValueError("For.var must be a non-empty string")
    iter_expr = stmt.get("iter")
    if not isinstance(iter_expr, dict):
        raise ValueError("For.iter must be an expression")
    body = stmt.get("body")
    if not isinstance(body, list):
        raise ValueError("For.body must be a list")

    lowered = {
        "type": "For",
        "var": var,
        "iter": _lower_expr(iter_expr),
        "body": _lower_statements(body),
    }
    return [lowered]


def _lower_foreach(stmt: dict) -> list[dict]:
    """Preserve ForEach statement but lower expressions inside it.

    ForEach is kept as-is (not lowered to While) to properly support
    Continue statements. The backends emit native for loops.
    """
    var = stmt.get("var")
    if not isinstance(var, str) or not var:
        raise ValueError("ForEach.var must be a non-empty string")
    iter_expr = stmt.get("iter")
    if not isinstance(iter_expr, dict):
        raise ValueError("ForEach.iter must be an expression")
    body = stmt.get("body")
    if not isinstance(body, list):
        raise ValueError("ForEach.body must be a list")

    lowered = {
        "type": "ForEach",
        "var": var,
        "iter": _lower_expr(iter_expr),
        "body": _lower_statements(body),
    }
    return [lowered]


def _lower_expr(expr: Any) -> Any:
    if not isinstance(expr, dict):
        return expr

    node_type = expr.get("type")
    # Range expressions are preserved for For loops
    if node_type == "Range":
        lowered = dict(expr)
        if "from" in lowered:
            lowered["from"] = _lower_expr(lowered["from"])
        if "to" in lowered:
            lowered["to"] = _lower_expr(lowered["to"])
        return lowered

    if node_type == "Binary":
        return {
            "type": "Binary",
            "op": expr.get("op"),
            "left": _lower_expr(expr.get("left")),
            "right": _lower_expr(expr.get("right")),
        }

    if node_type == "Array":
        items = expr.get("items")
        if isinstance(items, list):
            return {"type": "Array", "items": [_lower_expr(item) for item in items]}

    if node_type in {"Index", "Length"}:
        lowered = dict(expr)
        lowered["base"] = _lower_expr(expr.get("base"))
        if node_type == "Index":
            lowered["index"] = _lower_expr(expr.get("index"))
        return lowered

    if node_type == "Call":
        args = expr.get("args")
        if isinstance(args, list):
            return {
                "type": "Call",
                "name": expr.get("name"),
                "args": [_lower_expr(arg) for arg in args],
            }

    if node_type == "Map":
        items = expr.get("items")
        if isinstance(items, list):
            lowered_items = []
            for item in items:
                if isinstance(item, dict):
                    lowered_items.append({
                        "key": _lower_expr(item.get("key")),
                        "value": _lower_expr(item.get("value")),
                    })
            return {"type": "Map", "items": lowered_items}

    if node_type == "Get":
        return {
            "type": "Get",
            "base": _lower_expr(expr.get("base")),
            "key": _lower_expr(expr.get("key")),
        }

    return expr

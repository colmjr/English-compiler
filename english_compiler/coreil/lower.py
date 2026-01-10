"""Lower Core IL syntax sugar into core constructs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def lower_coreil(doc: dict) -> dict:
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

    return [stmt]


def _lower_for(stmt: dict) -> list[dict]:
    var = stmt.get("var")
    if not isinstance(var, str) or not var:
        raise ValueError("For.var must be a non-empty string")
    iter_expr = stmt.get("iter")
    if not isinstance(iter_expr, dict):
        raise ValueError("For.iter must be an expression")
    body = stmt.get("body")
    if not isinstance(body, list):
        raise ValueError("For.body must be a list")

    if iter_expr.get("type") != "Range":
        raise ValueError("For.iter must be a Range expression")

    from_expr = iter_expr.get("from")
    to_expr = iter_expr.get("to")
    if from_expr is None or to_expr is None:
        raise ValueError("Range must include from and to")

    inclusive = iter_expr.get("inclusive", False)
    if inclusive not in {True, False}:
        raise ValueError("Range.inclusive must be a boolean when provided")

    init_stmt = {
        "type": "Let",
        "name": var,
        "value": _lower_expr(from_expr),
    }

    compare_op = "<=" if inclusive else "<"
    while_test = {
        "type": "Binary",
        "op": compare_op,
        "left": {"type": "Var", "name": var},
        "right": _lower_expr(to_expr),
    }

    lowered_body = _lower_statements(body)
    increment = {
        "type": "Assign",
        "name": var,
        "value": {
            "type": "Binary",
            "op": "+",
            "left": {"type": "Var", "name": var},
            "right": {"type": "Literal", "value": 1},
        },
    }

    while_stmt = {
        "type": "While",
        "test": while_test,
        "body": lowered_body + [increment],
    }

    return [init_stmt, while_stmt]


def _lower_expr(expr: Any) -> Any:
    if not isinstance(expr, dict):
        return expr

    node_type = expr.get("type")
    if node_type == "Range":
        raise ValueError("Range expressions must be used with For")

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

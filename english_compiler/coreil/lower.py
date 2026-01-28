"""Lower Core IL syntax sugar into core constructs.

This file implements Core IL v1.7 lowering pass.
Core IL v1.7 adds Break and Continue loop control statements.

Lowering transformations:
- For/ForEach loops are PRESERVED (not lowered to While) to properly
  support Break and Continue statements. Expressions inside them are lowered.
- Range expressions inside For loops are preserved.

All other nodes (including Break, Continue) pass through unchanged.

Note: Prior to v1.7, For/ForEach were lowered to While loops. This was
changed to support Continue correctly (Continue in a lowered While loop
would skip the increment, causing infinite loops).

Backward compatibility: Accepts v0.1 through v1.7 programs.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LoweringContext:
    """Context object for lowering pass to avoid global mutable state."""

    temp_counter: int = field(default=0)

    def next_temp_suffix(self) -> int:
        """Get next unique suffix for temp variables."""
        suffix = self.temp_counter
        self.temp_counter += 1
        return suffix


def lower_coreil(doc: dict, *, ctx: LoweringContext | None = None) -> dict:
    """Lower Core IL syntax sugar into core constructs.

    Args:
        doc: Core IL document to lower.
        ctx: Optional lowering context. If not provided, a fresh context is created.
             Pass a shared context when lowering multiple documents to ensure
             unique temp variable names across all of them.

    Returns:
        Lowered Core IL document.
    """
    if not isinstance(doc, dict):
        raise ValueError("document must be an object")

    if ctx is None:
        ctx = LoweringContext()

    lowered = deepcopy(doc)
    body = lowered.get("body")
    if not isinstance(body, list):
        raise ValueError("body must be a list")

    lowered["body"] = _lower_statements(body, ctx)
    return lowered


def _lower_statements(stmts: list[dict], ctx: LoweringContext) -> list[dict]:
    lowered: list[dict] = []
    for stmt in stmts:
        lowered.extend(_lower_statement(stmt, ctx))
    return lowered


def _lower_statement(stmt: Any, ctx: LoweringContext) -> list[dict]:
    if not isinstance(stmt, dict):
        raise ValueError("statement must be an object")

    node_type = stmt.get("type")
    if node_type == "For":
        return _lower_for(stmt, ctx)

    if node_type == "ForEach":
        return _lower_foreach(stmt, ctx)

    if node_type in {"If", "While"}:
        lowered = dict(stmt)
        test = lowered.get("test")
        if test is not None:
            lowered["test"] = _lower_expr(test)
        body = lowered.get("body")
        if body is not None:
            lowered["body"] = _lower_statements(body, ctx)
        then_body = lowered.get("then")
        if then_body is not None:
            lowered["then"] = _lower_statements(then_body, ctx)
        else_body = lowered.get("else")
        if else_body is not None:
            lowered["else"] = _lower_statements(else_body, ctx)
        return [lowered]

    if node_type == "FuncDef":
        lowered = dict(stmt)
        body = lowered.get("body")
        if body is not None:
            lowered["body"] = _lower_statements(body, ctx)
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


def _lower_for(stmt: dict, ctx: LoweringContext) -> list[dict]:
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

    # Lower expressions inside the For but keep the For structure
    lowered = {
        "type": "For",
        "var": var,
        "iter": _lower_expr(iter_expr),
        "body": _lower_statements(body, ctx),
    }
    return [lowered]


def _lower_foreach(stmt: dict, ctx: LoweringContext) -> list[dict]:
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

    # Lower expressions inside the ForEach but keep the ForEach structure
    lowered = {
        "type": "ForEach",
        "var": var,
        "iter": _lower_expr(iter_expr),
        "body": _lower_statements(body, ctx),
    }
    return [lowered]


def _lower_expr(expr: Any) -> Any:
    if not isinstance(expr, dict):
        return expr

    node_type = expr.get("type")
    # Range expressions are preserved for For loops
    if node_type == "Range":
        # Lower the from/to expressions inside the Range but keep the Range structure
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

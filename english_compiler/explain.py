"""Reverse compiler: Core IL program to English explanation.

This module walks a Core IL AST and produces a human-readable English
description of what the program does. It is fully deterministic (no LLM).

Usage:
    from english_compiler.explain import explain
    text = explain(program_dict)
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Expression rendering
# ---------------------------------------------------------------------------

_OP_WORDS = {
    "+": "plus", "-": "minus", "*": "times", "/": "divided by",
    "%": "mod", "==": "is equal to", "!=": "is not equal to",
    "<": "is less than", "<=": "is less than or equal to",
    ">": "is greater than", ">=": "is greater than or equal to",
    "and": "and", "or": "or",
}

_OP_SYMBOLS = {
    "+": "+", "-": "-", "*": "*", "/": "/", "%": "%",
    "==": "==", "!=": "!=", "<": "<", "<=": "<=",
    ">": ">", ">=": ">=", "and": "and", "or": "or",
}


def _expr_str(node: Any, verbose: bool = False) -> str:
    """Return a compact human-readable representation of an expression."""
    if not isinstance(node, dict):
        return repr(node)

    t = node.get("type")

    if t == "Literal":
        v = node.get("value")
        if isinstance(v, str):
            return f'"{v}"'
        if isinstance(v, bool):
            return "true" if v else "false"
        if v is None:
            return "null"
        return str(v)

    if t == "Var":
        return node.get("name", "?")

    if t == "Binary":
        op = node.get("op", "?")
        left = _expr_str(node.get("left"), verbose)
        right = _expr_str(node.get("right"), verbose)
        sym = _OP_WORDS.get(op, op) if verbose else _OP_SYMBOLS.get(op, op)
        return f"({left} {sym} {right})"

    if t == "Not":
        arg = _expr_str(node.get("arg"), verbose)
        return f"not {arg}"

    if t == "Array":
        items = [_expr_str(i, verbose) for i in node.get("items", [])]
        return "[" + ", ".join(items) + "]"

    if t == "Tuple":
        items = [_expr_str(i, verbose) for i in node.get("items", [])]
        return "(" + ", ".join(items) + ")"

    if t == "Map":
        pairs = []
        for item in node.get("items", []):
            k = _expr_str(item.get("key"), verbose)
            v = _expr_str(item.get("value"), verbose)
            pairs.append(f"{k}: {v}")
        return "{" + ", ".join(pairs) + "}"

    if t == "Record":
        parts = []
        for f in node.get("fields", []):
            parts.append(f"{f.get('name', '?')}: {_expr_str(f.get('value'), verbose)}")
        return "Record{" + ", ".join(parts) + "}"

    if t == "Set":
        items = [_expr_str(i, verbose) for i in node.get("items", [])]
        return "Set{" + ", ".join(items) + "}"

    if t == "Index":
        return f"{_expr_str(node.get('base'), verbose)}[{_expr_str(node.get('index'), verbose)}]"

    if t == "Slice":
        return f"{_expr_str(node.get('base'), verbose)}[{_expr_str(node.get('start'), verbose)}:{_expr_str(node.get('end'), verbose)}]"

    if t == "Length":
        return f"length({_expr_str(node.get('base'), verbose)})"

    if t == "StringLength":
        return f"string_length({_expr_str(node.get('base'), verbose)})"

    if t in ("Get", "GetDefault"):
        base = _expr_str(node.get("base"), verbose)
        key = _expr_str(node.get("key"), verbose)
        if t == "GetDefault":
            default = _expr_str(node.get("default"), verbose)
            return f"{base}.get({key}, {default})"
        return f"{base}[{key}]"

    if t == "GetField":
        return f"{_expr_str(node.get('base'), verbose)}.{node.get('name', '?')}"

    if t == "Keys":
        return f"keys({_expr_str(node.get('base'), verbose)})"

    if t == "SetHas":
        return f"{_expr_str(node.get('value'), verbose)} in {_expr_str(node.get('base'), verbose)}"

    if t == "Call":
        name = node.get("name", "?")
        args = [_expr_str(a, verbose) for a in node.get("args", [])]
        return f"{name}({', '.join(args)})"

    if t == "Range":
        fr = _expr_str(node.get("from"), verbose)
        to = _expr_str(node.get("to"), verbose)
        inclusive = node.get("inclusive", False)
        return f"{fr} to {to}" + (" (inclusive)" if inclusive else "")

    if t in ("ToInt", "ToFloat", "ToString"):
        return f"{t.lower()}({_expr_str(node.get('value'), verbose)})"

    if t == "Math":
        return f"{node.get('op', '?')}({_expr_str(node.get('arg'), verbose)})"

    if t == "MathPow":
        return f"pow({_expr_str(node.get('base'), verbose)}, {_expr_str(node.get('exponent'), verbose)})"

    if t == "MathConst":
        return node.get("name", "?")

    if t == "DequeNew":
        return "new deque"
    if t == "HeapNew":
        return "new heap"

    # Fallback for other expression types
    return f"<{t}>"


# ---------------------------------------------------------------------------
# Statement explanation
# ---------------------------------------------------------------------------

def _indent(text: str, level: int) -> str:
    return "   " * level + text


def _explain_stmt(node: dict, level: int, verbose: bool) -> list[str]:
    """Return explanation lines for a single statement."""
    lines: list[str] = []
    t = node.get("type")

    if t == "Let":
        lines.append(_indent(f"Set {node.get('name', '?')} to {_expr_str(node.get('value'), verbose)}.", level))

    elif t == "Assign":
        lines.append(_indent(f"Update {node.get('name', '?')} to {_expr_str(node.get('value'), verbose)}.", level))

    elif t == "Print":
        parts = [_expr_str(a, verbose) for a in node.get("args", [])]
        lines.append(_indent(f"Print {', '.join(parts)}.", level))

    elif t == "If":
        lines.append(_indent(f"If {_expr_str(node.get('test'), verbose)}:", level))
        for s in node.get("then", []):
            lines.extend(_explain_stmt(s, level + 1, verbose))
        if node.get("else"):
            lines.append(_indent("Otherwise:", level))
            for s in node["else"]:
                lines.extend(_explain_stmt(s, level + 1, verbose))

    elif t == "While":
        lines.append(_indent(f"While {_expr_str(node.get('test'), verbose)}:", level))
        for s in node.get("body", []):
            lines.extend(_explain_stmt(s, level + 1, verbose))

    elif t == "For":
        var = node.get("var", "?")
        iter_expr = node.get("iter")
        if isinstance(iter_expr, dict) and iter_expr.get("type") == "Range":
            fr = _expr_str(iter_expr.get("from"), verbose)
            to = _expr_str(iter_expr.get("to"), verbose)
            end_word = "through" if iter_expr.get("inclusive", False) else "up to (exclusive)"
            lines.append(_indent(f"For {var} from {fr} {end_word} {to}:", level))
        else:
            lines.append(_indent(f"For {var} in {_expr_str(iter_expr, verbose)}:", level))
        for s in node.get("body", []):
            lines.extend(_explain_stmt(s, level + 1, verbose))

    elif t == "ForEach":
        lines.append(_indent(f"For each {node.get('var', '?')} in {_expr_str(node.get('iter'), verbose)}:", level))
        for s in node.get("body", []):
            lines.extend(_explain_stmt(s, level + 1, verbose))

    elif t == "FuncDef":
        name = node.get("name", "?")
        params = node.get("params", [])
        if params:
            param_str = ", ".join(f'"{p}"' for p in params)
            lines.append(_indent(f'Define function "{name}" with parameter(s) {param_str}:', level))
        else:
            lines.append(_indent(f'Define function "{name}" (no parameters):', level))
        for s in node.get("body", []):
            lines.extend(_explain_stmt(s, level + 1, verbose))

    elif t == "Return":
        if "value" in node:
            lines.append(_indent(f"Return {_expr_str(node['value'], verbose)}.", level))
        else:
            lines.append(_indent("Return.", level))

    elif t == "Call":
        args = [_expr_str(a, verbose) for a in node.get("args", [])]
        lines.append(_indent(f"Call {node.get('name', '?')}({', '.join(args)}).", level))

    elif t == "Push":
        lines.append(_indent(f"Append {_expr_str(node.get('value'), verbose)} to {_expr_str(node.get('base'), verbose)}.", level))

    elif t == "SetIndex":
        lines.append(_indent(f"Set {_expr_str(node.get('base'), verbose)}[{_expr_str(node.get('index'), verbose)}] to {_expr_str(node.get('value'), verbose)}.", level))

    elif t == "Set":
        lines.append(_indent(f"Set {_expr_str(node.get('base'), verbose)}[{_expr_str(node.get('key'), verbose)}] to {_expr_str(node.get('value'), verbose)}.", level))

    elif t == "SetField":
        lines.append(_indent(f"Set {_expr_str(node.get('base'), verbose)}.{node.get('name', '?')} to {_expr_str(node.get('value'), verbose)}.", level))

    elif t == "Break":
        lines.append(_indent("Break out of the loop.", level))

    elif t == "Continue":
        lines.append(_indent("Continue to the next iteration.", level))

    elif t == "Throw":
        lines.append(_indent(f"Throw an error: {_expr_str(node.get('message'), verbose)}.", level))

    elif t == "TryCatch":
        lines.append(_indent("Try:", level))
        for s in node.get("body", []):
            lines.extend(_explain_stmt(s, level + 1, verbose))
        lines.append(_indent(f"If an error occurs (caught as {node.get('catch_var', 'e')}):", level))
        for s in node.get("catch_body", []):
            lines.extend(_explain_stmt(s, level + 1, verbose))
        if node.get("finally_body"):
            lines.append(_indent("Finally (always runs):", level))
            for s in node["finally_body"]:
                lines.extend(_explain_stmt(s, level + 1, verbose))

    else:
        lines.append(_indent(f"[{t} statement]", level))

    return lines


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------

def _summarize(body: list[dict]) -> str | None:
    """Try to produce a one-line summary of the program."""
    func_names = [s.get("name", "?") for s in body if s.get("type") == "FuncDef"]
    has_print = any(s.get("type") == "Print" for s in body)

    parts: list[str] = []
    if func_names:
        parts.append(f"defines function(s) {', '.join(repr(n) for n in func_names)}")
    if has_print:
        parts.append("prints output")
    if not parts:
        return None
    return "This program " + " and ".join(parts) + "."


def explain(program: dict, *, verbose: bool = False) -> str:
    """Generate an English explanation of a Core IL program.

    Args:
        program: A parsed Core IL document (dict with "version" and "body").
        verbose: If True, produce more detailed descriptions.

    Returns:
        A multi-line string with the English explanation.
    """
    if not isinstance(program, dict):
        return "Error: program must be a dict."

    body = program.get("body")
    if not isinstance(body, list):
        return "Error: program has no body."

    if not body:
        return "This program does nothing (empty body)."

    lines: list[str] = []

    summary = _summarize(body)
    if summary:
        lines.append(summary)
        lines.append("")

    for i, stmt in enumerate(body, start=1):
        stmt_lines = _explain_stmt(stmt, 0, verbose)
        if stmt_lines:
            stmt_lines[0] = f"{i}. {stmt_lines[0].lstrip()}"
            for j in range(1, len(stmt_lines)):
                stmt_lines[j] = "   " + stmt_lines[j]
        lines.extend(stmt_lines)

    return "\n".join(lines)

"""Core IL static analysis (linter).

This module provides lint rules that catch issues beyond what validate.py
detects. It runs on pre-lowered Core IL (For/ForEach still intact).

Rules:
- unused-variable: Let declaration with no Var reference to it
- unreachable-code: Statements after Return/Break/Continue/Throw in same block
- empty-body: If/While/For/ForEach/TryCatch with body: []
- variable-shadowing: Let on an already-defined variable name (should be Assign)

Usage:
    from english_compiler.coreil.lint import lint_coreil

    warnings = lint_coreil(doc)
    for w in warnings:
        print(f"[{w['severity']}] {w['rule']}: {w['message']}")
"""

from __future__ import annotations

from typing import Any

from .node_nav import iter_nodes


def lint_coreil(doc: dict) -> list[dict]:
    """Run static analysis on a Core IL document.

    Args:
        doc: Core IL document (pre-lowered, as parsed from JSON).

    Returns:
        List of diagnostic dicts with keys:
        - rule: str (e.g., "unused-variable")
        - message: str (human-readable description)
        - severity: str ("warning" or "error")
        - path: str (JSON path to the offending node)
    """
    diagnostics: list[dict] = []
    body = doc.get("body")
    if not isinstance(body, list):
        return diagnostics

    _check_block(body, "$", set(), diagnostics)
    return diagnostics


def _add(diagnostics: list[dict], rule: str, message: str, path: str,
         severity: str = "warning") -> None:
    diagnostics.append({
        "rule": rule,
        "message": message,
        "severity": severity,
        "path": path,
    })


# ---------------------------------------------------------------------------
# Traversal helpers
# ---------------------------------------------------------------------------

def _collect_var_refs(node: Any) -> set[str]:
    """Collect all Var node names in an expression or statement tree."""
    refs: set[str] = set()
    for candidate in iter_nodes(node):
        if candidate.get("type") != "Var":
            continue
        name = candidate.get("name")
        if isinstance(name, str):
            refs.add(name)
    return refs


_TERMINATOR_TYPES = {"Return", "Break", "Continue", "Throw"}

_BODY_CONTAINERS = {
    "If": ("then", "else"),
    "While": ("body",),
    "For": ("body",),
    "ForEach": ("body",),
    "TryCatch": ("body", "catch_body", "finally_body"),
    "Switch": (),  # Switch cases handled separately
}


def _check_block(
    stmts: list,
    path: str,
    defined: set[str],
    diagnostics: list[dict],
) -> None:
    """Check a block of statements for lint issues.

    Args:
        stmts: List of statement nodes.
        path: JSON path prefix for diagnostics.
        defined: Set of variable names defined in this scope.
        diagnostics: Accumulator for warnings.
    """
    # --- Rule: unreachable-code ---
    for i, stmt in enumerate(stmts):
        if not isinstance(stmt, dict):
            continue
        stype = stmt.get("type")
        if stype in _TERMINATOR_TYPES and i < len(stmts) - 1:
            _add(diagnostics, "unreachable-code",
                 f"statements after {stype} are unreachable",
                 f"{path}[{i + 1}]")
            break  # only report once per block

    # --- Per-statement checks ---
    # Track Let declarations in this block for unused-variable analysis.
    # We collect all Var refs in the *rest* of the block + sub-blocks after each Let.
    let_decls: list[tuple[int, str]] = []  # (index, name)

    for i, stmt in enumerate(stmts):
        if not isinstance(stmt, dict):
            continue
        stype = stmt.get("type")
        stmt_path = f"{path}[{i}]"

        # --- Rule: variable-shadowing ---
        if stype == "Let":
            name = stmt.get("name")
            if isinstance(name, str):
                if name in defined:
                    _add(diagnostics, "variable-shadowing",
                         f"variable '{name}' shadows an existing definition (use Assign instead)",
                         stmt_path)
                let_decls.append((i, name))
                defined = defined | {name}  # immutable update for scope tracking

        elif stype == "Assign":
            name = stmt.get("name")
            if isinstance(name, str):
                defined = defined | {name}

        # --- Rule: empty-body ---
        if stype in _BODY_CONTAINERS:
            for body_key in _BODY_CONTAINERS[stype]:
                body = stmt.get(body_key)
                if isinstance(body, list) and len(body) == 0:
                    _add(diagnostics, "empty-body",
                         f"{stype} has empty {body_key}",
                         f"{stmt_path}.{body_key}")

        # --- Recurse into sub-blocks ---
        if stype == "If":
            then_body = stmt.get("then")
            if isinstance(then_body, list):
                _check_block(then_body, f"{stmt_path}.then", defined, diagnostics)
            else_body = stmt.get("else")
            if isinstance(else_body, list):
                _check_block(else_body, f"{stmt_path}.else", defined, diagnostics)

        elif stype == "While":
            body = stmt.get("body")
            if isinstance(body, list):
                _check_block(body, f"{stmt_path}.body", defined, diagnostics)

        elif stype in ("For", "ForEach"):
            var_name = stmt.get("var")
            inner_defined = defined | ({var_name} if isinstance(var_name, str) else set())
            body = stmt.get("body")
            if isinstance(body, list):
                _check_block(body, f"{stmt_path}.body", inner_defined, diagnostics)

        elif stype == "FuncDef":
            params = stmt.get("params", [])
            func_name = stmt.get("name")
            func_defined = set(p for p in params if isinstance(p, str))
            if isinstance(func_name, str):
                defined = defined | {func_name}
                func_defined.add(func_name)
            body = stmt.get("body")
            if isinstance(body, list):
                _check_block(body, f"{stmt_path}.body", func_defined, diagnostics)

        elif stype == "Switch":
            cases = stmt.get("cases", [])
            for ci, case in enumerate(cases):
                if isinstance(case, dict):
                    case_body = case.get("body")
                    if isinstance(case_body, list):
                        _check_block(case_body, f"{stmt_path}.cases[{ci}].body", defined, diagnostics)
            default = stmt.get("default")
            if isinstance(default, list):
                _check_block(default, f"{stmt_path}.default", defined, diagnostics)

        elif stype == "TryCatch":
            body = stmt.get("body")
            if isinstance(body, list):
                _check_block(body, f"{stmt_path}.body", defined, diagnostics)
            catch_var = stmt.get("catch_var")
            catch_defined = defined | ({catch_var} if isinstance(catch_var, str) else set())
            catch_body = stmt.get("catch_body")
            if isinstance(catch_body, list):
                _check_block(catch_body, f"{stmt_path}.catch_body", catch_defined, diagnostics)
            finally_body = stmt.get("finally_body")
            if isinstance(finally_body, list):
                _check_block(finally_body, f"{stmt_path}.finally_body", defined, diagnostics)

    # --- Rule: unused-variable ---
    # For each Let in this block, check if the variable is referenced
    # anywhere in the remaining statements of this block (including sub-blocks).
    for let_idx, let_name in let_decls:
        remaining_stmts = stmts[let_idx + 1:]
        refs = _collect_var_refs(remaining_stmts)
        if let_name not in refs:
            _add(diagnostics, "unused-variable",
                 f"variable '{let_name}' is declared but never used",
                 f"{path}[{let_idx}]")

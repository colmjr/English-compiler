"""CLI lint subcommand handlers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def lint_command(args: argparse.Namespace) -> int:
    """Handle the lint subcommand."""
    from english_compiler.coreil.lint import lint_coreil

    path = Path(args.file)
    try:
        with path.open("r", encoding="utf-8") as handle:
            doc = json.load(handle)
    except OSError as exc:
        print(f"{path}: {exc}")
        return 1
    except json.JSONDecodeError as exc:
        print(f"{path}: invalid json: {exc}")
        return 1

    diagnostics = lint_coreil(doc)

    if not diagnostics:
        print("No lint issues found.")
        return 0

    for diagnostic in diagnostics:
        severity = diagnostic.get("severity", "warning").upper()
        rule = diagnostic.get("rule", "unknown")
        message = diagnostic.get("message", "")
        lint_path = diagnostic.get("path", "")
        print(f"[{severity}] {lint_path}: {rule} - {message}")

    warning_count = sum(
        1 for diagnostic in diagnostics if diagnostic.get("severity") == "warning"
    )
    error_count = sum(
        1 for diagnostic in diagnostics if diagnostic.get("severity") == "error"
    )
    print(
        f"\n{len(diagnostics)} issue(s): "
        f"{warning_count} warning(s), {error_count} error(s)"
    )

    if args.strict or error_count > 0:
        return 1
    return 0


def run_lint_on_doc(doc: dict, strict: bool = False) -> int:
    """Run lint on a Core IL document and print results."""
    from english_compiler.coreil.lint import lint_coreil

    diagnostics = lint_coreil(doc)
    if not diagnostics:
        print("Lint: no issues found.")
        return 0

    print("\nLint results:")
    for diagnostic in diagnostics:
        severity = diagnostic.get("severity", "warning").upper()
        rule = diagnostic.get("rule", "unknown")
        message = diagnostic.get("message", "")
        lint_path = diagnostic.get("path", "")
        print(f"  [{severity}] {lint_path}: {rule} - {message}")

    warning_count = sum(
        1 for diagnostic in diagnostics if diagnostic.get("severity") == "warning"
    )
    error_count = sum(
        1 for diagnostic in diagnostics if diagnostic.get("severity") == "error"
    )
    print(
        f"  {len(diagnostics)} issue(s): "
        f"{warning_count} warning(s), {error_count} error(s)"
    )

    if strict or error_count > 0:
        return 1
    return 0


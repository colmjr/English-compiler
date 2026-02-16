"""Core IL interactive debugger.

Provides step-through debugging for Core IL programs, similar to pdb for Python.
Uses a callback hook in the interpreter to pause execution and inspect state.

Usage:
    from english_compiler.coreil.debug import debug_coreil
    debug_coreil(doc)  # launches interactive debugger
"""

from __future__ import annotations

from collections import deque
from typing import Any


class _DebugQuitSignal(Exception):
    """Signal to cleanly exit the debugger from inside the callback."""
    pass


def _format_value(value: Any, max_len: int = 80) -> str:
    """Pretty-print a Core IL runtime value with type annotation and truncation."""
    if value is None:
        return "None"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        raw = repr(value)
        if len(raw) > max_len:
            return raw[: max_len - 3] + "..."
        return raw
    if isinstance(value, list):
        inner = ", ".join(_format_value(v, max_len=30) for v in value[:10])
        suffix = f", ... ({len(value)} items)" if len(value) > 10 else ""
        raw = f"[{inner}{suffix}]"
        if len(raw) > max_len:
            return raw[: max_len - 3] + "..."
        return raw
    if isinstance(value, tuple):
        inner = ", ".join(_format_value(v, max_len=30) for v in value[:10])
        suffix = f", ... ({len(value)} items)" if len(value) > 10 else ""
        raw = f"({inner}{suffix})"
        if len(raw) > max_len:
            return raw[: max_len - 3] + "..."
        return raw
    if isinstance(value, set):
        items = sorted(repr(v) for v in list(value)[:10])
        inner = ", ".join(items)
        suffix = f", ... ({len(value)} items)" if len(value) > 10 else ""
        raw = f"{{{inner}{suffix}}}"
        if len(raw) > max_len:
            return raw[: max_len - 3] + "..."
        return raw
    if isinstance(value, deque):
        inner = ", ".join(_format_value(v, max_len=30) for v in list(value)[:10])
        suffix = f", ... ({len(value)} items)" if len(value) > 10 else ""
        raw = f"deque([{inner}{suffix}])"
        if len(raw) > max_len:
            return raw[: max_len - 3] + "..."
        return raw
    if isinstance(value, dict):
        # Check for heap
        if "_heap_items" in value:
            size = len(value["_heap_items"])
            return f"<heap size={size}>"
        # Regular dict/record
        items = []
        for k, v in list(value.items())[:10]:
            items.append(f"{_format_value(k, 20)}: {_format_value(v, 30)}")
        inner = ", ".join(items)
        suffix = f", ... ({len(value)} keys)" if len(value) > 10 else ""
        raw = f"{{{inner}{suffix}}}"
        if len(raw) > max_len:
            return raw[: max_len - 3] + "..."
        return raw
    return repr(value)


def _format_stmt(stmt: dict) -> str:
    """One-line summary of a Core IL statement."""
    stype = stmt.get("type", "?")

    if stype == "Let":
        return f"Let {stmt.get('name')} = ..."
    if stype == "Assign":
        return f"Assign {stmt.get('name')} = ..."
    if stype == "Print":
        argc = len(stmt.get("args", []))
        return f"Print ({argc} arg{'s' if argc != 1 else ''})"
    if stype == "If":
        return "If ..."
    if stype == "While":
        return "While ..."
    if stype == "For":
        return f"For {stmt.get('var')} in ..."
    if stype == "ForEach":
        return f"ForEach {stmt.get('var')} in ..."
    if stype == "FuncDef":
        params = stmt.get("params", [])
        return f"FuncDef {stmt.get('name')}({', '.join(params)})"
    if stype == "Return":
        return "Return ..."
    if stype == "Call":
        return f"Call {stmt.get('name')}(...)"
    if stype == "Push":
        return "Push ..."
    if stype == "Set":
        return "Set [key] = ..."
    if stype == "SetIndex":
        return "SetIndex [i] = ..."
    if stype == "SetField":
        return f"SetField .{stmt.get('name')} = ..."
    if stype == "Break":
        return "Break"
    if stype == "Continue":
        return "Continue"
    if stype == "Throw":
        return "Throw ..."
    if stype == "TryCatch":
        return f"TryCatch (catch_var={stmt.get('catch_var')})"
    return stype


class InteractiveDebugger:
    """Interactive debugger that hooks into the Core IL interpreter."""

    def __init__(self, doc: dict) -> None:
        self.doc = doc
        self.body = doc.get("body", [])
        self.breakpoints: set[int] = set()
        self.mode = "step"  # "step", "continue", "next"
        self.last_command = "s"
        self._next_depth: int | None = None  # for "next" mode

    def callback(
        self,
        stmt: dict,
        body_index: int,
        local_env: dict[str, Any] | None,
        global_env: dict[str, Any],
        functions: dict[str, dict],
        call_depth: int,
    ) -> None:
        """Step callback invoked by the interpreter before each statement."""
        should_stop = False

        if self.mode == "step":
            should_stop = True
        elif self.mode == "next":
            if call_depth <= (self._next_depth or 0):
                should_stop = True
        elif self.mode == "continue":
            if body_index in self.breakpoints:
                should_stop = True

        if not should_stop:
            return

        # Show current position
        depth_prefix = "  " * call_depth
        stmt_summary = _format_stmt(stmt)
        print(f"\n{depth_prefix}[depth={call_depth}] body[{body_index}]: {stmt_summary}")

        # Enter command loop
        self._command_loop(stmt, body_index, local_env, global_env, functions, call_depth)

    def _command_loop(
        self,
        stmt: dict,
        body_index: int,
        local_env: dict[str, Any] | None,
        global_env: dict[str, Any],
        functions: dict[str, dict],
        call_depth: int,
    ) -> None:
        """Read and execute debugger commands until the user resumes execution."""
        while True:
            try:
                raw = input("(debug) ")
            except (EOFError, KeyboardInterrupt):
                print()
                raise _DebugQuitSignal()

            cmd = raw.strip()
            if not cmd:
                cmd = self.last_command

            parts = cmd.split(None, 1)
            verb = parts[0].lower() if parts else ""
            arg = parts[1] if len(parts) > 1 else ""

            if verb in ("s", "step"):
                self.last_command = "s"
                self.mode = "step"
                return

            if verb in ("n", "next"):
                self.last_command = "n"
                self.mode = "next"
                self._next_depth = call_depth
                return

            if verb in ("c", "continue"):
                self.last_command = "c"
                self.mode = "continue"
                return

            if verb in ("v", "vars"):
                self.last_command = "v"
                self._show_vars(local_env, global_env)
                continue

            if verb in ("p", "print"):
                self.last_command = cmd
                self._show_var(arg, local_env, global_env)
                continue

            if verb in ("b", "break"):
                self.last_command = cmd
                self._add_breakpoint(arg)
                continue

            if verb == "rb":
                self.last_command = cmd
                self._remove_breakpoint(arg)
                continue

            if verb in ("bl", "breakpoints"):
                self.last_command = "bl"
                self._list_breakpoints()
                continue

            if verb in ("l", "list"):
                self.last_command = "l"
                self._list_body(body_index)
                continue

            if verb in ("q", "quit"):
                raise _DebugQuitSignal()

            if verb in ("h", "help"):
                self.last_command = "h"
                self._show_help()
                continue

            print(f"Unknown command: {verb!r}. Type 'h' for help.")

    def _show_vars(
        self,
        local_env: dict[str, Any] | None,
        global_env: dict[str, Any],
    ) -> None:
        if global_env:
            print("Global variables:")
            for name, value in global_env.items():
                print(f"  {name} = {_format_value(value)}")
        else:
            print("Global variables: (none)")

        if local_env is not None:
            if local_env:
                print("Local variables:")
                for name, value in local_env.items():
                    print(f"  {name} = {_format_value(value)}")
            else:
                print("Local variables: (none)")

    def _show_var(
        self,
        name: str,
        local_env: dict[str, Any] | None,
        global_env: dict[str, Any],
    ) -> None:
        if not name:
            print("Usage: p <variable_name>")
            return
        if local_env is not None and name in local_env:
            print(f"  {name} = {_format_value(local_env[name])}")
        elif name in global_env:
            print(f"  {name} = {_format_value(global_env[name])}")
        else:
            print(f"  Variable '{name}' not found")

    def _add_breakpoint(self, arg: str) -> None:
        if not arg:
            print("Usage: b <body_index>")
            return
        try:
            idx = int(arg)
        except ValueError:
            print(f"Invalid index: {arg}")
            return
        if idx < 0 or idx >= len(self.body):
            print(f"Index out of range (0..{len(self.body) - 1})")
            return
        self.breakpoints.add(idx)
        print(f"Breakpoint set at body[{idx}]: {_format_stmt(self.body[idx])}")

    def _remove_breakpoint(self, arg: str) -> None:
        if not arg:
            print("Usage: rb <body_index>")
            return
        try:
            idx = int(arg)
        except ValueError:
            print(f"Invalid index: {arg}")
            return
        if idx in self.breakpoints:
            self.breakpoints.discard(idx)
            print(f"Breakpoint removed at body[{idx}]")
        else:
            print(f"No breakpoint at body[{idx}]")

    def _list_breakpoints(self) -> None:
        if not self.breakpoints:
            print("No breakpoints set.")
            return
        print("Breakpoints:")
        for idx in sorted(self.breakpoints):
            label = _format_stmt(self.body[idx]) if idx < len(self.body) else "?"
            print(f"  body[{idx}]: {label}")

    def _list_body(self, current_index: int) -> None:
        if not self.body:
            print("(empty body)")
            return
        for i, stmt in enumerate(self.body):
            marker = ">>>" if i == current_index else "   "
            bp = " *" if i in self.breakpoints else ""
            print(f"  {marker} [{i}] {_format_stmt(stmt)}{bp}")

    def _show_help(self) -> None:
        print("Debugger commands:")
        print("  s, step       Step one statement (enters functions)")
        print("  n, next       Step one statement (steps over functions)")
        print("  c, continue   Run until next breakpoint")
        print("  v, vars       Show all variables")
        print("  p <name>      Print a specific variable")
        print("  b <index>     Set breakpoint at body index")
        print("  rb <index>    Remove breakpoint")
        print("  bl            List all breakpoints")
        print("  l, list       List body statements")
        print("  q, quit       Exit debugger")
        print("  h, help       Show this help")
        print("  (empty)       Repeat last command")


def debug_coreil(doc: dict) -> int:
    """Launch the interactive debugger for a Core IL document.

    Args:
        doc: A validated Core IL document.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    from .interp import run_coreil
    from .validate import validate_coreil

    errors = validate_coreil(doc)
    if errors:
        for error in errors:
            print(f"{error['path']}: {error['message']}")
        return 1

    body = doc.get("body", [])
    print(f"Core IL Debugger - {len(body)} top-level statement(s)")
    print("Type 'h' for help, 's' to step, 'c' to continue, 'q' to quit.")

    debugger = InteractiveDebugger(doc)

    try:
        rc = run_coreil(doc, step_callback=debugger.callback)
    except _DebugQuitSignal:
        print("\nDebugger exited.")
        return 0

    print("\nProgram finished.")
    return rc

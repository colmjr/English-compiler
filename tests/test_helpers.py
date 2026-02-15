"""Shared test utilities for Core IL testing.

This module provides reusable test infrastructure to avoid code duplication
across test files, including:
- Backend execution helpers
- Backend parity verification
- Invalid helper call detection
"""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path

from english_compiler.coreil.emit import emit_python
from english_compiler.coreil.emit_javascript import emit_javascript
from english_compiler.coreil.emit_cpp import emit_cpp, get_runtime_header_path, get_json_header_path
from english_compiler.coreil.interp import run_coreil


# Check for available backends
NODE_AVAILABLE = shutil.which("node") is not None

CPP_COMPILER: str | None = None
for _cc in ["g++", "clang++"]:
    if shutil.which(_cc):
        CPP_COMPILER = _cc
        break
CPP_AVAILABLE = CPP_COMPILER is not None

RUST_AVAILABLE = shutil.which("rustc") is not None
GO_AVAILABLE = shutil.which("go") is not None

# WASM backend availability (requires asc compiler)
ASC_AVAILABLE = shutil.which("asc") is not None
WASM_AVAILABLE = ASC_AVAILABLE and NODE_AVAILABLE

# Helper function names that should not be used in Core IL v0.5+
INVALID_HELPER_CALLS = {"get_or_default", "append", "keys", "entries"}


class TestFailure(Exception):
    """Raised when a test fails."""


@dataclass
class BackendResult:
    """Result from running a backend."""
    output: str
    exit_code: int
    success: bool
    error: str | None = None


def run_interpreter(doc: dict) -> BackendResult:
    """Run Core IL document in the interpreter.

    Args:
        doc: The Core IL document to execute.

    Returns:
        BackendResult with output, exit code, and success status.
    """
    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer):
            exit_code = run_coreil(doc)
        return BackendResult(
            output=buffer.getvalue(),
            exit_code=exit_code,
            success=exit_code == 0,
        )
    except Exception as exc:
        return BackendResult(
            output=buffer.getvalue(),
            exit_code=1,
            success=False,
            error=str(exc),
        )


def run_python_backend(doc: dict, timeout: int = 10) -> BackendResult:
    """Generate Python code and execute it.

    Args:
        doc: The Core IL document to transpile and run.
        timeout: Maximum execution time in seconds.

    Returns:
        BackendResult with output, exit code, and success status.
    """
    try:
        python_code = emit_python(doc)
    except Exception as exc:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"Python codegen failed: {exc}",
        )

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(python_code)
            tmp_path = tmp.name

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        Path(tmp_path).unlink()

        return BackendResult(
            output=result.stdout,
            exit_code=result.returncode,
            success=result.returncode == 0,
            error=result.stderr if result.returncode != 0 else None,
        )

    except subprocess.TimeoutExpired:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"Python execution timeout (>{timeout}s)",
        )
    except Exception as exc:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"Python execution error: {exc}",
        )


def run_javascript_backend(doc: dict, timeout: int = 10) -> BackendResult:
    """Generate JavaScript code and execute it with Node.js.

    Args:
        doc: The Core IL document to transpile and run.
        timeout: Maximum execution time in seconds.

    Returns:
        BackendResult with output, exit code, and success status.
        Returns failure if Node.js is not available.
    """
    if not NODE_AVAILABLE:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error="Node.js not available",
        )

    try:
        js_code = emit_javascript(doc)
    except Exception as exc:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"JavaScript codegen failed: {exc}",
        )

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(js_code)
            tmp_path = tmp.name

        result = subprocess.run(
            ["node", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        Path(tmp_path).unlink()

        return BackendResult(
            output=result.stdout,
            exit_code=result.returncode,
            success=result.returncode == 0,
            error=result.stderr if result.returncode != 0 else None,
        )

    except subprocess.TimeoutExpired:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"JavaScript execution timeout (>{timeout}s)",
        )
    except Exception as exc:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"JavaScript execution error: {exc}",
        )


def run_cpp_backend(doc: dict, timeout: int = 10) -> BackendResult:
    """Generate C++ code, compile, and execute it.

    Args:
        doc: The Core IL document to transpile and run.
        timeout: Maximum execution time in seconds.

    Returns:
        BackendResult with output, exit code, and success status.
        Returns failure if no C++ compiler is available.
    """
    if not CPP_AVAILABLE:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error="C++ compiler not available",
        )

    try:
        cpp_code = emit_cpp(doc)
    except Exception as exc:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"C++ codegen failed: {exc}",
        )

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            cpp_path = tmp_dir_path / "test.cpp"
            exe_path = tmp_dir_path / "test"

            cpp_path.write_text(cpp_code, encoding="utf-8")

            # Copy runtime headers
            shutil.copy(get_runtime_header_path(), tmp_dir_path / "coreil_runtime.hpp")
            shutil.copy(get_json_header_path(), tmp_dir_path / "json.hpp")

            # Compile
            compile_result = subprocess.run(
                [CPP_COMPILER, "-std=c++17", "-O2", str(cpp_path), "-o", str(exe_path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=tmp_dir,
            )

            if compile_result.returncode != 0:
                return BackendResult(
                    output="",
                    exit_code=1,
                    success=False,
                    error=f"C++ compilation failed:\n{compile_result.stderr}",
                )

            # Execute
            result = subprocess.run(
                [str(exe_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return BackendResult(
                output=result.stdout,
                exit_code=result.returncode,
                success=result.returncode == 0,
                error=result.stderr if result.returncode != 0 else None,
            )

    except subprocess.TimeoutExpired:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"C++ execution timeout (>{timeout}s)",
        )
    except Exception as exc:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"C++ execution error: {exc}",
        )


def run_rust_backend(doc: dict, timeout: int = 10) -> BackendResult:
    """Generate Rust code, compile, and execute it.

    Args:
        doc: The Core IL document to transpile and run.
        timeout: Maximum execution time in seconds.

    Returns:
        BackendResult with output, exit code, and success status.
        Returns failure if rustc is not available.
    """
    if not RUST_AVAILABLE:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error="Rust compiler not available",
        )

    from english_compiler.coreil.emit_rust import emit_rust, get_runtime_path

    try:
        rust_code = emit_rust(doc)
    except Exception as exc:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"Rust codegen failed: {exc}",
        )

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            rs_path = tmp_dir_path / "test.rs"
            exe_path = tmp_dir_path / "test"

            rs_path.write_text(rust_code, encoding="utf-8")

            # Copy runtime
            import shutil as shutil2
            shutil2.copy(get_runtime_path(), tmp_dir_path / "coreil_runtime.rs")

            # Compile
            compile_result = subprocess.run(
                ["rustc", str(rs_path), "-o", str(exe_path), "--edition", "2021"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=tmp_dir,
            )

            if compile_result.returncode != 0:
                return BackendResult(
                    output="",
                    exit_code=1,
                    success=False,
                    error=f"Rust compilation failed:\n{compile_result.stderr}",
                )

            # Execute
            result = subprocess.run(
                [str(exe_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return BackendResult(
                output=result.stdout,
                exit_code=result.returncode,
                success=result.returncode == 0,
                error=result.stderr if result.returncode != 0 else None,
            )

    except subprocess.TimeoutExpired:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"Rust execution timeout (>{timeout}s)",
        )
    except Exception as exc:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"Rust execution error: {exc}",
        )


def run_go_backend(doc: dict, timeout: int = 10) -> BackendResult:
    """Generate Go code, compile, and execute it.

    Args:
        doc: The Core IL document to transpile and run.
        timeout: Maximum execution time in seconds.

    Returns:
        BackendResult with output, exit code, and success status.
        Returns failure if Go is not available.
    """
    if not GO_AVAILABLE:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error="Go compiler not available",
        )

    from english_compiler.coreil.emit_go import emit_go, get_runtime_path

    try:
        go_code = emit_go(doc)
    except Exception as exc:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"Go codegen failed: {exc}",
        )

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            go_path = tmp_dir_path / "main.go"
            runtime_path = tmp_dir_path / "coreil_runtime.go"

            go_path.write_text(go_code, encoding="utf-8")

            # Copy runtime
            shutil.copy(get_runtime_path(), runtime_path)

            # Compile and run
            result = subprocess.run(
                ["go", "run", str(go_path), str(runtime_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmp_dir,
            )

            return BackendResult(
                output=result.stdout,
                exit_code=result.returncode,
                success=result.returncode == 0,
                error=result.stderr if result.returncode != 0 else None,
            )

    except subprocess.TimeoutExpired:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"Go execution timeout (>{timeout}s)",
        )
    except Exception as exc:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"Go execution error: {exc}",
        )


def run_wasm_backend(doc: dict, timeout: int = 30) -> BackendResult:
    """Generate AssemblyScript code, compile to WASM, and execute with Node.js.

    Args:
        doc: The Core IL document to transpile and run.
        timeout: Maximum execution time in seconds.

    Returns:
        BackendResult with output, exit code, and success status.
        Returns failure if asc compiler or Node.js is not available.
    """
    if not WASM_AVAILABLE:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error="WASM backend not available (requires asc and node)",
        )

    from english_compiler.coreil.emit_assemblyscript import emit_assemblyscript
    from english_compiler.coreil.wasm_build import compile_to_wasm, run_wasm

    try:
        as_code = emit_assemblyscript(doc)
    except Exception as exc:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"AssemblyScript codegen failed: {exc}",
        )

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)

            # Compile to WASM
            result = compile_to_wasm(
                as_code,
                tmp_dir_path,
                "test",
                emit_wat=False,
                optimize=False,  # Faster for tests
            )

            if not result.success:
                return BackendResult(
                    output="",
                    exit_code=1,
                    success=False,
                    error=f"WASM compilation failed: {result.error}",
                )

            # Run WASM with Node.js using proper I/O bindings
            stdout_output, exit_code = run_wasm(result.wasm_path, timeout=timeout)

            return BackendResult(
                output=stdout_output,
                exit_code=exit_code,
                success=exit_code == 0,
                error=None if exit_code == 0 else stdout_output,
            )

    except subprocess.TimeoutExpired:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"WASM execution timeout (>{timeout}s)",
        )
    except Exception as exc:
        return BackendResult(
            output="",
            exit_code=1,
            success=False,
            error=f"WASM execution error: {exc}",
        )


def check_invalid_calls(doc: dict, test_name: str | None = None) -> list[str]:
    """Check for invalid helper function calls in a Core IL document.

    Args:
        doc: The Core IL document to check.
        test_name: Optional test name for error messages.

    Returns:
        List of invalid helper function names found.
    """
    found: list[str] = []

    def _check_node(node: dict | list | str | int | float | bool | None) -> None:
        if isinstance(node, dict):
            if node.get("type") == "Call":
                name = node.get("name", "")
                if name in INVALID_HELPER_CALLS:
                    found.append(name)
            for value in node.values():
                _check_node(value)
        elif isinstance(node, list):
            for item in node:
                _check_node(item)

    _check_node(doc)
    return found


def verify_backend_parity(
    doc: dict,
    test_name: str,
    include_javascript: bool = True,
    include_cpp: bool = True,
    include_rust: bool = True,
    include_go: bool = True,
    include_wasm: bool = False,
) -> None:
    """Verify that all backends produce identical output.

    Args:
        doc: The Core IL document to test.
        test_name: Name of the test for error messages.
        include_javascript: Whether to test JavaScript backend.
        include_cpp: Whether to test C++ backend.
        include_rust: Whether to test Rust backend.
        include_go: Whether to test Go backend.
        include_wasm: Whether to test WASM backend (disabled by default).

    Raises:
        TestFailure: If any backend fails or outputs don't match.
    """
    # Run interpreter
    interp_result = run_interpreter(doc)
    if not interp_result.success:
        error_msg = interp_result.error or "unknown error"
        raise TestFailure(f"{test_name}: Interpreter failed: {error_msg}")

    # Run Python backend
    python_result = run_python_backend(doc)
    if not python_result.success:
        error_msg = python_result.error or "unknown error"
        raise TestFailure(f"{test_name}: Python backend failed: {error_msg}")

    if interp_result.output != python_result.output:
        raise TestFailure(
            f"{test_name}: Output mismatch (Python)!\n"
            f"Interpreter output:\n{interp_result.output}\n"
            f"Python output:\n{python_result.output}"
        )

    # Run JavaScript backend
    if include_javascript and NODE_AVAILABLE:
        js_result = run_javascript_backend(doc)
        if not js_result.success:
            error_msg = js_result.error or "unknown error"
            raise TestFailure(f"{test_name}: JavaScript backend failed: {error_msg}")

        if interp_result.output != js_result.output:
            raise TestFailure(
                f"{test_name}: Output mismatch (JavaScript)!\n"
                f"Interpreter output:\n{interp_result.output}\n"
                f"JavaScript output:\n{js_result.output}"
            )

    # Run C++ backend
    if include_cpp and CPP_AVAILABLE:
        cpp_result = run_cpp_backend(doc)
        if not cpp_result.success:
            error_msg = cpp_result.error or "unknown error"
            raise TestFailure(f"{test_name}: C++ backend failed: {error_msg}")

        if interp_result.output != cpp_result.output:
            raise TestFailure(
                f"{test_name}: Output mismatch (C++)!\n"
                f"Interpreter output:\n{interp_result.output}\n"
                f"C++ output:\n{cpp_result.output}"
            )

    # Run Rust backend
    if include_rust and RUST_AVAILABLE:
        rust_result = run_rust_backend(doc)
        if not rust_result.success:
            error_msg = rust_result.error or "unknown error"
            raise TestFailure(f"{test_name}: Rust backend failed: {error_msg}")

        if interp_result.output != rust_result.output:
            raise TestFailure(
                f"{test_name}: Output mismatch (Rust)!\n"
                f"Interpreter output:\n{interp_result.output}\n"
                f"Rust output:\n{rust_result.output}"
            )

    # Run Go backend
    if include_go and GO_AVAILABLE:
        go_result = run_go_backend(doc)
        if not go_result.success:
            error_msg = go_result.error or "unknown error"
            raise TestFailure(f"{test_name}: Go backend failed: {error_msg}")

        if interp_result.output != go_result.output:
            raise TestFailure(
                f"{test_name}: Output mismatch (Go)!\n"
                f"Interpreter output:\n{interp_result.output}\n"
                f"Go output:\n{go_result.output}"
            )

    # Run WASM backend (disabled by default)
    if include_wasm and WASM_AVAILABLE:
        wasm_result = run_wasm_backend(doc)
        if not wasm_result.success:
            error_msg = wasm_result.error or "unknown error"
            raise TestFailure(f"{test_name}: WASM backend failed: {error_msg}")

        if interp_result.output != wasm_result.output:
            raise TestFailure(
                f"{test_name}: Output mismatch (WASM)!\n"
                f"Interpreter output:\n{interp_result.output}\n"
                f"WASM output:\n{wasm_result.output}"
            )

"""Algorithm corpus regression test suite.

This test runner enforces:
1. Core IL validation passes
2. Interpreter executes without errors
3. Python backend executes without errors
4. JavaScript backend executes without errors (if Node.js available)
5. Interpreter output == Python output == JavaScript output (backend parity)
6. No invalid helper calls (e.g., "get_or_default", "append")
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from english_compiler.coreil.emit import emit_python
from english_compiler.coreil.emit_javascript import emit_javascript
from english_compiler.coreil.interp import run_coreil
from english_compiler.coreil.validate import validate_coreil
from english_compiler.frontend.mock_llm import generate_coreil_from_text


# Check if Node.js is available
_NODE_AVAILABLE = shutil.which("node") is not None


class TestFailure(Exception):
    """Raised when a test fails."""


def _check_invalid_calls(doc: dict, algo_name: str) -> None:
    """Check for invalid helper function calls that should not exist in v1.0."""
    invalid_calls = {"get_or_default", "append", "keys", "entries"}

    def _check_node(node: dict | list | str | int | float | bool | None) -> None:
        if isinstance(node, dict):
            if node.get("type") == "Call":
                name = node.get("name", "")
                if name in invalid_calls:
                    raise TestFailure(
                        f"{algo_name}: Invalid helper call '{name}' found. "
                        f"Use explicit primitives instead (GetDefault, Keys, Push)."
                    )
            for value in node.values():
                _check_node(value)
        elif isinstance(node, list):
            for item in node:
                _check_node(item)

    _check_node(doc)


def _run_algorithm_test(txt_path: Path) -> None:
    """Run a single algorithm test with full parity checks."""
    algo_name = txt_path.stem
    print(f"Testing {algo_name}...", end=" ", flush=True)

    # Read source text
    try:
        source_text = txt_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TestFailure(f"{algo_name}: Failed to read source: {exc}")

    # Generate Core IL
    try:
        doc = generate_coreil_from_text(source_text)
    except Exception as exc:
        raise TestFailure(f"{algo_name}: Frontend generation failed: {exc}")

    # Validate Core IL
    errors = validate_coreil(doc)
    if errors:
        error_msgs = [f"{e['path']}: {e['message']}" for e in errors]
        raise TestFailure(
            f"{algo_name}: Validation failed:\n" + "\n".join(error_msgs)
        )

    # Check for invalid helper calls
    _check_invalid_calls(doc, algo_name)

    # Run interpreter and capture output
    interpreter_buffer = io.StringIO()
    try:
        with redirect_stdout(interpreter_buffer):
            exit_code = run_coreil(doc)
        if exit_code != 0:
            raise TestFailure(
                f"{algo_name}: Interpreter failed with exit code {exit_code}"
            )
        interpreter_output = interpreter_buffer.getvalue()
    except Exception as exc:
        raise TestFailure(f"{algo_name}: Interpreter error: {exc}")

    # Generate Python code
    try:
        python_code = emit_python(doc)
    except Exception as exc:
        raise TestFailure(f"{algo_name}: Python codegen failed: {exc}")

    # Execute Python code in subprocess
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
            timeout=10,
        )

        # Clean up temp file
        Path(tmp_path).unlink()

        if result.returncode != 0:
            raise TestFailure(
                f"{algo_name}: Python execution failed with exit code {result.returncode}\n"
                f"stderr: {result.stderr}"
            )

        python_output = result.stdout

    except subprocess.TimeoutExpired:
        raise TestFailure(f"{algo_name}: Python execution timeout (>10s)")
    except Exception as exc:
        raise TestFailure(f"{algo_name}: Python execution error: {exc}")

    # Compare outputs (backend parity check)
    if interpreter_output != python_output:
        raise TestFailure(
            f"{algo_name}: Output mismatch (Python)!\n"
            f"Interpreter output:\n{interpreter_output}\n"
            f"Python output:\n{python_output}"
        )

    # Test JavaScript backend if Node.js is available
    if _NODE_AVAILABLE:
        # Generate JavaScript code
        try:
            js_code = emit_javascript(doc)
        except Exception as exc:
            raise TestFailure(f"{algo_name}: JavaScript codegen failed: {exc}")

        # Execute JavaScript code in subprocess
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
                timeout=10,
            )

            # Clean up temp file
            Path(tmp_path).unlink()

            if result.returncode != 0:
                raise TestFailure(
                    f"{algo_name}: JavaScript execution failed with exit code {result.returncode}\n"
                    f"stderr: {result.stderr}"
                )

            js_output = result.stdout

        except subprocess.TimeoutExpired:
            raise TestFailure(f"{algo_name}: JavaScript execution timeout (>10s)")
        except Exception as exc:
            raise TestFailure(f"{algo_name}: JavaScript execution error: {exc}")

        # Compare JavaScript output with interpreter output
        if interpreter_output != js_output:
            raise TestFailure(
                f"{algo_name}: Output mismatch (JavaScript)!\n"
                f"Interpreter output:\n{interpreter_output}\n"
                f"JavaScript output:\n{js_output}"
            )

    print("✓")


def main() -> int:
    """Run all algorithm regression tests."""
    root = Path(__file__).resolve().parents[1]
    algorithms_dir = root / "tests" / "algorithms"

    if not algorithms_dir.exists():
        print(f"Error: {algorithms_dir} does not exist")
        return 1

    # Find all .txt files in algorithms directory
    txt_files = sorted(algorithms_dir.glob("*.txt"))

    if not txt_files:
        print(f"Warning: No algorithm tests found in {algorithms_dir}")
        return 0

    print(f"Running {len(txt_files)} algorithm regression tests...\n")

    failures = []
    for txt_path in txt_files:
        try:
            _run_algorithm_test(txt_path)
        except TestFailure as exc:
            failures.append(str(exc))
            print("✗")

    print()

    if failures:
        print("=" * 70)
        print("FAILURES:")
        print("=" * 70)
        for i, failure in enumerate(failures, start=1):
            print(f"\n{i}. {failure}")
        print()
        print(f"{len(failures)}/{len(txt_files)} tests failed")
        return 1

    print(f"All {len(txt_files)} algorithm regression tests passed! ✓")
    print()
    print("Verified:")
    print("  • Core IL validation passes")
    print("  • Interpreter executes successfully")
    print("  • Python backend executes successfully")
    if _NODE_AVAILABLE:
        print("  • JavaScript backend executes successfully")
        print("  • Backend parity (interpreter output == Python output == JavaScript output)")
    else:
        print("  • Backend parity (interpreter output == Python output)")
        print("  • (JavaScript tests skipped - Node.js not available)")
    print("  • No invalid helper calls")
    return 0


if __name__ == "__main__":
    sys.exit(main())

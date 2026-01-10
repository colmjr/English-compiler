"""Parity tests: Compare interpreter output with generated Python output."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

from english_compiler.coreil.emit import emit_python
from english_compiler.coreil.interp import run_coreil


def run_parity_test(coreil_path: Path) -> tuple[bool, str]:
    """Run parity test for a single Core IL file.

    Returns:
        (passed, message) tuple
    """
    # Load Core IL document
    try:
        doc = json.loads(coreil_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"Failed to load Core IL: {exc}"

    # Run interpreter and capture output
    buffer_interp = io.StringIO()
    try:
        with redirect_stdout(buffer_interp):
            exit_code_interp = run_coreil(doc)
    except Exception as exc:
        return False, f"Interpreter failed: {exc}"

    interp_output = buffer_interp.getvalue()

    # Generate Python code
    try:
        python_code = emit_python(doc)
    except Exception as exc:
        return False, f"Codegen failed: {exc}"

    # Run generated Python and capture output
    try:
        result = subprocess.run(
            [sys.executable, "-c", python_code],
            capture_output=True,
            text=True,
            timeout=5,
        )
        python_output = result.stdout
        exit_code_python = result.returncode
    except subprocess.TimeoutExpired:
        return False, "Python execution timed out"
    except Exception as exc:
        return False, f"Python execution failed: {exc}"

    # Compare outputs
    if interp_output != python_output:
        return (
            False,
            f"Output mismatch:\n"
            f"  Interpreter: {interp_output!r}\n"
            f"  Python:      {python_output!r}",
        )

    if exit_code_interp != exit_code_python:
        return (
            False,
            f"Exit code mismatch:\n"
            f"  Interpreter: {exit_code_interp}\n"
            f"  Python:      {exit_code_python}",
        )

    return True, "OK"


def main() -> None:
    """Run parity tests on all examples."""
    root = Path(__file__).resolve().parents[1]
    examples_dir = root / "examples"

    # Find all .coreil.json files
    coreil_files = sorted(examples_dir.glob("*.coreil.json"))

    if not coreil_files:
        print("No Core IL files found in examples/")
        return

    print(f"Running parity tests on {len(coreil_files)} examples...\n")

    passed = 0
    failed = 0
    failures: list[tuple[Path, str]] = []

    for coreil_path in coreil_files:
        test_name = coreil_path.stem
        success, message = run_parity_test(coreil_path)

        if success:
            print(f"✓ {test_name}")
            passed += 1
        else:
            print(f"✗ {test_name}: {message.split(chr(10))[0]}")
            failed += 1
            failures.append((coreil_path, message))

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"Parity Tests: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")

    # Print detailed failure messages
    if failures:
        print("\nFailure Details:")
        for coreil_path, message in failures:
            print(f"\n{coreil_path.name}:")
            print(f"  {message}")

    # Exit with non-zero code if any tests failed
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

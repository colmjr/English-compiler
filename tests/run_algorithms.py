"""Algorithm corpus regression test suite.

This test runner enforces:
1. Core IL validation passes
2. Interpreter executes without errors
3. Python backend executes without errors
4. JavaScript backend executes without errors (if Node.js available)
5. C++ backend executes without errors (if g++/clang++ available)
6. Interpreter output == Python output == JavaScript output == C++ output (backend parity)
7. No invalid helper calls (e.g., "get_or_default", "append")
"""

from __future__ import annotations

import sys
from pathlib import Path

from english_compiler.coreil.validate import validate_coreil
from english_compiler.frontend.mock_llm import generate_coreil_from_text

from tests.test_helpers import (
    NODE_AVAILABLE,
    CPP_AVAILABLE,
    CPP_COMPILER,
    TestFailure,
    check_invalid_calls,
    verify_backend_parity,
)


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
    invalid_calls = check_invalid_calls(doc)
    if invalid_calls:
        raise TestFailure(
            f"{algo_name}: Invalid helper calls found: {invalid_calls}. "
            f"Use explicit primitives instead (GetDefault, Keys, Push)."
        )

    # Verify backend parity (runs all backends and compares outputs)
    verify_backend_parity(doc, algo_name)

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
    if NODE_AVAILABLE:
        print("  • JavaScript backend executes successfully")
    else:
        print("  • (JavaScript tests skipped - Node.js not available)")
    if CPP_AVAILABLE:
        print(f"  • C++ backend executes successfully ({CPP_COMPILER})")
    else:
        print("  • (C++ tests skipped - no g++/clang++ available)")
    backends = ["interpreter", "Python"]
    if NODE_AVAILABLE:
        backends.append("JavaScript")
    if CPP_AVAILABLE:
        backends.append("C++")
    print(f"  • Backend parity ({' == '.join(backends)} output)")
    print("  • No invalid helper calls")
    return 0


if __name__ == "__main__":
    sys.exit(main())

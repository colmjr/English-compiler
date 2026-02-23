---
name: add-test
description: Scaffold and add a new test case for the english-compiler. Determines the right test file, writes the Core IL fixture, adds assertions, and verifies it passes.
argument-hint: "[description of what to test]"
---

# Add Test

You are adding a test for: **$ARGUMENTS**

## Phase 1: Determine Test Location

Based on the description, decide which test file this belongs in:

| Category | File | When to use |
|----------|------|-------------|
| Core IL primitives / interpreter | `tests/run.py` | Testing a specific node type or interpreter behavior |
| Algorithm / backend parity | `tests/algorithms/*.txt` + `tests/run_algorithms.py` | Full pipeline test with interpreter == Python output |
| Short-circuit evaluation | `tests/test_short_circuit.py` | Logical operator short-circuiting |
| Lowering pass | `tests/test_lower.py` | For/ForEach to While transformation |
| Break/Continue | `tests/test_break_continue.py` | Loop control flow with Break/Continue |
| Try/Catch | `tests/test_try_catch.py` | Exception handling (Throw/TryCatch) |
| Switch statement | `tests/test_switch.py` | Switch-Case pattern matching |
| Type conversion | `tests/test_type_convert.py` | ToInt, ToFloat, ToString |
| Slicing | `tests/test_slice.py` | Slice expression behavior |
| String operations | `tests/test_string_ops.py` | StringSplit, StringTrim, etc. |
| Map/dictionary ops | `tests/test_map.py` | Map operations |
| Record ops | `tests/test_record.py` | Record field access |
| Set ops | `tests/test_set_ops.py` | Set data structure operations |
| Deque ops | `tests/test_deque.py` | Deque operations |
| Import / multi-file modules | `tests/test_import.py` | Import resolution, module flattening |
| JavaScript backend | `tests/test_javascript.py` | JS-specific codegen |
| Rust backend | `tests/test_rust.py` | Rust-specific codegen |
| Go backend | `tests/test_go.py` | Go-specific codegen |
| WASM backend | `tests/test_wasm_host_print.py` | WASM/AssemblyScript host string decoding |
| Static analysis | `tests/test_lint.py` | Linter rules |
| Optimizer | `tests/test_optimize.py` | Constant folding, DCE, etc. |
| Source maps | `tests/test_source_map.py` | English→CoreIL→target mappings |
| Debugger | `tests/test_debug.py` | Step-through debugger |
| Explain (reverse compile) | `tests/test_explain.py` | Core IL → English |
| Explain errors (LLM) | `tests/test_explain_errors.py` | LLM error explanations |
| Fuzz testing | `tests/test_fuzz.py` | Property-based fuzzing for backend parity |
| LLM retry logic | `tests/test_retry.py` | LLM error recovery retry logic |
| Helper utilities | `tests/test_helpers.py` | Helper utility functions |
| CLI helpers | `tests/test_cli_helpers.py` | CLI command helper modules |
| Regression suite meta | `tests/test_regression_suite.py` | Meta-tests for regression suite |
| Settings/config | `tests/test_settings.py` | Configuration system |
| Backend parity | `tests/run_parity.py` | Backend parity checks across all backends |
| New specialized area | `tests/test_<name>.py` | Only if none of the above fit |

Read the target test file to understand the existing patterns and conventions.

## Phase 2: Write the Test

Follow the conventions of the target file exactly. Typical patterns:

**For `tests/run.py`** (Core IL primitives):
- Create a Core IL JSON program inline or as a fixture file in `examples/`
- Use `_run_example(path, "expected output\n")` pattern
- Expected output must include trailing newline if the program uses Print

**For algorithm tests** (`tests/algorithms/*.txt`):
- Write natural English pseudocode in a new `.txt` file
- The test runner auto-discovers `.txt` files
- The test compiles via mock frontend, runs interpreter AND Python backend, and compares output

**For specialized test files**:
- Follow the existing assertion style in that file
- Build Core IL programs programmatically using dicts
- Use the interpreter directly: `from english_compiler.coreil.interp import interpret`

Key rules:
- Test ONE thing per test case — keep it focused
- Include edge cases if the behavior has boundaries (empty lists, zero, negative indices, etc.)
- Expected output must be exact (whitespace, newlines, formatting all matter)
- Use `validate_coreil()` before `interpret()` if testing validation

## Phase 3: Verify

Run the specific test file to confirm the new test passes:

```bash
python -m tests.<test_module>
```

Then run the full suite to confirm nothing else broke:

```bash
python -m tests.run
python -m tests.run_algorithms
```

Show the test output. If the new test fails, fix it — do not leave a failing test behind.

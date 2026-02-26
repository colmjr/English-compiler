---
name: implement-feature
description: Investigate, implement, and verify bug fixes or new features across all compiler backends (interpreter, Python, JavaScript, C++, Rust, Go, WASM)
---

# Implement Feature / Fix Bug

You are fixing or implementing: **$ARGUMENTS**

## Phase 1: Parallel Investigation

Use the Task tool to run these agents **in parallel**:

**Agent 1 — Interpreter & Python backend**:
Read the relevant source in `english_compiler/coreil/interp.py` and `english_compiler/coreil/emit.py`. Identify how the affected feature is currently implemented. Report what code paths are involved and any potential issues.

**Agent 2 — JavaScript backend**:
Read the relevant source in `english_compiler/coreil/emit_javascript.py`. Identify how the affected feature is implemented. Report what code paths are involved.

**Agent 3 — C++, Rust, Go, and WASM backends**:
Read the relevant source in `english_compiler/coreil/emit_cpp.py`, `english_compiler/coreil/emit_rust.py`, `english_compiler/coreil/emit_go.py`, and `english_compiler/coreil/emit_assemblyscript.py`. Identify how the affected feature is implemented. Report what code paths are involved.

**Agent 4 — Run full test suite**:
Run `python -m tests.run && python -m tests.run_algorithms && python -m tests.run_parity`. Capture which tests pass and which fail. Report a summary.

## Phase 2: Implement the Fix/Feature (Sequential, Interpreter-First)

Based on Phase 1 findings, implement changes **sequentially** in this order:

1. **Shared files first** (if needed): Edit `validate.py`, `lower.py`, `emit_utils.py`, `emit_base.py`, `constants.py`, `node_nav.py`, or any shared modules before touching backends.

2. **Interpreter** (`interp.py`): Implement the fix/feature here first. The interpreter is the reference implementation and must be correct before proceeding.

3. **Python backend** (`emit.py`): Implement the fix to match the interpreter's behavior exactly. The interpreter is the reference — match its output.

4. **JavaScript backend** (`emit_javascript.py`): Implement the fix to match the interpreter's behavior.

5. **C++ backend** (`emit_cpp.py`): Implement the fix to match the interpreter's behavior.

6. **Rust backend** (`emit_rust.py`): Implement the fix to match the interpreter's behavior.

7. **Go backend** (`emit_go.py`): Implement the fix to match the interpreter's behavior.

8. **WASM backend** (`emit_assemblyscript.py`): Implement the fix to match the interpreter's behavior.

If a backend doesn't have the affected feature, skip it. Each backend must stay consistent with the interpreter's behavior.

## Phase 3: Parallel Verification

Use the Task tool to run these **in parallel**:

**Agent A — Core tests**: Run `python -m tests.run`
**Agent B — Algorithm regression and parity**: Run `python -m tests.run_algorithms && python -m tests.run_parity`
**Agent C — All specialized tests**: Run all `python -m tests.test_*` modules. At minimum run: `test_short_circuit`, `test_lower`, `test_break_continue`, `test_try_catch`, `test_switch`, `test_type_convert`, `test_slice`, `test_string_ops`, `test_map`, `test_record`, `test_set_ops`, `test_deque`, `test_lint`, `test_optimize`, `test_javascript`, `test_rust`, `test_go`, `test_source_map`, `test_debug`, `test_explain`, `test_explain_errors`, `test_wasm_host_print`, `test_import`, `test_fuzz`, `test_helpers`, `test_cli_helpers`, `test_retry`, `test_regression_suite`.

If ANY test fails, iterate on the fix for that specific backend without regressing others. Re-run failing tests until all pass.

**Key constraint**: Do NOT mark this done until every backend passes. Show the final test output.

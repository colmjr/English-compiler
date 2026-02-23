---
name: refactor-clean
description: Refactor and clean up code in the english-compiler codebase. Removes dead code, improves structure, and ensures consistency across backends without changing behavior.
argument-hint: "[file, module, or area to refactor]"
---

# Refactor & Clean

You are refactoring: **$ARGUMENTS**

## Ground Rules

- **No behavior changes**: All existing tests must continue to pass with identical output. This is a refactor, not a feature change.
- **No new files**: Prefer editing existing files. Do not create utility modules or abstractions unless explicitly requested.
- **No over-engineering**: Keep changes minimal and focused. Three similar lines are better than a premature abstraction.
- **Backend parity**: If you touch one backend, verify the others remain consistent.

## Phase 1: Audit

Use the Task tool to run these **in parallel**:

**Agent 1 — Code analysis**:
Read the target file(s) specified in `$ARGUMENTS`. Identify:
- Dead code (unreachable branches, unused imports, unused variables/functions)
- Duplicated logic that could be consolidated
- Inconsistent naming or style
- Overly complex conditionals or nesting
- Missing or misleading comments (but do NOT add comments to code that is self-explanatory)

Report findings as a prioritized list.

**Agent 2 — Baseline test run**:
Run the full test suite to establish a baseline:
```
python -m tests.run && python -m tests.run_algorithms
```
Capture all output. Every test must pass before any refactoring begins.

## Phase 2: Refactor

Apply changes **one logical unit at a time**. For each change:

1. Make the edit
2. Verify the change is purely structural (no semantic difference)
3. Continue to the next change

Prioritize these categories (in order):
1. **Remove dead code**: Unused imports, unreachable branches, commented-out code
2. **Simplify logic**: Flatten nested conditionals, reduce redundancy
3. **Improve consistency**: Align naming conventions, parameter ordering, string formatting style
4. **Consolidate duplication**: Only if the duplication is within the same file and the abstraction is obvious

Do NOT:
- Rename public APIs or Core IL node type strings
- Change error message text (tests may depend on exact wording)
- Add type annotations, docstrings, or comments to code you didn't otherwise change
- Refactor test files unless they were explicitly included in the target

## Phase 3: Verify

Use the Task tool to run these **in parallel**:

**Agent A — Core tests**: Run `python -m tests.run`
**Agent B — Algorithm regression and parity**: Run `python -m tests.run_algorithms && python -m tests.run_parity`
**Agent C — All specialized tests**: Run all `python -m tests.test_*` modules that are relevant to the refactored code. When in doubt, run them all: `test_short_circuit`, `test_lower`, `test_break_continue`, `test_try_catch`, `test_switch`, `test_type_convert`, `test_slice`, `test_string_ops`, `test_map`, `test_record`, `test_set_ops`, `test_deque`, `test_lint`, `test_optimize`, `test_javascript`, `test_rust`, `test_go`, `test_source_map`, `test_debug`, `test_explain`, `test_explain_errors`, `test_wasm_host_print`, `test_import`, `test_fuzz`, `test_helpers`, `test_cli_helpers`, `test_retry`, `test_regression_suite`.

If ANY test fails, revert the specific change that caused the failure and re-run. Do NOT mark this done until every test passes.

Show a summary of:
- What was changed and why
- Lines removed vs added (net reduction is the goal)
- Final test results

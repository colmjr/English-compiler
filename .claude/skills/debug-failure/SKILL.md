---
name: debug-failure
description: Diagnose a failing test or runtime error by tracing through the compilation pipeline to isolate the root cause. Investigation only — does not make code changes.
argument-hint: "[error message, failing test name, or description of the problem]"
---

# Debug Failure

You are investigating: **$ARGUMENTS**

This is a **read-only investigation**. Do NOT make code changes — only report findings.

## Phase 1: Reproduce

First, reproduce the failure:

1. If a test name was given, run that specific test and capture the full output (including tracebacks)
2. If an error message was given, search for where it originates in the codebase
3. If a Core IL program was given, run it through the interpreter and capture output

Establish clearly: **what is the actual output** vs **what is the expected output**?

## Phase 2: Trace Through the Pipeline

Investigate each pipeline stage to isolate where the bug is introduced. Use the Task tool to run these **in parallel**:

**Agent 1 — Core IL validity**:
If a `.coreil.json` file is involved, read it and check:
- Does it pass `validate_coreil()`? If not, what validation error?
- Are all node types spelled correctly?
- Are expressions used where expressions are expected (not statements)?
- Are there any uses of non-existent helper functions or invented operations?

**Agent 2 — Interpreter behavior**:
Read `english_compiler/coreil/interp.py` and trace the execution path for the failing input:
- Which `_exec_stmt` / `_eval_expr` branch handles the relevant node?
- What are the intermediate values at each step?
- Where does the output diverge from expected?

**Agent 3 — Backend behavior** (if backend parity failure):
Read the relevant backend (`emit.py`, `emit_javascript.py`, `emit_cpp.py`, `emit_rust.py`, `emit_go.py`, `emit_assemblyscript.py`) and shared utilities (`emit_base.py`, `emit_utils.py`) and trace the codegen:
- What code does the backend emit for the failing node?
- Does the emitted code match the interpreter's semantics?
- Are there missing cases or incorrect translations?

**Agent 4 — Lowering pass / shared modules** (if For/ForEach or module system involved):
Read `english_compiler/coreil/lower.py`, `module.py`, `node_nav.py`, and `constants.py` and check:
- Is the lowering transformation correct for this case?
- Does the lowered While loop preserve the original semantics?
- Are loop variables and iterators handled correctly?
- For Import issues: is module resolution and flattening correct?

## Phase 3: Report

Present a clear diagnosis:

1. **Failure location**: Which pipeline stage introduces the bug (frontend / validation / lowering / interpreter / backend)?
2. **Root cause**: What specifically is wrong (missing case, off-by-one, wrong operator, etc.)?
3. **Affected code**: File path and line number(s) where the fix would go
4. **Suggested fix**: Brief description of what the fix should do (but do NOT implement it)
5. **Blast radius**: What other tests or features might be affected by a fix here?

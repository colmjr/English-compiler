# TODO

Feature ideas and improvements for the English Compiler. Items are tagged by priority.

**Tags:**
- `[HIGH]` — Strong next candidates; high impact or frequently requested
- `[MED]` — Solid ideas worth doing; needs design or scheduling
- `[LOW]` — Nice-to-have; someday/maybe
- `[EXPLORE]` — Needs research before committing

---

## New Core IL Nodes / Language Features

- ~~`[HIGH]` Ternary/conditional expressions (inline if/else)~~ ✅ Done (v1.11 — Ternary)
- ~~`[HIGH]` String interpolation / f-string style expressions~~ ✅ Done (v1.11 — StringFormat)
- `[MED]` Lambda/anonymous functions
- `[MED]` List comprehensions / map/filter/reduce
- `[MED]` Destructuring assignment (unpack tuple/record into variables)
- `[MED]` Enum type
- `[MED]` Optional/nullable type handling (null coalescing)
- `[LOW]` Classes/structs with methods (beyond Records)
- `[LOW]` Multi-return from functions
- `[EXPLORE]` Import/module system for Core IL programs

## Backend Expansion

- ~~`[HIGH]` Rust backend: JSON and Regex support (currently raises errors)~~ ✅ Done (pure Rust JSON parser/serializer + NFA regex engine)
- ~~`[HIGH]` Go backend: JSON and Regex support (currently raises errors)~~ ✅ Done (encoding/json + regexp stdlib)
- `[MED]` TypeScript backend (separate from WASM/AssemblyScript)
- `[MED]` Java backend
- `[LOW]` C backend (vs C++)
- `[LOW]` Swift backend
- `[LOW]` Kotlin backend

## Tooling & Developer Experience

- `[HIGH]` `english-compiler test` — built-in test runner with assert statements
- `[MED]` VS Code extension (syntax highlighting, diagnostics for Core IL JSON)
- `[MED]` `english-compiler fmt` — pretty-print/reformat Core IL JSON
- `[MED]` `english-compiler diff` — semantic diff between two Core IL files
- `[MED]` Profiler mode (count statement executions, timing)
- `[MED]` `english-compiler visualize` — AST visualization (mermaid/graphviz)
- `[LOW]` LSP server for Core IL JSON (autocomplete, hover, diagnostics)
- `[LOW]` Playground/web REPL (compile in browser)
- `[EXPLORE]` Execution trace export (JSON log of every step)

## Optimizer Improvements

- `[MED]` Function inlining for small functions
- `[MED]` Loop-invariant code motion
- `[LOW]` Loop unrolling
- `[EXPLORE]` Escape analysis (optimize heap allocations)

## Frontend / LLM Improvements

- `[HIGH]` Auto-fix mode — when validation fails, send errors back to LLM to retry
- `[MED]` Multi-file compilation (import across .txt files)
- `[MED]` Conversation mode — iteratively refine Core IL through dialogue
- `[MED]` Ollama/local LLM frontend
- `[LOW]` Cost tracking per compilation
- `[EXPLORE]` Fine-tuned small model for Core IL generation

## Static Analysis & Correctness

- ~~`[HIGH]` More lint rules: unused functions, infinite loop detection, unreachable branches~~ ✅ Done (unused-function, infinite-loop, unreachable-branch)
- `[MED]` Type inference pass (infer types without annotations)
- `[MED]` Purity analysis (mark functions as pure/impure)
- `[LOW]` Bounds checking at compile time where possible
- `[LOW]` Complexity analysis (Big-O estimation)

## Documentation & Education

- `[MED]` Interactive tutorial mode (guided Core IL exercises)
- `[MED]` Example gallery with curated English-to-code demonstrations
- `[LOW]` Video walkthroughs of compilation pipeline

## Infrastructure & Testing

- `[HIGH]` GitHub Actions for automated backend parity testing on PRs
- `[MED]` Benchmarking suite (track compilation speed over time)
- `[MED]` Fuzz testing (generate random Core IL, ensure no crashes)
- `[LOW]` Property-based testing for backend parity

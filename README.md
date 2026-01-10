# English Compiler

A production-ready compiler that translates English pseudocode into executable code through a deterministic intermediate representation (Core IL).

## Project Status

**Core IL v1.0 is stable and production-ready.** 🎉

The compiler has successfully compiled and executed real-world algorithms including:
- Array operations (sum, reverse, max)
- Sorting algorithms (bubble sort)
- String processing (bigram frequency)
- Advanced algorithms (Byte Pair Encoding - 596 lines of Core IL)

All tests pass with 100% parity between interpreter and Python code generation.

**📚 Documentation**:
- [STATUS.md](STATUS.md) - Detailed project status and capabilities
- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [MIGRATION.md](MIGRATION.md) - Upgrade guide from v0.5 to v1.0
- [VERSIONING.md](VERSIONING.md) - Version strategy and code hygiene
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Fast reference for Core IL syntax

## Requirements

- Python 3.10+
- Standard library for core functionality
- Optional: Anthropic SDK for Claude (`pip install anthropic`)

## Quick start (mock frontend)

1) Create a source file:

```sh
printf "hello\n" > examples/hello.txt
```

2) Compile and run:

```sh
python -m english_compiler compile --frontend mock examples/hello.txt
```

Expected output:

```text
Regenerating Core IL for examples/hello.txt
hello
```

## CLI usage

### Compile

```sh
python -m english_compiler compile [--frontend mock|claude] [--target coreil|python] [--regen] [--freeze] <source.txt>
```

Behavior:
- Produces `foo.coreil.json` and `foo.lock.json` next to the source file.
- When `--target python` is specified, also generates `foo.py` with executable Python code.
- Uses cached artifacts if they match the source hash.
- Exits `2` and prints ambiguity details when `ambiguities` is non-empty.

Flags:
- `--frontend mock`: use the mocked generator (default when no API key).
- `--frontend claude`: use Anthropic Claude (requires `ANTHROPIC_API_KEY`).
- `--target coreil`: only emit Core IL JSON (default).
- `--target python`: emit both Core IL JSON and Python code.
- `--regen`: force regeneration even if cache is valid.
- `--freeze`: fail if regeneration would be required.

### Run an existing Core IL file

```sh
python -m english_compiler run examples/hello.coreil.json
```

## Architecture

The compiler follows a three-stage pipeline:

```
English Text → LLM Frontend → Core IL (JSON) → Deterministic Backends
```

1. **Frontend (LLM)**: Claude translates English/pseudocode into Core IL JSON
   - This is the only non-deterministic step
   - Output is cached for reproducibility

2. **Core IL**: A closed, deterministic intermediate representation
   - All semantics are explicitly defined
   - No extension mechanism or helper functions
   - Version 1.0 is stable and frozen

3. **Backends**: Deterministic execution
   - Interpreter: Direct execution of Core IL
   - Python codegen: Transpiles to executable Python
   - Both backends produce identical output (verified by tests)

## Core IL v1.0

Core IL is a complete, closed intermediate representation with explicit primitives for all operations.

**Full specification**: [coreil_v1.md](coreil_v1.md)

**Key features**:
- Expressions: Literal, Var, Binary, Array, Tuple, Map, Index, Length, Get, GetDefault, Keys, Range, Call
- Statements: Let, Assign, SetIndex, Set, Push, Print, If, While, For, ForEach, FuncDef, Return
- Short-circuit evaluation for logical operators (`and`, `or`)
- Runtime type checking with clear error messages
- Recursion support with depth limits
- Dictionary insertion order preservation

**Historical versions** (for reference):
- [docs/coreil_v0_1.md](docs/coreil_v0_1.md) - Basic statements and expressions
- [docs/coreil_v0_2.md](docs/coreil_v0_2.md) - Arrays and indexing
- [docs/coreil_v0_3.md](docs/coreil_v0_3.md) - Functions, returns, and syntax sugar (For/Range loops)
- [docs/coreil_v0_5.md](docs/coreil_v0_5.md) - Sealed primitives (GetDefault, Keys, Push, Tuple)

## Artifacts

When compiling `foo.txt`, the following files are created:

- `foo.coreil.json`: Core IL program (always generated)
- `foo.lock.json`: cache metadata (hashes, model, timestamp)
- `foo.py`: executable Python code (only when `--target python` is used)

Cache reuse is based on the source hash and Core IL hash.

## Claude setup

Install the SDK:

```sh
python -m pip install anthropic
```

Required env vars:

```sh
export ANTHROPIC_API_KEY="your_api_key_here"
export ANTHROPIC_MODEL="claude-sonnet-4-5"
export ANTHROPIC_MAX_TOKENS="4096"
```

Compile with Claude:

```sh
python -m english_compiler compile --frontend claude examples/hello.txt
```

## Demo script

Run the Claude demo (prints a generated Core IL JSON object):

```sh
python -m scripts.demo_claude_compile
```

## Python code generation

The compiler can generate executable Python code from Core IL:

```sh
python -m english_compiler compile --target python examples/hello.txt
```

This produces `examples/hello.py` with the generated Python code. The generated code:
- Uses standard Python syntax and semantics
- Matches interpreter output exactly (verified by parity tests)
- Handles all Core IL v1.0 features (including maps, functions, loops, tuples, and sealed primitives)

### Backend parity tests

Run tests that verify the generated Python produces identical output to the interpreter:

```sh
python -m tests.run_parity
```

This tests all examples in the `examples/` directory and reports any mismatches.

## Exit codes

- `0`: success
- `1`: error (I/O, validation failure, or runtime error)
- `2`: ambiguities present (artifacts still written)

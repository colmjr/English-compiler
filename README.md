# English-compiler

A beginner-friendly compiler-like CLI that turns English or pseudocode into Core IL JSON, validates it, writes artifacts, and can execute the result.

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

## Core IL format

Core IL is documented in versioned specifications:

- `docs/coreil_v0_1.md` - Basic statements and expressions
- `docs/coreil_v0_2.md` - Arrays and indexing
- `docs/coreil_v0_3.md` - Functions, returns, and syntax sugar (For/Range loops)
- `docs/coreil_v0_4.md` - Maps/records (Map, Get, Set)
- `docs/coreil_v0_5.md` - Sealed primitives (GetDefault, Keys, Push, Tuple)

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
- Handles all Core IL v0.1-v0.5 features (including maps, functions, loops, and sealed primitives)

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

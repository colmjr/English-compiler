# English-compiler

## Run a Core IL file

Example:

```sh
python -m english_compiler run examples/hello.coreil.json
```

## Claude setup

Install the SDK:

```sh
python -m pip install anthropic
```

Required env vars:

```sh
export ANTHROPIC_API_KEY="your_api_key_here"
export ANTHROPIC_MODEL="claude-3-5-sonnet-20241022"
export ANTHROPIC_MAX_TOKENS="4096"
```

Run the demo script:

```sh
python scripts/demo_claude_compile.py
```

Compile with Claude:

```sh
python -m english_compiler compile --frontend claude examples/hello.txt
```

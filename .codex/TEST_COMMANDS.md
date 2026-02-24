# Test Commands

Use the project venv and run from the repository root.

Canonical commands (after activating `.venv`):

```sh
python -m tests.run
python -m tests.run_algorithms
python -m tests.run_parity
python -m tests.test_*
```

Equivalent explicit venv commands:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.run
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.run_algorithms
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.run_parity
```

Run all specialized test modules:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_break_continue
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_cli_helpers
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_debug
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_deque
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_explain
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_explain_errors
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_fuzz
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_go
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_helpers
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_import
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_javascript
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_lint
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_lower
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_map
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_optimize
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_record
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_regression_suite
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_retry
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_rust
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_set_ops
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_settings
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_short_circuit
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_slice
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_source_map
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_string_ops
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_switch
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_try_catch
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_type_convert
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m tests.test_wasm_host_print
```

Known behavior:
- `tests.run_parity` currently reports 2 expected failures:
  - `external_call_demo.coreil` (interpreter does not support `ExternalCall`)
  - `module_main.coreil` (import resolution requires `base_dir`)

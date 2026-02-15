"""CLI entry point for english_compiler."""

from __future__ import annotations

import argparse

from english_compiler import __version__
from english_compiler.settings import (
    Settings,
    get_config_path,
    load_settings,
    save_settings,
    delete_settings,
    VALID_FRONTENDS,
    VALID_TARGETS,
)
import datetime
import hashlib
import json
from pathlib import Path

# Built-in exit commands (instant, no API call)
BUILTIN_EXIT_COMMANDS = {"exit", "quit", ":q", ":quit", ":exit"}
TIER2_FALLBACK_ERROR_MARKERS = ("ExternalCall", "MethodCall", "PropertyGet")
TRUE_VALUE_STRINGS = ("true", "1", "yes", "on")
FALSE_VALUE_STRINGS = ("false", "0", "no", "off")


def _print_validation_errors(errors: list[dict]) -> None:
    for error in errors:
        print(f"{error['path']}: {error['message']}")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_json(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _write_json(path: Path, data: dict) -> bool:
    try:
        path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        print(f"{path}: {exc}")
        return False
    return True


def _get_output_path(source_path: Path, subdir: str, suffix: str) -> Path:
    """Get output path in organized directory structure.

    Args:
        source_path: Path to source file (e.g., examples/hello.txt)
        subdir: Subdirectory name (e.g., "coreil", "py", "cpp")
        suffix: File suffix including dot (e.g., ".coreil.json", ".py")

    Returns:
        Path like examples/output/py/hello.py
    """
    output_dir = source_path.parent / "output" / subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / (source_path.stem + suffix)


def _print_ambiguities(ambiguities: list[dict]) -> None:
    print("Ambiguities detected:")
    for i, item in enumerate(ambiguities, start=1):
        question = item.get("question", "(missing question)")
        options = item.get("options", [])
        default = item.get("default", None)
        if isinstance(options, list):
            options_text = ", ".join(str(opt) for opt in options)
        else:
            options_text = str(options)
        print(f"{i}. {question}")
        print(f"   options: {options_text}")
        print(f"   default: {default}")


def _print_experimental_warning() -> None:
    """Print warning banner for experimental mode."""
    print("=" * 70)
    print("WARNING: EXPERIMENTAL MODE - Direct LLM Compilation")
    print("=" * 70)
    print("This mode bypasses Core IL and generates code directly.")
    print()
    print("Implications:")
    print("  - NON-DETERMINISTIC: Same input may produce different outputs")
    print("  - NO SEMANTIC VALIDATION: Generated code is not verified")
    print("  - POTENTIAL BUGS: LLM may generate incorrect or unsafe code")
    print()
    print("DO NOT use in production systems.")
    print("=" * 70)
    print()


def _get_experimental_output_path(source_path: Path, target: str, suffix: str) -> Path:
    """Get output path for experimental mode.

    Args:
        source_path: Path to source file
        target: Target language ("python", "javascript", "cpp")
        suffix: File suffix including dot

    Returns:
        Path like examples/output/experimental/py/hello.py
    """
    # Map target to subdirectory
    subdir_map = {"python": "py", "javascript": "js", "cpp": "cpp"}
    subdir = subdir_map.get(target, target)
    output_dir = source_path.parent / "output" / "experimental" / subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / (source_path.stem + suffix)


def _generate_code_header(model_name: str, target: str) -> str:
    """Generate warning header for experimental code.

    Args:
        model_name: The model used for generation
        target: Target language

    Returns:
        Warning header as a string
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    comment_chars = {"python": "#", "javascript": "//", "cpp": "//"}
    c = comment_chars.get(target, "#")

    return f"""{c} ============================================================================
{c} EXPERIMENTAL: Generated directly by LLM without Core IL validation
{c} Model: {model_name}
{c} Generated: {timestamp}
{c} WARNING: This code is NON-DETERMINISTIC and may contain bugs
{c} ============================================================================

"""


def _run_python_file(python_path: Path) -> int:
    """Run a Python file and return exit code."""
    import subprocess
    import sys
    result = subprocess.run([sys.executable, str(python_path)], capture_output=False)
    return result.returncode


def _run_javascript_file(js_path: Path) -> int:
    """Run a JavaScript file with Node.js and return exit code."""
    import subprocess
    result = subprocess.run(["node", str(js_path)], capture_output=False)
    return result.returncode


def _run_rust_file(rust_path: Path) -> int:
    """Compile and run a Rust file and return exit code."""
    import subprocess
    import tempfile
    import shutil

    compiler = shutil.which("rustc")
    if compiler is None:
        print("Error: rustc not found")
        return 1

    with tempfile.NamedTemporaryFile(suffix="", delete=False) as tmp:
        exe_path = tmp.name

    try:
        from english_compiler.coreil.emit_rust import get_runtime_path
        runtime_dir = get_runtime_path().parent

        # Copy runtime to same directory as source so include! works
        import shutil as shutil2
        runtime_dst = rust_path.parent / "coreil_runtime.rs"
        shutil2.copy(get_runtime_path(), runtime_dst)

        compile_result = subprocess.run(
            [compiler, str(rust_path), "-o", exe_path, "--edition", "2021"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if compile_result.returncode != 0:
            print(f"Rust compilation failed:\n{compile_result.stderr}")
            return 1

        result = subprocess.run([exe_path], capture_output=False, timeout=30)
        return result.returncode

    except subprocess.TimeoutExpired:
        print("Rust execution timeout")
        return 1
    finally:
        Path(exe_path).unlink(missing_ok=True)


def _run_cpp_file(cpp_path: Path) -> int:
    """Compile and run a C++ file and return exit code."""
    import subprocess
    import tempfile
    import shutil

    # Check for g++ or clang++
    compiler = None
    for cc in ["g++", "clang++"]:
        if shutil.which(cc):
            compiler = cc
            break

    if compiler is None:
        print("Error: No C++ compiler found (tried g++, clang++)")
        return 1

    # Create temp executable
    with tempfile.NamedTemporaryFile(suffix="", delete=False) as tmp:
        exe_path = tmp.name

    try:
        # Compile with runtime header directory in include path
        from english_compiler.coreil.emit_cpp import get_runtime_header_path
        include_dir = get_runtime_header_path().parent

        compile_result = subprocess.run(
            [compiler, "-std=c++17", "-O2", "-I", str(include_dir), str(cpp_path), "-o", exe_path],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if compile_result.returncode != 0:
            print(f"C++ compilation failed:\n{compile_result.stderr}")
            return 1

        # Run the compiled executable
        result = subprocess.run([exe_path], capture_output=False, timeout=30)
        return result.returncode

    except subprocess.TimeoutExpired:
        print("C++ execution timeout")
        return 1
    finally:
        # Clean up temp executable
        Path(exe_path).unlink(missing_ok=True)


def _is_tier2_unsupported_error(exc: ValueError) -> bool:
    message = str(exc)
    return any(marker in message for marker in TIER2_FALLBACK_ERROR_MARKERS)


def _run_tier2_fallback(
    source_path: Path,
    target: str,
    supported_targets: tuple[str, ...],
) -> int | None:
    if target not in supported_targets:
        return None

    if target == "python":
        python_path = _get_output_path(source_path, "py", ".py")
        print(f"Note: Tier 2 operation not supported in interpreter, running {python_path}")
        return _run_python_file(python_path)

    if target == "javascript":
        js_path = _get_output_path(source_path, "js", ".js")
        print(f"Note: Tier 2 operation not supported in interpreter, running {js_path}")
        return _run_javascript_file(js_path)

    if target == "cpp":
        cpp_path = _get_output_path(source_path, "cpp", ".cpp")
        print(f"Note: Tier 2 operation not supported in interpreter, running {cpp_path}")
        return _run_cpp_file(cpp_path)

    if target == "rust":
        rust_path = _get_output_path(source_path, "rust", ".rs")
        print(f"Note: Tier 2 operation not supported in interpreter, running {rust_path}")
        return _run_rust_file(rust_path)

    return None


def _parse_bool_setting(value: str) -> bool | None:
    normalized = value.lower()
    if normalized in TRUE_VALUE_STRINGS:
        return True
    if normalized in FALSE_VALUE_STRINGS:
        return False
    return None


def _emit_target_code(
    doc: dict,
    source_path: Path,
    coreil_path: Path,
    target: str,
    check_freshness: bool = False,
) -> bool:
    """Emit code for the specified target.

    Args:
        doc: The Core IL document
        source_path: Path to the source file (used to derive output paths)
        coreil_path: Path to the Core IL JSON file
        target: Target language ("coreil", "python", "javascript", "cpp", "wasm")
        check_freshness: If True, skip generation if target is newer than coreil

    Returns:
        True if successful, False on error (error message already printed)
    """
    if target == "coreil":
        return True

    from english_compiler.coreil.emit import emit_python
    from english_compiler.coreil.emit_javascript import emit_javascript
    from english_compiler.coreil.emit_cpp import emit_cpp, get_runtime_header_path, get_json_header_path
    import shutil

    if target == "python":
        output_path = _get_output_path(source_path, "py", ".py")
        lang_name = "Python"
        emit_func = emit_python
    elif target == "javascript":
        output_path = _get_output_path(source_path, "js", ".js")
        lang_name = "JavaScript"
        emit_func = emit_javascript
    elif target == "cpp":
        output_path = _get_output_path(source_path, "cpp", ".cpp")
        lang_name = "C++"
        emit_func = emit_cpp
    elif target == "rust":
        from english_compiler.coreil.emit_rust import emit_rust, get_runtime_path as get_rust_runtime_path
        output_path = _get_output_path(source_path, "rust", ".rs")
        lang_name = "Rust"
        emit_func = emit_rust
    elif target == "go":
        from english_compiler.coreil.emit_go import emit_go, get_runtime_path as get_go_runtime_path
        output_path = _get_output_path(source_path, "go", ".go")
        lang_name = "Go"
        emit_func = emit_go
    elif target == "wasm":
        # WASM target - emit AssemblyScript and optionally compile
        return _emit_wasm_target(doc, source_path, coreil_path, check_freshness)
    else:
        return True

    # Check freshness if requested
    if check_freshness and output_path.exists():
        if output_path.stat().st_mtime >= coreil_path.stat().st_mtime:
            return True

    try:
        code = emit_func(doc)
        output_path.write_text(code, encoding="utf-8")
        print(f"Generated {lang_name} code at {output_path}")

        # For C++, also copy runtime headers
        if target == "cpp":
            runtime_dir = output_path.parent
            shutil.copy(get_runtime_header_path(), runtime_dir / "coreil_runtime.hpp")
            shutil.copy(get_json_header_path(), runtime_dir / "json.hpp")

        # For Rust, copy runtime library
        if target == "rust":
            runtime_dir = output_path.parent
            shutil.copy(get_rust_runtime_path(), runtime_dir / "coreil_runtime.rs")

        # For Go, copy runtime library
        if target == "go":
            runtime_dir = output_path.parent
            shutil.copy(get_go_runtime_path(), runtime_dir / "coreil_runtime.go")

    except OSError as exc:
        print(f"{output_path}: {exc}")
        return False
    except (ValueError, TypeError, KeyError) as exc:
        print(f"{lang_name} codegen failed: {exc}")
        return False

    return True


def _emit_wasm_target(
    doc: dict,
    source_path: Path,
    coreil_path: Path,
    check_freshness: bool = False,
) -> bool:
    """Emit AssemblyScript code and optionally compile to WASM.

    Args:
        doc: The Core IL document
        source_path: Path to the source file
        coreil_path: Path to the Core IL JSON file
        check_freshness: If True, skip if target is newer than coreil

    Returns:
        True if successful, False on error
    """
    import shutil
    from english_compiler.coreil.emit_assemblyscript import emit_assemblyscript, get_runtime_path
    from english_compiler.coreil.wasm_build import ASC_AVAILABLE, compile_to_wasm

    # AssemblyScript output path
    as_path = _get_output_path(source_path, "wasm", ".as.ts")

    # Check freshness
    if check_freshness and as_path.exists():
        if as_path.stat().st_mtime >= coreil_path.stat().st_mtime:
            return True

    try:
        code = emit_assemblyscript(doc)
        as_path.write_text(code, encoding="utf-8")
        print(f"Generated AssemblyScript code at {as_path}")

        # Copy runtime library
        runtime_dir = as_path.parent
        runtime_src = get_runtime_path()
        runtime_dst = runtime_dir / "coreil_runtime.ts"
        shutil.copy(runtime_src, runtime_dst)
        print(f"Copied runtime library to {runtime_dst}")

    except OSError as exc:
        print(f"{as_path}: {exc}")
        return False
    except (ValueError, TypeError, KeyError) as exc:
        print(f"AssemblyScript codegen failed: {exc}")
        return False

    # Optionally compile to WASM if asc is available
    if ASC_AVAILABLE:
        result = compile_to_wasm(
            code,
            as_path.parent,  # output/wasm/
            source_path.stem,
            emit_wat=False,
            optimize=True,
        )
        if result.success:
            print(f"Compiled to WebAssembly at {result.wasm_path}")
        else:
            print(f"WASM compilation failed: {result.error}")
            print("Note: AssemblyScript source was still generated successfully")
    else:
        print("Note: asc compiler not found, skipping WASM compilation")
        print("      Install with: npm install -g assemblyscript")

    return True


def _compile_experimental(args: argparse.Namespace) -> int:
    """Handle experimental mode compilation (direct LLM to target code)."""
    from english_compiler.frontend import get_frontend
    from english_compiler.frontend.experimental import validate_syntax

    target = args.target
    source_path = Path(args.file)

    # Determine file suffix
    suffix_map = {"python": ".py", "javascript": ".js", "cpp": ".cpp"}
    suffix = suffix_map[target]

    output_path = _get_experimental_output_path(source_path, target, suffix)
    lock_path = _get_experimental_output_path(source_path, target, ".exp.lock.json")

    try:
        source_text = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"{source_path}: {exc}")
        return 1

    source_sha256 = _sha256_bytes(source_text.encode("utf-8"))

    # Check cache
    lock_doc = _load_json(lock_path)
    reuse_cache = False
    if not args.regen and lock_doc is not None:
        lock_source_sha256 = lock_doc.get("source_sha256")
        lock_target = lock_doc.get("target")
        if (
            isinstance(lock_source_sha256, str)
            and lock_source_sha256 == source_sha256
            and lock_target == target
            and output_path.exists()
        ):
            reuse_cache = True

    if reuse_cache:
        print(f"Using cached experimental output from {output_path}")
    else:
        if args.freeze:
            print(f"freeze enabled: regeneration required for {source_path}")
            return 1

        # Print warning
        _print_experimental_warning()

        # Get frontend
        frontend_name = args.frontend
        try:
            frontend = get_frontend(frontend_name)
        except RuntimeError as exc:
            print(str(exc))
            return 1

        print(f"Generating {target} code for {source_path} using {frontend.get_model_name()}")

        try:
            code = frontend.generate_code_direct(source_text, target)
        except RuntimeError as exc:
            print(f"Frontend error: {exc}")
            return 1

        # Validate syntax (Python only)
        errors = validate_syntax(code, target)
        if errors:
            print("Syntax validation errors:")
            for error in errors:
                print(f"  {error}")
            print("Note: Code was still generated but may not be executable")

        # Add warning header
        header = _generate_code_header(frontend.get_model_name(), target)
        full_code = header + code

        # Write output
        try:
            output_path.write_text(full_code, encoding="utf-8")
            print(f"Generated {target} code at {output_path}")
        except OSError as exc:
            print(f"{output_path}: {exc}")
            return 1

        # Write lock file
        lock_doc = {
            "source_sha256": source_sha256,
            "model": frontend.get_model_name(),
            "target": target,
            "experimental": True,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        if not _write_json(lock_path, lock_doc):
            return 1

    # Run the generated code
    print()
    print("Running generated code:")
    print("-" * 40)
    if target == "python":
        return _run_python_file(output_path)
    elif target == "javascript":
        return _run_javascript_file(output_path)
    elif target == "cpp":
        return _run_cpp_file(output_path)
    return 0


def _handle_watch_mode(args: argparse.Namespace) -> int:
    """Handle watch mode for automatic recompilation."""
    from english_compiler.watch import is_watchfiles_available, watch_and_compile

    if not is_watchfiles_available():
        print("Error: watchfiles is not installed.")
        print("Install it with: pip install english-compiler[watch]")
        return 1

    if args.freeze:
        print("--watch and --freeze cannot be used together")
        return 1

    source_path = Path(args.file)

    def compile_single_file(file_path: Path) -> int:
        """Wrapper that compiles a single file."""
        # Create a modified args with the specific file
        modified_args = argparse.Namespace(**vars(args))
        modified_args.file = str(file_path)
        modified_args.watch = False  # Prevent recursion
        return _compile_command(modified_args)

    return watch_and_compile(source_path, compile_single_file)


def _compile_command(args: argparse.Namespace) -> int:
    from english_compiler.coreil.interp import run_coreil
    from english_compiler.coreil.validate import validate_coreil
    from english_compiler.frontend import get_frontend

    # Handle watch mode first
    if getattr(args, "watch", False):
        return _handle_watch_mode(args)

    if args.regen and args.freeze:
        print("--regen and --freeze cannot be used together")
        return 1

    # Load settings and apply defaults
    settings = load_settings()

    # Apply settings as defaults when CLI args not provided
    # Note: args.frontend is None when not specified on CLI
    # args.target is None when not specified (we use sentinel None instead of default "coreil")
    if args.frontend is None:
        args.frontend = settings.frontend
    if not args.explain_errors:
        args.explain_errors = settings.explain_errors
    if args.target is None:
        args.target = settings.target if settings.target else "coreil"
    if not args.regen:
        args.regen = settings.regen
    if not args.freeze:
        args.freeze = settings.freeze

    # Handle experimental mode
    if args.experimental:
        valid_experimental_targets = ("python", "javascript", "cpp")
        if args.target not in valid_experimental_targets:
            print(
                f"--experimental requires --target to be one of: "
                f"{', '.join(valid_experimental_targets)}"
            )
            print(f"Got: --target {args.target}")
            return 1
        return _compile_experimental(args)

    source_path = Path(args.file)
    coreil_path = _get_output_path(source_path, "coreil", ".coreil.json")
    lock_path = _get_output_path(source_path, "coreil", ".lock.json")

    try:
        source_text = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"{source_path}: {exc}")
        return 1

    source_sha256 = _sha256_bytes(source_text.encode("utf-8"))

    # Set up error callback if requested
    error_callback = None
    explain_frontend = None
    if getattr(args, "explain_errors", False):
        try:
            explain_frontend = get_frontend(args.frontend)
            error_callback = _make_error_callback(explain_frontend, source_text)
        except RuntimeError as exc:
            print(str(exc))
            return 1

    lock_doc = _load_json(lock_path)
    reuse_cache = False
    if not args.regen and lock_doc is not None:
        lock_source_sha256 = lock_doc.get("source_sha256")
        lock_coreil_sha256 = lock_doc.get("coreil_sha256")
        if (
            isinstance(lock_source_sha256, str)
            and isinstance(lock_coreil_sha256, str)
            and lock_source_sha256 == source_sha256
            and coreil_path.exists()
        ):
            coreil_sha256 = _sha256_file(coreil_path)
            if coreil_sha256 == lock_coreil_sha256:
                reuse_cache = True

    if reuse_cache:
        print(f"Using cached Core IL from {coreil_path}")
        doc = _load_json(coreil_path)
        if doc is None:
            print(f"{coreil_path}: invalid json")
            return 1

        # Run optimizer if requested
        if getattr(args, "optimize", False):
            from english_compiler.coreil.optimize import optimize
            doc = optimize(doc)
            print("Applied optimization pass")

        # Run lint if requested
        if getattr(args, "lint", False):
            lint_rc = _run_lint_on_doc(doc)
            if lint_rc != 0:
                return lint_rc

        # Emit code for the specified target (even when using cache)
        target = getattr(args, "target", "coreil")
        if not _emit_target_code(doc, source_path, coreil_path, target, check_freshness=True):
            return 1

        ambiguities = doc.get("ambiguities", [])
        if isinstance(ambiguities, list) and ambiguities:
            _print_ambiguities(ambiguities)
            return 2

        # Try interpreter first, fall back to generated code for ExternalCall
        try:
            return run_coreil(doc, error_callback=error_callback)
        except ValueError as exc:
            if _is_tier2_unsupported_error(exc):
                fallback_rc = _run_tier2_fallback(
                    source_path,
                    target,
                    supported_targets=("python", "javascript", "cpp", "rust"),
                )
                if fallback_rc is not None:
                    return fallback_rc
            raise

    if args.freeze:
        print(f"freeze enabled: regeneration required for {source_path}")
        return 1

    # Get frontend (auto-detect if not specified, reuse if already created for explain_errors)
    if explain_frontend is not None:
        frontend = explain_frontend
    else:
        frontend_name = args.frontend
        try:
            frontend = get_frontend(frontend_name)
        except RuntimeError as exc:
            print(str(exc))
            return 1

    print(f"Regenerating Core IL for {source_path} using {frontend.get_model_name()}")
    try:
        doc = frontend.generate_coreil_from_text(source_text)
    except RuntimeError as exc:
        print(f"Frontend error: {exc}")
        return 1
    model_name = frontend.get_model_name()
    errors = validate_coreil(doc)
    if errors:
        _print_validation_errors(errors)
        return 1

    if not _write_json(coreil_path, doc):
        return 1

    # Run optimizer if requested
    if getattr(args, "optimize", False):
        from english_compiler.coreil.optimize import optimize
        doc = optimize(doc)
        print("Applied optimization pass")

    # Run lint if requested
    if getattr(args, "lint", False):
        lint_rc = _run_lint_on_doc(doc)
        if lint_rc != 0:
            return lint_rc

    # Emit code for the specified target
    target = getattr(args, "target", "coreil")
    if not _emit_target_code(doc, source_path, coreil_path, target, check_freshness=False):
        return 1

    lock_doc = {
        "source_sha256": source_sha256,
        "coreil_sha256": _sha256_file(coreil_path),
        "model": model_name,
        "system_prompt_version": "dev",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    if not _write_json(lock_path, lock_doc):
        return 1

    ambiguities = doc.get("ambiguities", [])
    if isinstance(ambiguities, list) and ambiguities:
        _print_ambiguities(ambiguities)
        return 2

    # Try interpreter first, fall back to generated code for Tier 2 operations
    try:
        return run_coreil(doc, error_callback=error_callback)
    except ValueError as exc:
        if _is_tier2_unsupported_error(exc):
            fallback_rc = _run_tier2_fallback(
                source_path,
                target,
                supported_targets=("python", "javascript", "cpp"),
            )
            if fallback_rc is not None:
                return fallback_rc
        raise


def _make_error_callback(frontend, source_text: str | None = None):
    """Create an error callback that uses the LLM to explain errors.

    Args:
        frontend: The LLM frontend to use.
        source_text: Optional source text for context.

    Returns:
        A callback function that prints an LLM-explained error.
    """
    from english_compiler.frontend.error_explainer import explain_error

    def callback(error_msg: str) -> None:
        explanation = explain_error(frontend, error_msg, source_text)
        print(explanation)

    return callback


def _run_command(args: argparse.Namespace) -> int:
    from english_compiler.coreil.interp import run_coreil

    # Load settings and apply defaults
    settings = load_settings()
    frontend_name = args.frontend if args.frontend is not None else settings.frontend
    explain_errors = args.explain_errors or settings.explain_errors

    path = Path(args.file)
    try:
        with path.open("r", encoding="utf-8") as handle:
            doc = json.load(handle)
    except OSError as exc:
        print(f"{path}: {exc}")
        return 1
    except json.JSONDecodeError as exc:
        print(f"{path}: invalid json: {exc}")
        return 1

    error_callback = None
    if explain_errors:
        from english_compiler.frontend import get_frontend

        try:
            frontend = get_frontend(frontend_name)
        except RuntimeError as exc:
            print(str(exc))
            return 1
        error_callback = _make_error_callback(frontend)

    return run_coreil(doc, error_callback=error_callback)


def _config_command(args: argparse.Namespace) -> int:
    """Handle the config subcommand."""
    config_action = getattr(args, "config_action", None)

    if config_action == "set":
        return _config_set(args.key, args.value)
    elif config_action == "get":
        return _config_get(args.key)
    elif config_action == "list":
        return _config_list()
    elif config_action == "path":
        return _config_path()
    elif config_action == "reset":
        return _config_reset()
    else:
        print("Usage: english-compiler config {set,get,list,path,reset}")
        return 1


def _config_set(key: str, value: str) -> int:
    """Set a config value."""
    settings = load_settings()

    # Normalize key (support both hyphen and underscore)
    key_normalized = key.replace("-", "_")

    if key_normalized == "frontend":
        if value not in VALID_FRONTENDS:
            print(f"Invalid frontend: {value}")
            print(f"Valid options: {', '.join(VALID_FRONTENDS)}")
            return 1
        settings.frontend = value
    elif key_normalized == "explain_errors":
        parsed_bool = _parse_bool_setting(value)
        if parsed_bool is None:
            print(f"Invalid boolean value: {value}")
            print("Use: true, false, 1, 0, yes, no, on, off")
            return 1
        settings.explain_errors = parsed_bool
    elif key_normalized == "target":
        if value not in VALID_TARGETS:
            print(f"Invalid target: {value}")
            print(f"Valid options: {', '.join(VALID_TARGETS)}")
            return 1
        settings.target = value
    elif key_normalized == "regen":
        parsed_bool = _parse_bool_setting(value)
        if parsed_bool is None:
            print(f"Invalid boolean value: {value}")
            print("Use: true, false, 1, 0, yes, no, on, off")
            return 1
        settings.regen = parsed_bool
    elif key_normalized == "freeze":
        parsed_bool = _parse_bool_setting(value)
        if parsed_bool is None:
            print(f"Invalid boolean value: {value}")
            print("Use: true, false, 1, 0, yes, no, on, off")
            return 1
        settings.freeze = parsed_bool
    else:
        print(f"Unknown setting: {key}")
        print("Valid settings: frontend, target, explain-errors, regen, freeze")
        return 1

    if not save_settings(settings):
        print(f"Failed to write config file: {get_config_path()}")
        return 1

    print(f"Set {key} = {value}")
    return 0


def _config_get(key: str) -> int:
    """Get a config value."""
    settings = load_settings()

    # Normalize key
    key_normalized = key.replace("-", "_")

    if key_normalized == "frontend":
        value = settings.frontend if settings.frontend else "(not set)"
    elif key_normalized == "explain_errors":
        value = str(settings.explain_errors).lower()
    elif key_normalized == "target":
        value = settings.target if settings.target else "(not set)"
    elif key_normalized == "regen":
        value = str(settings.regen).lower()
    elif key_normalized == "freeze":
        value = str(settings.freeze).lower()
    else:
        print(f"Unknown setting: {key}")
        print("Valid settings: frontend, target, explain-errors, regen, freeze")
        return 1

    print(f"{key}: {value}")
    return 0


def _config_list() -> int:
    """List all config values."""
    settings = load_settings()

    print("Current settings:")
    print(f"  frontend: {settings.frontend if settings.frontend else '(not set)'}")
    print(f"  target: {settings.target if settings.target else '(not set)'}")
    print(f"  explain-errors: {str(settings.explain_errors).lower()}")
    print(f"  regen: {str(settings.regen).lower()}")
    print(f"  freeze: {str(settings.freeze).lower()}")

    config_path = get_config_path()
    if config_path.exists():
        print(f"\nConfig file: {config_path}")
    else:
        print(f"\nConfig file: {config_path} (not created yet)")

    return 0


def _config_path() -> int:
    """Show config file path."""
    config_path = get_config_path()
    print(config_path)
    return 0


def _config_reset() -> int:
    """Delete config file."""
    config_path = get_config_path()

    if not config_path.exists():
        print(f"Config file does not exist: {config_path}")
        return 0

    if not delete_settings():
        print(f"Failed to delete config file: {config_path}")
        return 1

    print(f"Deleted config file: {config_path}")
    return 0


def _is_exit_command(text: str, frontend) -> bool:
    """Check if input is an exit command.

    Args:
        text: The user input text.
        frontend: The LLM frontend for natural language classification.

    Returns:
        True if the input is an exit command, False otherwise.
    """
    normalized = text.lower().strip()

    # Built-in commands (instant check)
    if normalized in BUILTIN_EXIT_COMMANDS:
        return True

    # Use LLM to classify natural language
    try:
        response = frontend.classify_exit_intent(normalized)
        return response.strip().upper() == "EXIT"
    except Exception:
        # On error, assume it's code (safe default)
        return False


def _repl_command(args: argparse.Namespace) -> int:
    """Interactive REPL for English pseudocode."""
    from english_compiler.coreil.interp import run_coreil
    from english_compiler.coreil.validate import validate_coreil
    from english_compiler.frontend import get_frontend

    # Load settings and apply defaults
    settings = load_settings()
    frontend_name = args.frontend if args.frontend is not None else settings.frontend
    explain_errors = args.explain_errors or settings.explain_errors

    # Get frontend
    try:
        frontend = get_frontend(frontend_name)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print(f"English Compiler REPL [{frontend.get_model_name()}]")
    print("Type English pseudocode to compile and run.")
    print("Exit: 'exit', ':q', or just say goodbye naturally")
    print()

    while True:
        try:
            source_text = input(">>> ").strip()

            if not source_text:
                continue

            # Check for exit (built-in commands + LLM classification)
            if _is_exit_command(source_text, frontend):
                print("Goodbye!")
                break

            # Compile
            try:
                doc = frontend.generate_coreil_from_text(source_text)
            except RuntimeError as exc:
                print(f"Compilation error: {exc}")
                continue

            # Validate
            errors = validate_coreil(doc)
            if errors:
                for e in errors:
                    print(f"Error: {e['path']}: {e['message']}")
                continue

            # Execute
            error_callback = None
            if explain_errors:
                error_callback = _make_error_callback(frontend, source_text)

            try:
                run_coreil(doc, error_callback=error_callback)
            except Exception as exc:
                print(f"Runtime error: {exc}")

        except KeyboardInterrupt:
            print("\nInterrupted. Type 'exit' to quit.")
        except EOFError:
            print("\nGoodbye!")
            break

    return 0


def _lint_command(args: argparse.Namespace) -> int:
    """Handle the lint subcommand."""
    from english_compiler.coreil.lint import lint_coreil

    path = Path(args.file)
    try:
        with path.open("r", encoding="utf-8") as handle:
            doc = json.load(handle)
    except OSError as exc:
        print(f"{path}: {exc}")
        return 1
    except json.JSONDecodeError as exc:
        print(f"{path}: invalid json: {exc}")
        return 1

    diagnostics = lint_coreil(doc)

    if not diagnostics:
        print("No lint issues found.")
        return 0

    for d in diagnostics:
        severity = d.get("severity", "warning").upper()
        rule = d.get("rule", "unknown")
        message = d.get("message", "")
        lint_path = d.get("path", "")
        print(f"[{severity}] {lint_path}: {rule} - {message}")

    warning_count = sum(1 for d in diagnostics if d.get("severity") == "warning")
    error_count = sum(1 for d in diagnostics if d.get("severity") == "error")
    print(f"\n{len(diagnostics)} issue(s): {warning_count} warning(s), {error_count} error(s)")

    if args.strict or error_count > 0:
        return 1
    return 0


def _run_lint_on_doc(doc: dict, strict: bool = False) -> int:
    """Run lint on a Core IL document and print results.

    Returns 0 if no issues (or non-strict mode with only warnings), 1 otherwise.
    """
    from english_compiler.coreil.lint import lint_coreil

    diagnostics = lint_coreil(doc)
    if not diagnostics:
        print("Lint: no issues found.")
        return 0

    print("\nLint results:")
    for d in diagnostics:
        severity = d.get("severity", "warning").upper()
        rule = d.get("rule", "unknown")
        message = d.get("message", "")
        lint_path = d.get("path", "")
        print(f"  [{severity}] {lint_path}: {rule} - {message}")

    warning_count = sum(1 for d in diagnostics if d.get("severity") == "warning")
    error_count = sum(1 for d in diagnostics if d.get("severity") == "error")
    print(f"  {len(diagnostics)} issue(s): {warning_count} warning(s), {error_count} error(s)")

    if strict or error_count > 0:
        return 1
    return 0


def _explain_command(args: argparse.Namespace) -> int:
    """Handle the explain subcommand."""
    from english_compiler.explain import explain

    path = Path(args.file)
    try:
        with path.open("r", encoding="utf-8") as handle:
            doc = json.load(handle)
    except OSError as exc:
        print(f"{path}: {exc}")
        return 1
    except json.JSONDecodeError as exc:
        print(f"{path}: invalid json: {exc}")
        return 1

    text = explain(doc, verbose=getattr(args, "verbose", False))
    print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="english-compiler")
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser("compile", help="Compile a source file")
    compile_parser.add_argument("file", help="Path to the source text file")
    compile_parser.add_argument(
        "--frontend",
        choices=["mock", "claude", "openai", "gemini", "qwen"],
        default=None,
        help="Frontend to use (default: auto-detect based on available API keys)",
    )
    compile_parser.add_argument(
        "--target",
        choices=["coreil", "python", "javascript", "cpp", "rust", "go", "wasm"],
        default=None,
        help="Compilation target (default: coreil)",
    )
    compile_parser.add_argument("--regen", action="store_true", help="Force regeneration")
    compile_parser.add_argument(
        "--freeze",
        action="store_true",
        help="Fail if regeneration would be required",
    )
    compile_parser.add_argument(
        "--experimental",
        action="store_true",
        help="EXPERIMENTAL: Compile directly to target without Core IL (non-deterministic)",
    )
    compile_parser.add_argument(
        "--explain-errors",
        action="store_true",
        help="Use LLM to explain runtime errors in user-friendly terms",
    )
    compile_parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Watch file/directory for changes and recompile automatically",
    )
    compile_parser.add_argument(
        "--lint",
        action="store_true",
        help="Run static analysis after compilation",
    )
    compile_parser.add_argument(
        "--optimize",
        action="store_true",
        help="Run optimization pass on Core IL before codegen",
    )
    compile_parser.set_defaults(func=_compile_command)

    run_parser = subparsers.add_parser("run", help="Run a Core IL file")
    run_parser.add_argument("file", help="Path to the Core IL JSON file")
    run_parser.add_argument(
        "--explain-errors",
        action="store_true",
        help="Use LLM to explain runtime errors in user-friendly terms",
    )
    run_parser.add_argument(
        "--frontend",
        choices=["mock", "claude", "openai", "gemini", "qwen"],
        default=None,
        help="Frontend to use for error explanation (default: auto-detect)",
    )
    run_parser.set_defaults(func=_run_command)

    # Config subcommand
    config_parser = subparsers.add_parser("config", help="Manage configuration settings")
    config_subparsers = config_parser.add_subparsers(dest="config_action")

    # config set
    config_set_parser = config_subparsers.add_parser(
        "set", help="Set a configuration value"
    )
    config_set_parser.add_argument(
        "key",
        help="Setting name (frontend, explain-errors)",
    )
    config_set_parser.add_argument(
        "value",
        help="Value to set",
    )

    # config get
    config_get_parser = config_subparsers.add_parser(
        "get", help="Get a configuration value"
    )
    config_get_parser.add_argument(
        "key",
        help="Setting name (frontend, explain-errors)",
    )

    # config list
    config_subparsers.add_parser("list", help="List all configuration values")

    # config path
    config_subparsers.add_parser("path", help="Show configuration file path")

    # config reset
    config_subparsers.add_parser("reset", help="Delete configuration file")

    config_parser.set_defaults(func=_config_command)

    # REPL subcommand
    repl_parser = subparsers.add_parser("repl", help="Interactive REPL mode")
    repl_parser.add_argument(
        "--frontend",
        choices=["mock", "claude", "openai", "gemini", "qwen"],
        default=None,
        help="Frontend to use (default: auto-detect based on available API keys)",
    )
    repl_parser.add_argument(
        "--explain-errors",
        action="store_true",
        help="Use LLM to explain runtime errors in user-friendly terms",
    )
    repl_parser.set_defaults(func=_repl_command)

    # Explain subcommand
    explain_parser = subparsers.add_parser("explain", help="Explain a Core IL program in English")
    explain_parser.add_argument("file", help="Path to the Core IL JSON file")
    explain_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Produce more detailed explanations",
    )
    explain_parser.set_defaults(func=_explain_command)

    # Lint subcommand
    lint_parser = subparsers.add_parser("lint", help="Run static analysis on a Core IL file")
    lint_parser.add_argument("file", help="Path to the Core IL JSON file")
    lint_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (exit 1 if any found)",
    )
    lint_parser.set_defaults(func=_lint_command)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

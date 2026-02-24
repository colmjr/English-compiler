"""CLI entry point for english_compiler."""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

from english_compiler import __version__
from english_compiler.cli.config_flow import config_command as _config_command
from english_compiler.cli.emit_helpers import (
    emit_target_code as _emit_target_code,
)
from english_compiler.cli.emit_helpers import (
    is_tier2_unsupported_error as _is_tier2_unsupported_error,
)
from english_compiler.cli.emit_helpers import (
    run_tier2_fallback as _run_tier2_fallback,
)
from english_compiler.cli.io_utils import (
    generate_code_header as _generate_code_header,
)
from english_compiler.cli.io_utils import (
    get_experimental_output_path as _get_experimental_output_path,
)
from english_compiler.cli.io_utils import (
    get_output_path as _get_output_path,
)
from english_compiler.cli.io_utils import (
    load_json as _load_json,
)
from english_compiler.cli.io_utils import (
    print_ambiguities as _print_ambiguities,
)
from english_compiler.cli.io_utils import (
    print_experimental_warning as _print_experimental_warning,
)
from english_compiler.cli.io_utils import (
    print_validation_errors as _print_validation_errors,
)
from english_compiler.cli.io_utils import (
    sha256_bytes as _sha256_bytes,
)
from english_compiler.cli.io_utils import (
    sha256_file as _sha256_file,
)
from english_compiler.cli.io_utils import (
    write_json as _write_json,
)
from english_compiler.cli.lint_flow import (
    lint_command as _lint_command,
)
from english_compiler.cli.lint_flow import (
    run_lint_on_doc as _run_lint_on_doc,
)
from english_compiler.cli.run_targets import (
    run_cpp_file as _run_cpp_file,
)
from english_compiler.cli.run_targets import (
    run_javascript_file as _run_javascript_file,
)
from english_compiler.cli.run_targets import (
    run_python_file as _run_python_file,
)
from english_compiler.cli.run_targets import (
    run_rust_file as _run_rust_file,
)
from english_compiler.settings import load_settings

# Built-in exit commands (instant, no API call)
BUILTIN_EXIT_COMMANDS = {"exit", "quit", ":q", ":quit", ":exit"}
TIER2_FALLBACK_TARGETS = ("python", "javascript", "cpp", "rust")


def _run_experimental_target(target: str, output_path: Path) -> int:
    runners = {
        "python": _run_python_file,
        "javascript": _run_javascript_file,
        "cpp": _run_cpp_file,
    }
    runner = runners.get(target)
    if runner is None:
        return 0
    return runner(output_path)


def _process_compiled_doc(
    args: argparse.Namespace,
    doc: dict,
    source_path: Path,
    coreil_path: Path,
    run_coreil,
    error_callback,
    *,
    check_freshness: bool,
) -> int:
    """Run optimize/lint/emit/execute flow for a compiled Core IL document."""
    if getattr(args, "optimize", False):
        from english_compiler.coreil.optimize import optimize

        doc = optimize(doc)
        print("Applied optimization pass")

    if getattr(args, "lint", False):
        lint_rc = _run_lint_on_doc(doc)
        if lint_rc != 0:
            return lint_rc

    target = getattr(args, "target", "coreil")
    if not _emit_target_code(
        doc,
        source_path,
        coreil_path,
        target,
        check_freshness=check_freshness,
    ):
        return 1

    ambiguities = doc.get("ambiguities", [])
    if isinstance(ambiguities, list) and ambiguities:
        _print_ambiguities(ambiguities)
        return 2

    try:
        return run_coreil(
            doc, error_callback=error_callback, base_dir=coreil_path.parent
        )
    except ValueError as exc:
        if _is_tier2_unsupported_error(exc):
            fallback_rc = _run_tier2_fallback(
                source_path,
                target,
                supported_targets=TIER2_FALLBACK_TARGETS,
            )
            if fallback_rc is not None:
                return fallback_rc
        raise


def _load_json_doc(path: Path) -> tuple[object | None, bool]:
    """Load a JSON file with consistent error reporting."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), True
    except OSError as exc:
        print(f"{path}: {exc}")
    except json.JSONDecodeError as exc:
        print(f"{path}: invalid json: {exc}")
    return None, False


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

        print(
            f"Generating {target} code for {source_path} using {frontend.get_model_name()}"
        )

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
    return _run_experimental_target(target, output_path)


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
        return _process_compiled_doc(
            args,
            doc,
            source_path,
            coreil_path,
            run_coreil,
            error_callback,
            check_freshness=True,
        )

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

    lock_doc = {
        "source_sha256": source_sha256,
        "coreil_sha256": _sha256_file(coreil_path),
        "model": model_name,
        "system_prompt_version": "dev",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    if not _write_json(lock_path, lock_doc):
        return 1

    return _process_compiled_doc(
        args,
        doc,
        source_path,
        coreil_path,
        run_coreil,
        error_callback,
        check_freshness=False,
    )


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
    doc, ok = _load_json_doc(path)
    if not ok:
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

    return run_coreil(doc, error_callback=error_callback, base_dir=path.parent)


def _debug_command(args: argparse.Namespace) -> int:
    """Handle the debug subcommand."""
    from english_compiler.coreil.debug import debug_coreil

    path = Path(args.file)
    doc, ok = _load_json_doc(path)
    if not ok:
        return 1

    return debug_coreil(doc)


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


def _explain_command(args: argparse.Namespace) -> int:
    """Handle the explain subcommand."""
    from english_compiler.explain import explain

    path = Path(args.file)
    doc, ok = _load_json_doc(path)
    if not ok:
        return 1

    text = explain(doc, verbose=getattr(args, "verbose", False))
    print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="english-compiler")
    parser.add_argument(
        "--version",
        "-V",
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
    compile_parser.add_argument(
        "--regen", action="store_true", help="Force regeneration"
    )
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
        "--watch",
        "-w",
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
    config_parser = subparsers.add_parser(
        "config", help="Manage configuration settings"
    )
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
    explain_parser = subparsers.add_parser(
        "explain", help="Explain a Core IL program in English"
    )
    explain_parser.add_argument("file", help="Path to the Core IL JSON file")
    explain_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Produce more detailed explanations",
    )
    explain_parser.set_defaults(func=_explain_command)

    # Lint subcommand
    lint_parser = subparsers.add_parser(
        "lint", help="Run static analysis on a Core IL file"
    )
    lint_parser.add_argument("file", help="Path to the Core IL JSON file")
    lint_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (exit 1 if any found)",
    )
    lint_parser.set_defaults(func=_lint_command)

    # Debug subcommand
    debug_parser = subparsers.add_parser(
        "debug", help="Debug a Core IL file interactively"
    )
    debug_parser.add_argument("file", help="Path to the Core IL JSON file")
    debug_parser.set_defaults(func=_debug_command)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

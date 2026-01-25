"""CLI entry point for english_compiler."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any


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


def _run_python_file(python_path: Path) -> int:
    """Run a Python file and return exit code."""
    import subprocess
    import sys
    result = subprocess.run([sys.executable, str(python_path)], capture_output=False)
    return result.returncode


def _compile_command(args: argparse.Namespace) -> int:
    from english_compiler.coreil.emit import emit_python
    from english_compiler.coreil.interp import run_coreil
    from english_compiler.coreil.validate import validate_coreil
    from english_compiler.frontend import get_frontend

    if args.regen and args.freeze:
        print("--regen and --freeze cannot be used together")
        return 1

    source_path = Path(args.file)
    coreil_path = source_path.with_suffix(".coreil.json")
    lock_path = source_path.with_suffix(".lock.json")

    try:
        source_text = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"{source_path}: {exc}")
        return 1

    source_sha256 = _sha256_bytes(source_text.encode("utf-8"))

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

        # Emit Python code if target is "python" (even when using cache)
        target = getattr(args, "target", "coreil")
        if target == "python":
            python_path = source_path.with_suffix(".py")
            # Only regenerate Python if it doesn't exist or is older than Core IL
            if not python_path.exists() or python_path.stat().st_mtime < coreil_path.stat().st_mtime:
                try:
                    python_code = emit_python(doc)
                    python_path.write_text(python_code, encoding="utf-8")
                    print(f"Generated Python code at {python_path}")
                except OSError as exc:
                    print(f"{python_path}: {exc}")
                    return 1
                except Exception as exc:
                    print(f"Python codegen failed: {exc}")
                    return 1

        ambiguities = doc.get("ambiguities", [])
        if isinstance(ambiguities, list) and ambiguities:
            _print_ambiguities(ambiguities)
            return 2

        # Try interpreter first, fall back to Python for ExternalCall
        try:
            return run_coreil(doc)
        except ValueError as exc:
            if "ExternalCall" in str(exc) and target == "python":
                python_path = source_path.with_suffix(".py")
                print(f"Note: ExternalCall not supported in interpreter, running {python_path}")
                return _run_python_file(python_path)
            raise

    if args.freeze:
        print(f"freeze enabled: regeneration required for {source_path}")
        return 1

    # Get frontend (auto-detect if not specified)
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

    # Emit Python code if target is "python"
    target = getattr(args, "target", "coreil")
    if target == "python":
        python_path = source_path.with_suffix(".py")
        try:
            python_code = emit_python(doc)
            python_path.write_text(python_code, encoding="utf-8")
            print(f"Generated Python code at {python_path}")
        except OSError as exc:
            print(f"{python_path}: {exc}")
            return 1
        except Exception as exc:
            print(f"Python codegen failed: {exc}")
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

    # Try interpreter first, fall back to Python for ExternalCall
    try:
        return run_coreil(doc)
    except ValueError as exc:
        if "ExternalCall" in str(exc) and target == "python":
            python_path = source_path.with_suffix(".py")
            print(f"Note: ExternalCall not supported in interpreter, running {python_path}")
            return _run_python_file(python_path)
        raise


def _run_command(args: argparse.Namespace) -> int:
    from english_compiler.coreil.interp import run_coreil

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

    return run_coreil(doc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="english-compiler")
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
        choices=["coreil", "python"],
        default="coreil",
        help="Compilation target (default: coreil)",
    )
    compile_parser.add_argument("--regen", action="store_true", help="Force regeneration")
    compile_parser.add_argument(
        "--freeze",
        action="store_true",
        help="Fail if regeneration would be required",
    )
    compile_parser.set_defaults(func=_compile_command)

    run_parser = subparsers.add_parser("run", help="Run a Core IL file")
    run_parser.add_argument("file", help="Path to the Core IL JSON file")
    run_parser.set_defaults(func=_run_command)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

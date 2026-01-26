"""CLI entry point for english_compiler."""

from __future__ import annotations

import argparse

from english_compiler import __version__
import datetime
import hashlib
import json
from pathlib import Path


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


def _run_javascript_file(js_path: Path) -> int:
    """Run a JavaScript file with Node.js and return exit code."""
    import subprocess
    result = subprocess.run(["node", str(js_path)], capture_output=False)
    return result.returncode


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
        output_path = source_path.with_suffix(".py")
        lang_name = "Python"
        emit_func = emit_python
    elif target == "javascript":
        output_path = source_path.with_suffix(".js")
        lang_name = "JavaScript"
        emit_func = emit_javascript
    elif target == "cpp":
        output_path = source_path.with_suffix(".cpp")
        lang_name = "C++"
        emit_func = emit_cpp
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
    as_path = source_path.with_suffix(".as.ts")

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
            source_path.parent,
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


def _compile_command(args: argparse.Namespace) -> int:
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
            return run_coreil(doc)
        except ValueError as exc:
            if "ExternalCall" in str(exc):
                if target == "python":
                    python_path = source_path.with_suffix(".py")
                    print(f"Note: ExternalCall not supported in interpreter, running {python_path}")
                    return _run_python_file(python_path)
                elif target == "javascript":
                    js_path = source_path.with_suffix(".js")
                    print(f"Note: ExternalCall not supported in interpreter, running {js_path}")
                    return _run_javascript_file(js_path)
                elif target == "cpp":
                    cpp_path = source_path.with_suffix(".cpp")
                    print(f"Note: ExternalCall not supported in interpreter, running {cpp_path}")
                    return _run_cpp_file(cpp_path)
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

    # Try interpreter first, fall back to generated code for ExternalCall
    try:
        return run_coreil(doc)
    except ValueError as exc:
        if "ExternalCall" in str(exc):
            if target == "python":
                python_path = source_path.with_suffix(".py")
                print(f"Note: ExternalCall not supported in interpreter, running {python_path}")
                return _run_python_file(python_path)
            elif target == "javascript":
                js_path = source_path.with_suffix(".js")
                print(f"Note: ExternalCall not supported in interpreter, running {js_path}")
                return _run_javascript_file(js_path)
            elif target == "cpp":
                cpp_path = source_path.with_suffix(".cpp")
                print(f"Note: ExternalCall not supported in interpreter, running {cpp_path}")
                return _run_cpp_file(cpp_path)
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
        choices=["coreil", "python", "javascript", "cpp", "wasm"],
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

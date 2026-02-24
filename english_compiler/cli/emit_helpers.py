"""CLI helpers for code emission and tier-2 runtime fallbacks."""

from __future__ import annotations

from pathlib import Path

from english_compiler.cli.io_utils import get_output_path, write_json
from english_compiler.cli.run_targets import (
    run_cpp_file,
    run_javascript_file,
    run_python_file,
    run_rust_file,
)

TIER2_FALLBACK_ERROR_MARKERS = ("ExternalCall", "MethodCall", "PropertyGet")


def is_tier2_unsupported_error(exc: ValueError) -> bool:
    message = str(exc)
    return any(marker in message for marker in TIER2_FALLBACK_ERROR_MARKERS)


def run_tier2_fallback(
    source_path: Path,
    target: str,
    supported_targets: tuple[str, ...],
) -> int | None:
    fallback_specs = {
        "python": ("py", ".py", run_python_file),
        "javascript": ("js", ".js", run_javascript_file),
        "cpp": ("cpp", ".cpp", run_cpp_file),
        "rust": ("rust", ".rs", run_rust_file),
    }

    spec = fallback_specs.get(target)
    if target not in supported_targets or spec is None:
        return None

    subdir, suffix, runner = spec
    output_path = get_output_path(source_path, subdir, suffix)
    print(f"Note: Tier 2 operation not supported in interpreter, running {output_path}")
    return runner(output_path)


def emit_target_code(
    doc: dict,
    source_path: Path,
    coreil_path: Path,
    target: str,
    check_freshness: bool = False,
) -> bool:
    """Emit code for the specified target."""
    if target in ("coreil", ""):
        return True

    import shutil

    from english_compiler.coreil.emit import emit_python
    from english_compiler.coreil.emit_cpp import (
        emit_cpp,
        get_json_header_path,
        get_runtime_header_path,
    )
    from english_compiler.coreil.emit_javascript import emit_javascript

    if target == "wasm":
        return emit_wasm_target(doc, source_path, coreil_path, check_freshness)

    def copy_cpp_runtime(runtime_dir: Path) -> None:
        shutil.copy(get_runtime_header_path(), runtime_dir / "coreil_runtime.hpp")
        shutil.copy(get_json_header_path(), runtime_dir / "json.hpp")

    target_specs: dict[str, tuple[str, str, str, object, object | None]] = {
        "python": ("py", ".py", "Python", emit_python, None),
        "javascript": ("js", ".js", "JavaScript", emit_javascript, None),
        "cpp": ("cpp", ".cpp", "C++", emit_cpp, copy_cpp_runtime),
    }

    if target == "rust":
        from english_compiler.coreil.emit_rust import (
            emit_rust,
        )
        from english_compiler.coreil.emit_rust import (
            get_runtime_path as get_rust_runtime_path,
        )

        def copy_rust_runtime(runtime_dir: Path) -> None:
            shutil.copy(get_rust_runtime_path(), runtime_dir / "coreil_runtime.rs")

        target_specs["rust"] = ("rust", ".rs", "Rust", emit_rust, copy_rust_runtime)

    if target == "go":
        from english_compiler.coreil.emit_go import (
            emit_go,
        )
        from english_compiler.coreil.emit_go import (
            get_runtime_path as get_go_runtime_path,
        )

        def copy_go_runtime(runtime_dir: Path) -> None:
            shutil.copy(get_go_runtime_path(), runtime_dir / "coreil_runtime.go")

        target_specs["go"] = ("go", ".go", "Go", emit_go, copy_go_runtime)

    target_spec = target_specs.get(target)
    if target_spec is None:
        return True

    subdir, suffix, lang_name, emit_func, runtime_copy_func = target_spec
    output_path = get_output_path(source_path, subdir, suffix)

    if check_freshness and output_path.exists():
        if output_path.stat().st_mtime >= coreil_path.stat().st_mtime:
            return True

    try:
        code, coreil_line_map = emit_func(doc)
        output_path.write_text(code, encoding="utf-8")
        print(f"Generated {lang_name} code at {output_path}")

        english_to_coreil = doc.get("source_map")
        if english_to_coreil is not None:
            from english_compiler.coreil.source_map import compose_source_maps

            english_to_target = compose_source_maps(english_to_coreil, coreil_line_map)
            coreil_to_target_str = {str(k): v for k, v in coreil_line_map.items()}
            source_map_data = {
                "english_to_coreil": english_to_coreil,
                "coreil_to_target": coreil_to_target_str,
                "english_to_target": english_to_target,
            }
            source_map_path = output_path.with_suffix(".sourcemap.json")
            write_json(source_map_path, source_map_data)
            print(f"Generated source map at {source_map_path}")

        if runtime_copy_func is not None:
            runtime_copy_func(output_path.parent)

    except OSError as exc:
        print(f"{output_path}: {exc}")
        return False
    except (ValueError, TypeError, KeyError) as exc:
        print(f"{lang_name} codegen failed: {exc}")
        return False

    return True


def emit_wasm_target(
    doc: dict,
    source_path: Path,
    coreil_path: Path,
    check_freshness: bool = False,
) -> bool:
    """Emit AssemblyScript code and optionally compile to WASM."""
    import shutil

    from english_compiler.coreil.emit_assemblyscript import (
        emit_assemblyscript,
        get_runtime_path,
    )
    from english_compiler.coreil.wasm_build import ASC_AVAILABLE, compile_to_wasm

    as_path = get_output_path(source_path, "wasm", ".as.ts")

    if check_freshness and as_path.exists():
        if as_path.stat().st_mtime >= coreil_path.stat().st_mtime:
            return True

    try:
        code, _line_map = emit_assemblyscript(doc)
        as_path.write_text(code, encoding="utf-8")
        print(f"Generated AssemblyScript code at {as_path}")

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

    if ASC_AVAILABLE:
        result = compile_to_wasm(
            code,
            as_path.parent,
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

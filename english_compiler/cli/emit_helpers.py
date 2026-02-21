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
    if target not in supported_targets:
        return None

    if target == "python":
        python_path = get_output_path(source_path, "py", ".py")
        print(f"Note: Tier 2 operation not supported in interpreter, running {python_path}")
        return run_python_file(python_path)

    if target == "javascript":
        js_path = get_output_path(source_path, "js", ".js")
        print(f"Note: Tier 2 operation not supported in interpreter, running {js_path}")
        return run_javascript_file(js_path)

    if target == "cpp":
        cpp_path = get_output_path(source_path, "cpp", ".cpp")
        print(f"Note: Tier 2 operation not supported in interpreter, running {cpp_path}")
        return run_cpp_file(cpp_path)

    if target == "rust":
        rust_path = get_output_path(source_path, "rust", ".rs")
        print(f"Note: Tier 2 operation not supported in interpreter, running {rust_path}")
        return run_rust_file(rust_path)

    return None


def emit_target_code(
    doc: dict,
    source_path: Path,
    coreil_path: Path,
    target: str,
    check_freshness: bool = False,
) -> bool:
    """Emit code for the specified target."""
    if target == "coreil":
        return True

    import shutil

    from english_compiler.coreil.emit import emit_python
    from english_compiler.coreil.emit_cpp import (
        emit_cpp,
        get_json_header_path,
        get_runtime_header_path,
    )
    from english_compiler.coreil.emit_javascript import emit_javascript

    if target == "python":
        output_path = get_output_path(source_path, "py", ".py")
        lang_name = "Python"
        emit_func = emit_python
    elif target == "javascript":
        output_path = get_output_path(source_path, "js", ".js")
        lang_name = "JavaScript"
        emit_func = emit_javascript
    elif target == "cpp":
        output_path = get_output_path(source_path, "cpp", ".cpp")
        lang_name = "C++"
        emit_func = emit_cpp
    elif target == "rust":
        from english_compiler.coreil.emit_rust import (
            emit_rust,
            get_runtime_path as get_rust_runtime_path,
        )

        output_path = get_output_path(source_path, "rust", ".rs")
        lang_name = "Rust"
        emit_func = emit_rust
    elif target == "go":
        from english_compiler.coreil.emit_go import (
            emit_go,
            get_runtime_path as get_go_runtime_path,
        )

        output_path = get_output_path(source_path, "go", ".go")
        lang_name = "Go"
        emit_func = emit_go
    elif target == "wasm":
        return emit_wasm_target(doc, source_path, coreil_path, check_freshness)
    else:
        return True

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

        if target == "cpp":
            runtime_dir = output_path.parent
            shutil.copy(get_runtime_header_path(), runtime_dir / "coreil_runtime.hpp")
            shutil.copy(get_json_header_path(), runtime_dir / "json.hpp")

        if target == "rust":
            runtime_dir = output_path.parent
            shutil.copy(get_rust_runtime_path(), runtime_dir / "coreil_runtime.rs")

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


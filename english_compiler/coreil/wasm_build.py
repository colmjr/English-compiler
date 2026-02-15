"""WASM build helper for Core IL.

This module provides utilities for compiling AssemblyScript to WebAssembly.

Usage:
    from english_compiler.coreil.wasm_build import compile_to_wasm, ASC_AVAILABLE

    if ASC_AVAILABLE:
        result = compile_to_wasm(as_code, output_path)
        if result.success:
            print(f"Compiled to {result.wasm_path}")
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


# Check if AssemblyScript compiler is available
ASC_AVAILABLE = shutil.which("asc") is not None


def get_runtime_path() -> Path:
    """Return path to the AssemblyScript runtime library."""
    return Path(__file__).parent / "wasm_runtime" / "coreil_runtime.ts"


@dataclass
class CompileResult:
    """Result from WASM compilation."""
    success: bool
    wasm_path: Path | None = None
    wat_path: Path | None = None
    error: str | None = None


def compile_to_wasm(
    as_code: str,
    output_dir: Path,
    name: str = "program",
    *,
    emit_wat: bool = False,
    optimize: bool = True,
) -> CompileResult:
    """Compile AssemblyScript code to WebAssembly.

    Args:
        as_code: AssemblyScript source code.
        output_dir: Directory to write output files.
        name: Base name for output files (default: "program").
        emit_wat: Also emit WAT text format (default: False).
        optimize: Enable optimization (default: True).

    Returns:
        CompileResult with paths to generated files.
    """
    if not ASC_AVAILABLE:
        return CompileResult(
            success=False,
            error="AssemblyScript compiler (asc) not found. Install with: npm install -g assemblyscript",
        )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create temp directory for compilation
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Write source file
        src_path = tmp_path / f"{name}.ts"
        src_path.write_text(as_code, encoding="utf-8")

        # Copy runtime library
        runtime_src = get_runtime_path()
        runtime_dst = tmp_path / "coreil_runtime.ts"
        shutil.copy(runtime_src, runtime_dst)

        # Build command
        wasm_path = output_dir / f"{name}.wasm"
        cmd = [
            "asc",
            str(src_path),
            "-o", str(wasm_path),
            "--runtime", "stub",  # Use stub runtime (smaller output)
            "--exportStart", "main",  # Export main function
        ]

        if optimize:
            cmd.extend(["-O3"])
        else:
            cmd.extend(["--debug"])

        if emit_wat:
            wat_path = output_dir / f"{name}.wat"
            cmd.extend(["-t", str(wat_path)])
        else:
            wat_path = None

        # Run compiler
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return CompileResult(
                success=False,
                error="Compilation timeout (>60s)",
            )
        except Exception as exc:
            return CompileResult(
                success=False,
                error=f"Compilation error: {exc}",
            )

        if result.returncode != 0:
            return CompileResult(
                success=False,
                error=f"asc failed:\n{result.stderr}",
            )

        return CompileResult(
            success=True,
            wasm_path=wasm_path,
            wat_path=wat_path,
        )


def run_wasm(wasm_path: Path, timeout: int = 10) -> tuple[str, int]:
    """Run a WebAssembly file using Node.js.

    Properly decodes AssemblyScript strings from WASM linear memory
    using the AS string format (length-prefixed UTF-16LE).

    Args:
        wasm_path: Path to the .wasm file.
        timeout: Maximum execution time in seconds.

    Returns:
        Tuple of (stdout output, exit code).
    """
    if not shutil.which("node"):
        return ("Node.js not available", 1)

    # Create a Node.js wrapper that properly reads AS strings from WASM memory.
    # AssemblyScript strings in memory have this layout:
    #   ptr - 4 bytes: string byte length (UTF-16LE)
    #   ptr onwards: UTF-16LE encoded characters
    runner_code = f'''
const fs = require('fs');

// Read an AssemblyScript string from WASM linear memory.
// AS strings are stored as: [4-byte byte-length at ptr-4][UTF-16LE data at ptr]
function readASString(memory, ptr) {{
    if (ptr === 0) return "";
    const buffer = new Uint8Array(memory.buffer);
    // The 4 bytes before the pointer contain the byte length
    const byteLength = (
        buffer[ptr - 4] |
        (buffer[ptr - 3] << 8) |
        (buffer[ptr - 2] << 16) |
        (buffer[ptr - 1] << 24)
    ) >>> 0;
    if (byteLength === 0) return "";
    const u16 = new Uint16Array(memory.buffer, ptr, byteLength >> 1);
    return String.fromCharCode(...u16);
}}

let memory;

const importObject = {{
    env: {{
        print: (ptr) => {{
            console.log(readASString(memory, ptr));
        }},
        abort: (msgPtr, filePtr, line, col) => {{
            const msg = msgPtr ? readASString(memory, msgPtr) : "unknown";
            console.error("abort: " + msg + " at line " + line);
            process.exit(1);
        }},
    }},
}};

async function run() {{
    const wasmBuffer = fs.readFileSync('{wasm_path}');
    const {{ instance }} = await WebAssembly.instantiate(wasmBuffer, importObject);

    memory = instance.exports.memory;

    // Call _start or main if exported
    if (instance.exports._start) {{
        instance.exports._start();
    }} else if (instance.exports.main) {{
        instance.exports.main();
    }}
}}

run().catch(err => {{
    console.error(err.message || err);
    process.exit(1);
}});
'''

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".js",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(runner_code)
        runner_path = tmp.name

    try:
        result = subprocess.run(
            ["node", runner_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return (result.stdout, result.returncode)
    except subprocess.TimeoutExpired:
        return ("Execution timeout", 1)
    except Exception as exc:
        return (str(exc), 1)
    finally:
        Path(runner_path).unlink(missing_ok=True)

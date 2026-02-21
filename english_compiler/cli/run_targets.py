"""CLI helpers for executing generated target programs."""

from __future__ import annotations

from pathlib import Path


def run_python_file(python_path: Path) -> int:
    """Run a Python file and return exit code."""
    import subprocess
    import sys

    result = subprocess.run([sys.executable, str(python_path)], capture_output=False)
    return result.returncode


def run_javascript_file(js_path: Path) -> int:
    """Run a JavaScript file with Node.js and return exit code."""
    import subprocess

    result = subprocess.run(["node", str(js_path)], capture_output=False)
    return result.returncode


def run_rust_file(rust_path: Path) -> int:
    """Compile and run a Rust file and return exit code."""
    import shutil
    import subprocess
    import tempfile

    compiler = shutil.which("rustc")
    if compiler is None:
        print("Error: rustc not found")
        return 1

    with tempfile.NamedTemporaryFile(suffix="", delete=False) as tmp:
        exe_path = tmp.name

    try:
        from english_compiler.coreil.emit_rust import get_runtime_path

        runtime_dst = rust_path.parent / "coreil_runtime.rs"
        shutil.copy(get_runtime_path(), runtime_dst)

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


def run_cpp_file(cpp_path: Path) -> int:
    """Compile and run a C++ file and return exit code."""
    import shutil
    import subprocess
    import tempfile

    compiler = None
    for cc in ["g++", "clang++"]:
        if shutil.which(cc):
            compiler = cc
            break

    if compiler is None:
        print("Error: No C++ compiler found (tried g++, clang++)")
        return 1

    with tempfile.NamedTemporaryFile(suffix="", delete=False) as tmp:
        exe_path = tmp.name

    try:
        from english_compiler.coreil.emit_cpp import get_runtime_header_path

        include_dir = get_runtime_header_path().parent
        compile_result = subprocess.run(
            [
                compiler,
                "-std=c++17",
                "-O2",
                "-I",
                str(include_dir),
                str(cpp_path),
                "-o",
                exe_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if compile_result.returncode != 0:
            print(f"C++ compilation failed:\n{compile_result.stderr}")
            return 1

        result = subprocess.run([exe_path], capture_output=False, timeout=30)
        return result.returncode

    except subprocess.TimeoutExpired:
        print("C++ execution timeout")
        return 1
    finally:
        Path(exe_path).unlink(missing_ok=True)


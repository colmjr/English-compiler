"""Watch mode for automatic recompilation on file changes."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Callable


def is_watchfiles_available() -> bool:
    """Check if the watchfiles library is installed."""
    try:
        import watchfiles  # noqa: F401
        return True
    except ImportError:
        return False


def watch_and_compile(
    path: Path,
    compile_func: Callable[[Path], int],
    file_filter: str = "*.txt",
) -> int:
    """Watch a file or directory and recompile on changes.

    Args:
        path: Path to file or directory to watch.
        compile_func: Function to call with the file path when changes detected.
        file_filter: Glob pattern for files to watch in directory mode.

    Returns:
        Exit code (0 for normal exit, 1 for error).
    """
    try:
        from watchfiles import watch, Change
    except ImportError:
        print("Error: watchfiles is not installed.")
        print("Install it with: pip install english-compiler[watch]")
        return 1

    path = path.resolve()
    is_directory = path.is_dir()

    if is_directory:
        print(f"Watching directory: {path} for {file_filter} files")
        watch_path = path
    else:
        print(f"Watching file: {path}")
        watch_path = path.parent

    print("Press Ctrl+C to stop watching")
    print("-" * 50)
    print()

    # Do initial compilation
    if is_directory:
        # Find first matching file for initial compilation
        files = list(path.glob(file_filter))
        if files:
            _run_compile(files[0], compile_func)
    else:
        _run_compile(path, compile_func)

    try:
        for changes in watch(watch_path, debounce=1600, recursive=False):
            for change_type, changed_path in changes:
                changed_path = Path(changed_path)

                # Skip if not a modification
                if change_type != Change.modified:
                    continue

                # In file mode, only react to the specific file
                if not is_directory:
                    if changed_path != path:
                        continue
                    _run_compile(path, compile_func)
                else:
                    # In directory mode, check if file matches filter
                    if not changed_path.match(file_filter):
                        continue
                    _run_compile(changed_path, compile_func)

    except KeyboardInterrupt:
        print()
        print("Stopped watching.")
        return 0

    return 0


def _run_compile(file_path: Path, compile_func: Callable[[Path], int]) -> None:
    """Run compilation for a single file with formatted output."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] Compiling: {file_path.name}")
    print("-" * 50)

    try:
        exit_code = compile_func(file_path)
        print("-" * 50)
        if exit_code == 0:
            print(f"[{timestamp}] Compilation successful")
        elif exit_code == 2:
            print(f"[{timestamp}] Compilation completed with ambiguities")
        else:
            print(f"[{timestamp}] Compilation failed (exit code: {exit_code})")
    except Exception as exc:
        print("-" * 50)
        print(f"[{timestamp}] Compilation error: {exc}")

    print()

"""CLI helpers for JSON I/O, hashing, and output path management."""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path


def print_validation_errors(errors: list[dict]) -> None:
    for error in errors:
        print(f"{error['path']}: {error['message']}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def write_json(path: Path, data: dict) -> bool:
    try:
        path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        print(f"{path}: {exc}")
        return False
    return True


def get_output_path(source_path: Path, subdir: str, suffix: str) -> Path:
    """Get output path in organized directory structure."""
    output_dir = source_path.parent / "output" / subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / (source_path.stem + suffix)


def print_ambiguities(ambiguities: list[dict]) -> None:
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


def print_experimental_warning() -> None:
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


def get_experimental_output_path(source_path: Path, target: str, suffix: str) -> Path:
    """Get output path for experimental mode."""
    subdir_map = {"python": "py", "javascript": "js", "cpp": "cpp"}
    subdir = subdir_map.get(target, target)
    output_dir = source_path.parent / "output" / "experimental" / subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / (source_path.stem + suffix)


def generate_code_header(model_name: str, target: str) -> str:
    """Generate warning header for experimental code."""
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


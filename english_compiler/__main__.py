"""CLI entry point for english_compiler."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
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
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"{path}: {exc}")
        return False
    return True


def _compile_command(args: argparse.Namespace) -> int:
    from english_compiler.coreil.interp import run_coreil
    from english_compiler.frontend.mock_llm import generate_coreil_from_text
    from englishc.coreil.validate import validate_coreil

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
        return run_coreil(doc)

    if args.freeze:
        print(f"freeze enabled: regeneration required for {source_path}")
        return 1

    print(f"Regenerating Core IL for {source_path}")
    doc = generate_coreil_from_text(source_text)
    errors = validate_coreil(doc)
    if errors:
        _print_validation_errors(errors)
        return 1

    if not _write_json(coreil_path, doc):
        return 1

    lock_doc = {
        "source_sha256": source_sha256,
        "coreil_sha256": _sha256_file(coreil_path),
        "model": "mock",
        "system_prompt_version": "dev",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    if not _write_json(lock_path, lock_doc):
        return 1

    return run_coreil(doc)


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
    parser = argparse.ArgumentParser(prog="english_compiler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser("compile", help="Compile a source file")
    compile_parser.add_argument("file", help="Path to the source text file")
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

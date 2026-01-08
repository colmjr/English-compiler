"""CLI entry point for englishc."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _compile_command(args: argparse.Namespace) -> int:
    filename = args.file
    print(f"Compiling {filename}...")
    return 0


def _validate_command(args: argparse.Namespace) -> int:
    from englishc.coreil.validate import validate_coreil

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

    errors = validate_coreil(doc)
    if errors:
        for error in errors:
            print(f\"{error['path']}: {error['message']}\")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="englishc")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser("compile", help="Compile a file")
    compile_parser.add_argument("file", help="Path to the input file")
    compile_parser.set_defaults(func=_compile_command)

    validate_parser = subparsers.add_parser("validate", help="Validate a Core IL file")
    validate_parser.add_argument("file", help="Path to the Core IL JSON file")
    validate_parser.set_defaults(func=_validate_command)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

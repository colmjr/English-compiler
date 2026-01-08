"""CLI entry point for english_compiler."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _print_validation_errors(errors: list[dict]) -> None:
    for error in errors:
        print(f"{error['path']}: {error['message']}")


def _compile_command(args: argparse.Namespace) -> int:
    from english_compiler.coreil.interp import run_coreil
    from english_compiler.frontend.mock_llm import generate_coreil_from_text
    from englishc.coreil.validate import validate_coreil

    path = Path(args.file)
    try:
        source_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"{path}: {exc}")
        return 1

    doc = generate_coreil_from_text(source_text)
    errors = validate_coreil(doc)
    if errors:
        _print_validation_errors(errors)
        return 1

    output_path = path.with_suffix(".coreil.json")
    try:
        output_path.write_text(
            json.dumps(doc, indent=2, sort_keys=False) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        print(f"{output_path}: {exc}")
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
    compile_parser.set_defaults(func=_compile_command)

    run_parser = subparsers.add_parser("run", help="Run a Core IL file")
    run_parser.add_argument("file", help="Path to the Core IL JSON file")
    run_parser.set_defaults(func=_run_command)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

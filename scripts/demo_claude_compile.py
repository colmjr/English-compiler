"""Demo Claude Core IL generation."""

from __future__ import annotations

import json

from english_compiler.frontend.claude import generate_coreil_from_text


def main() -> None:
    source_text = "Print hello."
    doc = generate_coreil_from_text(source_text)
    print(json.dumps(doc, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

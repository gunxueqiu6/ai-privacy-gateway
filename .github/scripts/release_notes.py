#!/usr/bin/env python3
"""Extract release notes for a given version from CHANGELOG.md.

Usage: python release_notes.py v2.0.2 > release_body.md
"""
import re
import sys


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: release_notes.py <version>", file=sys.stderr)
        sys.exit(2)
    version = sys.argv[1].lstrip("v")
    with open("CHANGELOG.md", encoding="utf-8") as f:
        changelog = f.read()

    pattern = r"## \[" + re.escape(version) + r"\].*?\n(.*?)(?=\n## \[|\n---|\Z)"
    match = re.search(pattern, changelog, re.DOTALL)
    if not match:
        print(f"Release notes for version {version} not found in CHANGELOG.md", file=sys.stderr)
        sys.exit(1)
    print(match.group(1).strip())


if __name__ == "__main__":
    main()

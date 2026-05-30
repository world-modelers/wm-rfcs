#!/usr/bin/env python3
"""Validate the WM-RFC corpus.

This is a structural linter, not a content reviewer. It enforces the
preamble contract defined in PROCESS.md so that every RFC in `rfcs/` is
machine-readable and the index stays consistent. It has no third-party
dependencies and runs on any Python >= 3.8.

Checks, per RFC file `rfcs/WM-RFC-NNNN-*.md`:
  - a preamble fenced by a leading `---` / `---` block exists;
  - all REQUIRED headers are present and non-empty;
  - `WM-RFC` is a 4-digit integer that matches the filename;
  - `Status`, `Type`, and (for Standards Track) `Category` are in their enums;
  - `Created` is an ISO-8601 date (YYYY-MM-DD);
  - cross-reference headers (`Requires`, `Replaces`, `Superseded-By`) are present
    when the status implies them (`Superseded` => `Superseded-By`).

Corpus-level checks:
  - filenames follow `WM-RFC-NNNN-<slug>.md`;
  - numbers are unique;
  - every RFC appears in the index table of `rfcs/README.md`.

Exit code is non-zero if any check fails; the report lists every problem.
"""

from __future__ import annotations

import datetime as _dt
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RFC_DIR = REPO_ROOT / "rfcs"
INDEX = RFC_DIR / "README.md"

FILENAME_RE = re.compile(r"^WM-RFC-(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
HEADER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):[ \t]*(.*)$")

REQUIRED_HEADERS = ("WM-RFC", "Title", "Author", "Status", "Type", "Created", "License")

# Lifecycle states (see PROCESS.md §"Status lifecycle").
STATUSES = {
    "Draft",
    "Review",
    "Last Call",
    "Accepted",
    "Final",
    "Living",
    "Rejected",
    "Withdrawn",
    "Superseded",
    "Deprecated",
}
TYPES = {"Standards Track", "Process", "Informational"}
CATEGORIES = {"Interface", "Data", "Registry", "Meta"}


def parse_preamble(text: str):
    """Return (headers_dict, error_or_None). Headers preserve first occurrence."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "missing opening '---' preamble fence on line 1"
    headers = {}
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            return headers, None
        if not line.strip():
            continue
        m = HEADER_RE.match(line)
        if not m:
            return headers, f"malformed preamble line {i + 1}: {line!r}"
        key, value = m.group(1), m.group(2).strip()
        headers.setdefault(key, value)
    return headers, "missing closing '---' preamble fence"


def validate_file(path: Path):
    errors = []
    name = path.name

    fm = FILENAME_RE.match(name)
    if not fm:
        errors.append(
            f"filename does not match WM-RFC-NNNN-<slug>.md (lowercase slug): {name}"
        )

    headers, perr = parse_preamble(path.read_text(encoding="utf-8"))
    if perr:
        errors.append(perr)
        return errors, headers  # cannot continue without a preamble

    for key in REQUIRED_HEADERS:
        if not headers.get(key):
            errors.append(f"missing or empty required header: {key}")

    num = headers.get("WM-RFC", "")
    if num:
        if not re.fullmatch(r"\d{4}", num):
            errors.append(f"WM-RFC must be a zero-padded 4-digit number, got {num!r}")
        elif fm and num != fm.group(1):
            errors.append(
                f"WM-RFC header ({num}) does not match filename number ({fm.group(1)})"
            )

    status = headers.get("Status", "")
    if status and status not in STATUSES:
        errors.append(f"Status {status!r} not in {sorted(STATUSES)}")

    rfc_type = headers.get("Type", "")
    if rfc_type and rfc_type not in TYPES:
        errors.append(f"Type {rfc_type!r} not in {sorted(TYPES)}")

    category = headers.get("Category", "")
    if rfc_type == "Standards Track" and not category:
        errors.append("Standards Track RFCs require a Category header")
    if category and category not in CATEGORIES:
        errors.append(f"Category {category!r} not in {sorted(CATEGORIES)}")

    created = headers.get("Created", "")
    if created:
        try:
            _dt.date.fromisoformat(created)
        except ValueError:
            errors.append(f"Created {created!r} is not an ISO-8601 date (YYYY-MM-DD)")

    if status == "Superseded" and not headers.get("Superseded-By"):
        errors.append("Status is Superseded but Superseded-By header is missing")

    return errors, headers


def main() -> int:
    if not RFC_DIR.is_dir():
        print(f"error: {RFC_DIR} does not exist", file=sys.stderr)
        return 1

    rfc_files = sorted(
        p for p in RFC_DIR.glob("WM-RFC-*.md") if p.name != "WM-RFC-0000-template.md"
    )
    template = RFC_DIR / "WM-RFC-0000-template.md"
    if template.exists():
        rfc_files = [template, *rfc_files]

    if not rfc_files:
        print("error: no WM-RFC-*.md files found in rfcs/", file=sys.stderr)
        return 1

    index_text = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
    if not index_text:
        print(f"error: index {INDEX} is missing or empty", file=sys.stderr)
        return 1

    total_errors = 0
    seen_numbers = {}

    for path in rfc_files:
        errors, headers = validate_file(path)
        num = headers.get("WM-RFC", "")
        if num:
            if num in seen_numbers and num != "0000":
                errors.append(
                    f"duplicate WM-RFC number {num} (also {seen_numbers[num]})"
                )
            seen_numbers[num] = path.name

        # Every non-template RFC must be linked from the index.
        if path.name != "WM-RFC-0000-template.md" and path.name not in index_text:
            errors.append(f"not referenced in the index rfcs/README.md")

        if errors:
            total_errors += len(errors)
            print(f"FAIL {path.name}")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"ok   {path.name}")

    print()
    if total_errors:
        print(f"{total_errors} problem(s) found across {len(rfc_files)} file(s)")
        return 1
    print(f"all {len(rfc_files)} RFC file(s) valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

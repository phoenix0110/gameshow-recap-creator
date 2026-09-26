#!/usr/bin/env python3
"""Validate gameshow recap script Markdown format.

Usage: python tools/validate_script_format.py <script.md>
Exit 0 = pass, Exit 1 = errors found.
"""

import io
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

HEADER_RE = re.compile(r"^### (\d+:\d{2})\u2013(\d+:\d{2})\uff5c(.+)$")
CAMERA_RE = re.compile(r"\[\d+:\d{2}\u2013\d+:\d{2}\]")


def _time_to_sec(t: str) -> int:
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def validate(lines: list[str]) -> list[str]:
    errors: list[str] = []
    has_h1 = has_bq = has_script = has_packing = False
    script_start = script_end = -1

    for i, raw in enumerate(lines):
        ln = i + 1
        s = raw.strip()
        if not has_h1 and s.startswith("# ") and not s.startswith("## "):
            has_h1 = True
        if s.startswith(">") and has_h1 and not has_script:
            has_bq = True
        if s == "## \u811a\u672c":
            has_script, script_start = True, i
        if s == "## \u5305\u88c5\u6e05\u5355":
            has_packing, script_end = True, i

    if not has_h1:
        errors.append("ERR: missing H1 title")
    if not has_bq:
        errors.append("ERR: missing metadata blockquote before ## \u811a\u672c")
    if not has_script:
        errors.append("ERR: missing '## \u811a\u672c' section")
    if not has_packing:
        errors.append("ERR: missing '## \u5305\u88c5\u6e05\u5355' section")
    if has_script and has_packing and script_start > script_end:
        errors.append("ERR: '## \u811a\u672c' must come before '## \u5305\u88c5\u6e05\u5355'")
    if not has_script:
        return errors

    end = script_end if script_end > script_start else len(lines)
    prev_end_sec = -1
    seg_count = 0
    segments: list[tuple[int, int, int, str]] = []
    in_narration = False

    for i in range(script_start + 1, end):
        ln = i + 1
        s = lines[i].strip()

        if s.startswith("### "):
            in_narration = False
            seg_count += 1
            m = HEADER_RE.match(s)
            if not m:
                hint = ""
                if "-" in s and "\u2013" not in s:
                    hint += " use en-dash not hyphen"
                if "|" in s and "\uff5c" not in s:
                    hint += " use fullwidth bar not pipe"
                errors.append(f"ERR L{ln}: bad header format{hint}")
                continue
            t0, t1 = _time_to_sec(m[1]), _time_to_sec(m[2])
            if t0 >= t1:
                errors.append(f"ERR L{ln}: time range inverted {m[1]}>{m[2]}")
            if t0 < prev_end_sec:
                errors.append(f"ERR L{ln}: overlaps previous segment")
            prev_end_sec = t1
            segments.append((ln, t0, t1, m[3].strip()))
            continue

        if s.startswith("**\u753b\u9762**") and not CAMERA_RE.search(s):
            errors.append(f"ERR L{ln}: camera line missing [MM:SS\u2013MM:SS]")
        if s.startswith("**\u65c1\u767d**"):
            in_narration = True
            continue
        if in_narration:
            if s == "" or s.startswith("**"):
                in_narration = False
            elif not s.startswith(">"):
                errors.append(f"ERR L{ln}: narration line missing '>' prefix")
    if seg_count == 0:
        errors.append("ERR: no ### segments found in script section")
    elif segments:
        first_ln, first_start, first_end, first_title = segments[0]
        if first_start != 0:
            errors.append(f"ERR L{first_ln}: first segment must start at 0:00")
        if "\u94a9\u5b50" not in first_title:
            errors.append(f"ERR L{first_ln}: first segment title must contain '\u94a9\u5b50'")
        if len(segments) > 1 and segments[1][1] != first_end:
            errors.append(
                f"ERR L{segments[1][0]}: first story segment must start when hook ends"
            )
    return errors


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python validate_script_format.py <script.md>", file=sys.stderr)
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"ERR: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    errs = validate(path.read_text(encoding="utf-8").splitlines())
    for e in errs:
        print(e)
    print(f"\n{'FAILED: ' + str(len(errs)) + ' error(s)' if errs else 'OK'}")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()

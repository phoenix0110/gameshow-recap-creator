#!/usr/bin/env python3
"""Validate the Markdown format of a gameshow recap script.

Usage:
    python tools/validate_script_format.py <script.md>

Exit 0 = all checks pass
Exit 1 = validation errors found
"""

import argparse
import re
import sys
from pathlib import Path

SEGMENT_HEADER_RE = re.compile(
    r"^### (\d+:\d{2})\u2013(\d+:\d{2})\uff5c(.+)$"
)

SEGMENT_HEADER_LOOSE_RE = re.compile(r"^### .+")

CAMERA_TIMESTAMP_RE = re.compile(r"\[\d+:\d{2}\u2013\d+:\d{2}\]")

FORBIDDEN_HEADER_PATTERNS = [
    (re.compile(r"^\d+[\.\、\)]"), "段头包含序号"),
    (re.compile(r"[()（）]"), "段头包含括号"),
    (re.compile(r"约"), '段头包含"约"'),
]


def parse_time(t: str) -> int:
    """Convert M:SS string to total seconds."""
    parts = t.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def validate_file_structure(lines: list[str]) -> list[str]:
    errors: list[str] = []

    h1_line = None
    blockquote_found = False
    script_section_line = None
    packing_section_line = None

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if h1_line is None and stripped.startswith("# ") and not stripped.startswith("## "):
            h1_line = i
        if stripped.startswith(">") and h1_line and script_section_line is None:
            blockquote_found = True
        if stripped == "## 脚本":
            script_section_line = i
        if stripped == "## 包装清单":
            packing_section_line = i

    if h1_line is None:
        errors.append("ERROR L1: 缺少 H1 标题（# ...）")
    if not blockquote_found:
        errors.append("ERROR: 缺少元数据 blockquote（标题之后、## 脚本之前应有 > 开头的引用块）")
    if script_section_line is None:
        errors.append('ERROR: 缺少 "## 脚本" 段落')
    if packing_section_line is None:
        errors.append('ERROR: 缺少 "## 包装清单" 段落')
    if script_section_line and packing_section_line:
        if script_section_line > packing_section_line:
            errors.append(
                f'ERROR L{script_section_line}: "## 脚本" (L{script_section_line}) '
                f'应出现在 "## 包装清单" (L{packing_section_line}) 之前'
            )

    return errors


def _find_script_range(lines: list[str]) -> tuple[int | None, int | None]:
    """Return (start, end) 1-based line numbers of the script section body."""
    start = None
    end = None
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "## 脚本":
            start = i + 1
        elif start and stripped.startswith("## ") and stripped != "## 脚本":
            end = i
            break
    if start and end is None:
        end = len(lines) + 1
    return start, end


def validate_segment_headers(lines: list[str]) -> list[str]:
    errors: list[str] = []
    start, end = _find_script_range(lines)
    if start is None:
        return errors

    prev_end_seconds = -1
    found_any_segment = False

    for i in range(start - 1, (end or len(lines) + 1) - 1):
        line = lines[i].strip()
        if not line.startswith("### "):
            continue

        found_any_segment = True
        lineno = i + 1
        match = SEGMENT_HEADER_RE.match(line)

        if not match:
            hint = _diagnose_header(line)
            errors.append(f"ERROR L{lineno}: 段头格式不符 \"{line}\" -- {hint}")
            continue

        time_start_str, time_end_str, seg_name = match.group(1), match.group(2), match.group(3)

        ss = int(time_start_str.split(":")[1])
        es = int(time_end_str.split(":")[1])
        if ss > 59:
            errors.append(f"ERROR L{lineno}: 起始时间秒数 {ss} 超出范围 (00-59)")
        if es > 59:
            errors.append(f"ERROR L{lineno}: 结束时间秒数 {es} 超出范围 (00-59)")

        start_sec = parse_time(time_start_str)
        end_sec = parse_time(time_end_str)

        if start_sec >= end_sec:
            errors.append(
                f"ERROR L{lineno}: 段头时间倒序 {time_start_str} >= {time_end_str}"
            )

        if start_sec < prev_end_seconds:
            errors.append(
                f"ERROR L{lineno}: 段头时间与上一段重叠或倒退 "
                f"(本段起始 {time_start_str}，上一段结束秒数 {prev_end_seconds}s)"
            )
        prev_end_seconds = end_sec

        for pattern, msg in FORBIDDEN_HEADER_PATTERNS:
            if pattern.search(seg_name):
                errors.append(f"ERROR L{lineno}: {msg} \"{seg_name}\"")

    if not found_any_segment:
        errors.append('ERROR: "## 脚本" 内未找到任何 ### 段头')

    return errors


def _diagnose_header(line: str) -> str:
    """Provide a human-readable hint about what's wrong with a malformed header."""
    hints = []
    if "-" in line and "\u2013" not in line:
        hints.append('应使用 en-dash "–"(U+2013) 而非连字符 "-"')
    if "|" in line and "\uff5c" not in line:
        hints.append('应使用全角竖线 "｜"(U+FF5C) 而非半角 "|"')
    if "\u2014" in line:
        hints.append('应使用 en-dash "–"(U+2013) 而非 em-dash "—"')
    if "：" in line and "\uff5c" not in line:
        hints.append('段名分隔符应使用全角竖线 "｜" 而非冒号')
    return "; ".join(hints) if hints else "格式不匹配 ### M:SS–M:SS｜段名"


def validate_segment_content(lines: list[str]) -> list[str]:
    errors: list[str] = []
    start, end = _find_script_range(lines)
    if start is None:
        return errors

    segments = _split_segments(lines, start - 1, (end or len(lines) + 1) - 1)

    for seg_lineno, seg_lines in segments:
        has_narration = False
        in_narration = False

        for offset, sline in enumerate(seg_lines):
            lineno = seg_lineno + offset
            stripped = sline.strip()

            if stripped.startswith("**画面**") and not CAMERA_TIMESTAMP_RE.search(stripped):
                errors.append(
                    f"ERROR L{lineno}: **画面** 行缺少 [MM:SS–MM:SS] 时间码"
                )

            if stripped.startswith("**旁白**"):
                has_narration = True
                in_narration = True
                continue

            if in_narration:
                if stripped == "":
                    in_narration = False
                    continue
                if stripped.startswith("**"):
                    in_narration = False
                elif not stripped.startswith(">"):
                    errors.append(
                        f'ERROR L{lineno}: 旁白行缺少 ">" 前缀: "{stripped}"'
                    )

            if stripped.startswith("**花字**"):
                content = stripped.split("：", 1)[-1].strip() if "：" in stripped else ""
                if content and "/" in content and " / " not in content:
                    errors.append(
                        f'ERROR L{lineno}: **花字** 多项应使用 " / " (空格+斜杠+空格) 分隔'
                    )

        if not has_narration:
            errors.append(f"ERROR L{seg_lineno}: 段落缺少 **旁白** 标记")

    return errors


def _split_segments(
    lines: list[str], start_idx: int, end_idx: int
) -> list[tuple[int, list[str]]]:
    """Split the script section into (lineno, lines) per ### segment."""
    segments: list[tuple[int, list[str]]] = []
    current_start: int | None = None
    current_lines: list[str] = []

    for i in range(start_idx, end_idx):
        stripped = lines[i].strip()
        if stripped.startswith("### "):
            if current_start is not None:
                segments.append((current_start, current_lines))
            current_start = i + 1
            current_lines = [lines[i]]
        elif current_start is not None:
            current_lines.append(lines[i])

    if current_start is not None:
        segments.append((current_start, current_lines))

    return segments


def validate(filepath: Path) -> list[str]:
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()

    errors: list[str] = []
    errors.extend(validate_file_structure(lines))
    errors.extend(validate_segment_headers(lines))
    errors.extend(validate_segment_content(lines))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate gameshow recap script Markdown format"
    )
    parser.add_argument("file", type=Path, help="Path to the script Markdown file")
    args = parser.parse_args()

    if not args.file.exists():
        print(f"ERROR: 文件不存在: {args.file}", file=sys.stderr)
        sys.exit(1)

    errors = validate(args.file)

    if errors:
        for e in errors:
            print(e)
        print(f"\nFAILED: {len(errors)} error(s) found")
        sys.exit(1)
    else:
        print("OK: all format checks passed")
        sys.exit(0)


if __name__ == "__main__":
    main()

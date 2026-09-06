#!/usr/bin/env python3
"""Check alignment between recap script 画面 timestamps and source subtitles.

For each script section, extracts subtitle entries within the 画面 time range
and outputs them alongside the narration text for LLM review.
Also checks monotonic ordering of source timestamps.

Usage:
    python tools/check_alignment.py <script.md> <subtitle.srt>
    python tools/check_alignment.py <script.md> <subtitle.srt> --search "keyword"

Exit 0 = all mechanical checks pass, Exit 1 = errors found.
"""

import io
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


SECTION_RE = re.compile(r"^###\s+(\d+:\d{2})\u2013(\d+:\d{2})\uff5c(.+)$")
VISUAL_RE = re.compile(r"\[(\d+:\d{2})\s*\u2013\s*(\d+:\d{2})\]")
SRT_TS_RE = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)")


def _mmss_to_sec(t: str) -> float:
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def _sec_to_mmss(sec: float) -> str:
    m = int(sec) // 60
    s = int(sec) % 60
    return f"{m}:{s:02d}"


def _srt_ts_to_sec(ts: str) -> float:
    match = SRT_TS_RE.match(ts.strip())
    if not match:
        return 0.0
    h, m, s, ms = int(match[1]), int(match[2]), int(match[3]), int(match[4])
    return h * 3600 + m * 60 + s + ms / 1000


def parse_srt(path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8", errors="replace")
    entries: list[dict] = []
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = block.strip().split("\n")
        ts_line = next((l for l in lines if "-->" in l), None)
        if ts_line is None:
            continue
        ts_idx = lines.index(ts_line)
        parts = ts_line.split("-->")
        if len(parts) != 2:
            continue
        start = _srt_ts_to_sec(parts[0])
        end = _srt_ts_to_sec(parts[1])
        text = " ".join(lines[ts_idx + 1 :]).strip()
        text = re.sub(r"<[^>]+>", "", text)
        if text:
            entries.append({"start": start, "end": end, "text": text})
    return entries


def parse_script(path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")

    sections: list[dict] = []
    i = 0
    while i < len(lines):
        m = SECTION_RE.match(lines[i].strip())
        if not m:
            i += 1
            continue

        out_start = _mmss_to_sec(m[1])
        out_end = _mmss_to_sec(m[2])
        title = m[3].strip()
        line_num = i + 1

        visual_ranges: list[tuple[float, float, str]] = []
        narration_lines: list[str] = []
        in_narration = False
        i += 1

        while i < len(lines):
            s = lines[i].strip()
            if SECTION_RE.match(s):
                break
            if s.startswith("## "):
                break

            if s.startswith("**\u753b\u9762**"):
                for vm in VISUAL_RE.finditer(s):
                    vs = _mmss_to_sec(vm[1])
                    ve = _mmss_to_sec(vm[2])
                    desc = s.split("]", 1)[-1].strip() if "]" in s else ""
                    visual_ranges.append((vs, ve, desc))
                in_narration = False
            elif s.startswith("**\u65c1\u767d**"):
                in_narration = True
            elif in_narration:
                if s == "" or s.startswith("**"):
                    in_narration = False
                elif s.startswith(">"):
                    narration_lines.append(s.lstrip("> ").strip())
            i += 1

        sections.append({
            "title": title,
            "line": line_num,
            "out_start": out_start,
            "out_end": out_end,
            "visual_ranges": visual_ranges,
            "narration": "\n".join(narration_lines),
        })
    return sections


def subs_in_range(entries: list[dict], start: float, end: float) -> list[dict]:
    return [e for e in entries if e["end"] > start and e["start"] < end]


def search_keyword(entries: list[dict], keyword: str) -> list[dict]:
    kw = keyword.lower()
    return [e for e in entries if kw in e["text"].lower()]


def run_check(sections: list[dict], srt_entries: list[dict]) -> list[str]:
    errors: list[str] = []
    prev_src_start = -1.0

    for idx, sec in enumerate(sections):
        prefix = f"[{idx + 1}] {sec['title']}"

        if not sec["visual_ranges"]:
            errors.append(f"{prefix}: no \u753b\u9762 time range found")
            continue

        for j, (vs, ve, _desc) in enumerate(sec["visual_ranges"]):
            tag = f"{prefix} \u753b\u9762[{j}]" if len(sec["visual_ranges"]) > 1 else prefix

            if vs >= ve:
                errors.append(f"{tag}: inverted range [{_sec_to_mmss(vs)}\u2013{_sec_to_mmss(ve)}]")
            if vs < prev_src_start:
                errors.append(
                    f"{tag}: NON-MONOTONIC \u2013 [{_sec_to_mmss(vs)}] < "
                    f"previous [{_sec_to_mmss(prev_src_start)}]"
                )
            prev_src_start = vs

            subs = subs_in_range(srt_entries, vs, ve)
            if not subs:
                errors.append(
                    f"{tag}: EMPTY RANGE [{_sec_to_mmss(vs)}\u2013{_sec_to_mmss(ve)}] "
                    f"\u2013 no subtitles found"
                )
    return errors


def print_report(sections: list[dict], srt_entries: list[dict]) -> None:
    for idx, sec in enumerate(sections):
        print(f"\n{'=' * 60}")
        print(f"[{idx + 1}/{len(sections)}] {sec['title']}")
        print(f"  Output: {_sec_to_mmss(sec['out_start'])}\u2013{_sec_to_mmss(sec['out_end'])}")

        if not sec["visual_ranges"]:
            print("  \u753b\u9762: (none)")
            print("  \u2757 NO VISUAL RANGE")
        else:
            for j, (vs, ve, desc) in enumerate(sec["visual_ranges"]):
                tag = f"  \u753b\u9762[{j}]" if len(sec["visual_ranges"]) > 1 else "  \u753b\u9762"
                print(f"{tag}: [{_sec_to_mmss(vs)}\u2013{_sec_to_mmss(ve)}] {desc}")

                subs = subs_in_range(srt_entries, vs, ve)
                if not subs:
                    print(f"    \u274c EMPTY: no subtitles in range")
                else:
                    print(f"    Subtitles ({len(subs)} entries):")
                    for sub in subs[:15]:
                        time_tag = _sec_to_mmss(sub["start"])
                        text = sub["text"][:90]
                        print(f"      [{time_tag}] {text}")
                    if len(subs) > 15:
                        print(f"      ... and {len(subs) - 15} more")

        narr = sec["narration"]
        preview = narr[:150] + ("..." if len(narr) > 150 else "")
        print(f"  \u65c1\u767d: {preview}")


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage:\n"
            "  python check_alignment.py <script.md> <subtitle.srt>\n"
            "  python check_alignment.py <script.md> <subtitle.srt> --search \"keyword\"",
            file=sys.stderr,
        )
        sys.exit(1)

    script_path = Path(sys.argv[1])
    srt_path = Path(sys.argv[2])

    if not script_path.exists():
        sys.exit(f"ERR: script not found: {script_path}")
    if not srt_path.exists():
        sys.exit(f"ERR: subtitle not found: {srt_path}")

    sections = parse_script(script_path)
    srt_entries = parse_srt(srt_path)

    if not sections:
        sys.exit("ERR: no sections found in script")
    if not srt_entries:
        sys.exit("ERR: no entries found in subtitle file")

    # Keyword search mode
    if "--search" in sys.argv:
        si = sys.argv.index("--search")
        if si + 1 >= len(sys.argv):
            sys.exit("ERR: --search requires a keyword")
        kw = sys.argv[si + 1]
        results = search_keyword(srt_entries, kw)
        print(f"Search '{kw}': {len(results)} match(es)")
        for r in results:
            print(f"  [{_sec_to_mmss(r['start'])}\u2013{_sec_to_mmss(r['end'])}] {r['text']}")
        sys.exit(0)

    srt_span = f"{_sec_to_mmss(srt_entries[0]['start'])}\u2013{_sec_to_mmss(srt_entries[-1]['end'])}"
    print(f"Script: {len(sections)} sections")
    print(f"Subtitle: {len(srt_entries)} entries ({srt_span})")

    print_report(sections, srt_entries)

    errors = run_check(sections, srt_entries)

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"  Sections: {len(sections)}")
    print(f"  Errors: {len(errors)}")

    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  \u274c {e}")
        print(f"\nFAILED: {len(errors)} error(s)")
        sys.exit(1)
    else:
        print("\nOK \u2013 all mechanical checks pass")
        print("Review the subtitle excerpts above to verify content alignment.")
        sys.exit(0)


if __name__ == "__main__":
    main()

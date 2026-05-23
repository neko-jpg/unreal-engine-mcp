"""Fold CHANGELOG.d/<wave>-*.md fragments into the top of CHANGELOG.md.

234-stubs Wave 0.5 follow-up (umbrella: #69).

The wave-close PR runs this script to append every accumulated fragment to
the `## [Unreleased]` section of `CHANGELOG.md` under a new
`### 234-stubs Wave <n>` subsection. The fragments are then deleted in
the same commit, leaving `CHANGELOG.d/` ready for the next wave.

Usage:
    python scripts/fold_changelog_fragments.py --wave 1
    python scripts/fold_changelog_fragments.py --wave 3 --dry-run

The script is intentionally idempotent: if the target subsection already
exists for the wave, fragments are *appended* to it instead of duplicating
the heading.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path
from typing import List


REPO_ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
FRAGMENT_DIR = REPO_ROOT / "CHANGELOG.d"

UNRELEASED_HEADER = "## [Unreleased]"
WAVE_HEADING_FMT = "### 234-stubs Wave {wave}"
EXCLUDED_FRAGMENT_NAMES = {"README.md", ".gitkeep"}


def _iter_fragments(wave: int) -> List[Path]:
    if not FRAGMENT_DIR.is_dir():
        return []
    prefix = f"w{wave}-"
    out: List[Path] = []
    for p in sorted(FRAGMENT_DIR.glob("*.md")):
        if p.name in EXCLUDED_FRAGMENT_NAMES:
            continue
        if not p.name.lower().startswith(prefix):
            continue
        out.append(p)
    return out


def _ensure_unreleased(content: str) -> str:
    if UNRELEASED_HEADER in content:
        return content
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    header = f"{UNRELEASED_HEADER}\n\n_Last folded: {today}_\n\n"
    return header + content


def _splice_wave_block(content: str, wave: int, body: str) -> str:
    """Insert or extend the wave subsection inside ## [Unreleased]."""
    wave_heading = WAVE_HEADING_FMT.format(wave=wave)
    if wave_heading in content:
        pattern = re.compile(
            r"(" + re.escape(wave_heading) + r"\s*\n)",
            re.MULTILINE,
        )
        return pattern.sub(r"\1\n" + body.strip() + "\n\n", content, count=1)

    pattern = re.compile(
        r"(" + re.escape(UNRELEASED_HEADER) + r"\s*\n)",
        re.MULTILINE,
    )
    section = f"\n{wave_heading}\n\n{body.strip()}\n\n"
    return pattern.sub(r"\1" + section, content, count=1)


def fold(wave: int, *, dry_run: bool = False) -> int:
    fragments = _iter_fragments(wave)
    if not fragments:
        print(f"no fragments found for wave {wave}")
        return 0

    body_chunks: List[str] = []
    for fragment in fragments:
        body_chunks.append(fragment.read_text(encoding="utf-8-sig").strip())
    body = "\n\n".join(body_chunks)

    original = CHANGELOG.read_text(encoding="utf-8-sig") if CHANGELOG.exists() else ""
    updated = _ensure_unreleased(original)
    updated = _splice_wave_block(updated, wave, body)

    if dry_run:
        print(f"[dry-run] would fold {len(fragments)} fragment(s) into wave {wave}")
        for fragment in fragments:
            try:
                rel = fragment.relative_to(REPO_ROOT)
            except ValueError:
                rel = fragment
            print(f"  - {rel}")
        return 0

    CHANGELOG.write_text(updated, encoding="utf-8")
    for fragment in fragments:
        fragment.unlink()
    print(
        f"folded {len(fragments)} fragment(s) into "
        f"'{WAVE_HEADING_FMT.format(wave=wave)}' under {UNRELEASED_HEADER}"
    )
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wave", type=int, required=True, choices=[1, 2, 3, 4, 5])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    return fold(args.wave, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

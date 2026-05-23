"""Audit that no new `queued: true` success path is introduced.

234-stubs Wave 0.5 follow-up (umbrella: #69).

This script counts every `SetBoolField(TEXT("queued"), true)` occurrence in
the C++ command handlers under
`Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/*Commands.cpp` and
compares them to a baseline JSON snapshot stored at
`artifacts/queued_baseline.json`.

The audit *does not* require existing queued sites to be removed (that is the
job of the per-category Wave 1-5 PRs), but it does fail if a PR adds new
queued sites or moves them between files in a way that increases the total.

Usage:
    # Verify against the existing baseline.
    python scripts/audit_no_new_queued.py

    # Rebuild the baseline (only after a wave close PR).
    python scripts/audit_no_new_queued.py --update-baseline

    # Use a custom baseline location (CI artifacts).
    python scripts/audit_no_new_queued.py --baseline path/to/queued_baseline.json

Exit codes:
    0  Current counts are equal to or lower than baseline (and per-file is
       not strictly larger anywhere).
    1  A regression was detected (count increased for the repository or for a
       specific file). The CI workflow uses this exit code to block the PR.
    2  Invalid arguments or unreadable baseline file.

The baseline schema is intentionally tiny so that diffs in PRs are obvious:

    {
        "schema": 1,
        "generated_utc": "2026-05-23T00:00:00Z",
        "total": 226,
        "per_file": {
            "EpicUnrealMCPAiNavExtensionCommands.cpp": 23,
            ...
        }
    }

When the baseline is rebuilt the previous values are replaced atomically.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[1]
CPP_DIR = (
    REPO_ROOT
    / "Plugins"
    / "UnrealMCP"
    / "Source"
    / "UnrealMCP"
    / "Private"
    / "Commands"
)
DEFAULT_BASELINE = REPO_ROOT / "artifacts" / "queued_baseline.json"

# Matches the canonical queued-success pattern used by every stub category
# handler: `Data->SetBoolField(TEXT("queued"), true);`.
QUEUED_PATTERN = re.compile(
    r'SetBoolField\(\s*TEXT\(\s*"queued"\s*\)\s*,\s*true\s*\)'
)


def _iter_cpp_files() -> Iterable[Path]:
    if not CPP_DIR.is_dir():
        return []
    return sorted(CPP_DIR.glob("*Commands.cpp"))


def count_queued_per_file() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for path in _iter_cpp_files():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        n = len(QUEUED_PATTERN.findall(text))
        if n:
            counts[path.name] = n
    return counts


def load_baseline(baseline_path: Path) -> Dict[str, object]:
    if not baseline_path.is_file():
        raise SystemExit(
            f"baseline file is missing: {baseline_path}. Run with "
            "--update-baseline once to seed it."
        )
    try:
        data = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover
        raise SystemExit(f"failed to read baseline {baseline_path}: {exc}") from exc
    if not isinstance(data, dict) or "per_file" not in data:
        raise SystemExit(
            f"baseline {baseline_path} is malformed (missing 'per_file')."
        )
    return data


def write_baseline(baseline_path: Path, counts: Dict[str, int]) -> None:
    payload = {
        "schema": 1,
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "total": sum(counts.values()),
        "per_file": dict(sorted(counts.items())),
    }
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def diff_against_baseline(
    current: Dict[str, int], baseline: Dict[str, object]
) -> List[str]:
    """Return a list of human-readable regression messages.

    A regression is reported when:
      * the total across all files strictly increased, OR
      * any individual file's count strictly increased, OR
      * a brand-new file appeared with a non-zero count.
    """
    problems: List[str] = []
    baseline_per_file = baseline.get("per_file") or {}
    if not isinstance(baseline_per_file, dict):
        problems.append("baseline 'per_file' is not an object")
        return problems

    baseline_total = int(baseline.get("total") or 0)
    current_total = sum(current.values())
    if current_total > baseline_total:
        problems.append(
            f"total queued:true regressed: baseline={baseline_total} -> "
            f"current={current_total} (delta=+{current_total - baseline_total})"
        )

    for name, current_count in sorted(current.items()):
        prior = int(baseline_per_file.get(name, 0))
        if current_count > prior:
            problems.append(
                f"{name}: {prior} -> {current_count} (+{current_count - prior})"
            )
    return problems


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE,
        help=f"baseline JSON path (default: {DEFAULT_BASELINE.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="rewrite the baseline file with the current counts and exit 0.",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        dest="print_counts",
        help="print the current per-file counts as JSON on stdout.",
    )
    args = parser.parse_args(argv)

    current = count_queued_per_file()

    if args.print_counts:
        print(json.dumps({"total": sum(current.values()), "per_file": current}, indent=2))

    if args.update_baseline:
        write_baseline(args.baseline, current)
        print(
            f"wrote baseline {args.baseline} "
            f"(total={sum(current.values())}, files={len(current)})"
        )
        return 0

    baseline = load_baseline(args.baseline)
    problems = diff_against_baseline(current, baseline)
    if problems:
        print("queued:true regression detected:")
        for line in problems:
            print(f"  - {line}")
        print(
            "\nIf this PR intentionally promotes handlers, run "
            "'python scripts/audit_no_new_queued.py --update-baseline' "
            "from a wave-close PR (not a category PR) and commit the diff."
        )
        return 1

    print(
        f"queued:true audit OK (current total={sum(current.values())}, "
        f"baseline total={int(baseline.get('total') or 0)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

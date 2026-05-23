"""234-stubs Wave 0.5 follow-up (umbrella: #69).

Unit tests for scripts/audit_no_new_queued.py. The tests import the script
as a module so the regex, baseline I/O, and diff logic can be exercised
without spawning a subprocess.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "audit_no_new_queued.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_no_new_queued", SCRIPT)
    assert spec and spec.loader, "could not load audit_no_new_queued.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def audit_mod():
    return _load_module()


def test_pattern_matches_canonical_queued_line(audit_mod):
    src = 'Data->SetBoolField(TEXT("queued"), true);'
    assert audit_mod.QUEUED_PATTERN.search(src) is not None


def test_pattern_ignores_executed_line(audit_mod):
    src = 'Data->SetBoolField(TEXT("executed"), true);'
    assert audit_mod.QUEUED_PATTERN.search(src) is None


def test_pattern_ignores_queued_false(audit_mod):
    src = 'Data->SetBoolField(TEXT("queued"), false);'
    assert audit_mod.QUEUED_PATTERN.search(src) is None


def test_diff_passes_when_counts_match(audit_mod):
    current = {"A.cpp": 3, "B.cpp": 1}
    baseline = {"total": 4, "per_file": {"A.cpp": 3, "B.cpp": 1}}
    assert audit_mod.diff_against_baseline(current, baseline) == []


def test_diff_passes_when_counts_drop(audit_mod):
    current = {"A.cpp": 2, "B.cpp": 1}
    baseline = {"total": 4, "per_file": {"A.cpp": 3, "B.cpp": 1}}
    assert audit_mod.diff_against_baseline(current, baseline) == []


def test_diff_flags_total_regression(audit_mod):
    current = {"A.cpp": 4, "B.cpp": 1}
    baseline = {"total": 4, "per_file": {"A.cpp": 3, "B.cpp": 1}}
    problems = audit_mod.diff_against_baseline(current, baseline)
    assert any("total queued:true regressed" in p for p in problems)


def test_diff_flags_per_file_regression(audit_mod):
    current = {"A.cpp": 5}
    baseline = {"total": 5, "per_file": {"A.cpp": 3, "B.cpp": 2}}
    problems = audit_mod.diff_against_baseline(current, baseline)
    assert any("A.cpp: 3 -> 5" in p for p in problems)


def test_diff_flags_new_file_with_queued(audit_mod):
    current = {"A.cpp": 3, "Newcomer.cpp": 1}
    baseline = {"total": 3, "per_file": {"A.cpp": 3}}
    problems = audit_mod.diff_against_baseline(current, baseline)
    assert any("Newcomer.cpp: 0 -> 1" in p for p in problems)


def test_write_baseline_roundtrip(tmp_path, audit_mod):
    target = tmp_path / "queued_baseline.json"
    counts = {"Z.cpp": 7, "A.cpp": 2}
    audit_mod.write_baseline(target, counts)
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["total"] == 9
    assert list(payload["per_file"].keys()) == ["A.cpp", "Z.cpp"]


def test_load_baseline_rejects_missing_per_file(tmp_path, audit_mod):
    target = tmp_path / "bad.json"
    target.write_text(json.dumps({"total": 0}), encoding="utf-8")
    with pytest.raises(SystemExit):
        audit_mod.load_baseline(target)


def test_load_baseline_tolerates_utf8_bom(tmp_path, audit_mod):
    target = tmp_path / "bom.json"
    payload = {"schema": 1, "total": 0, "per_file": {}}
    target.write_text(json.dumps(payload), encoding="utf-8-sig")
    assert audit_mod.load_baseline(target)["per_file"] == {}


def test_real_baseline_matches_current_counts(audit_mod):
    """The committed baseline must match the current tree state.

    Wave 1+ category PRs should *decrease* this count and rerun
    `--update-baseline` only from a wave-close PR.
    """
    current = audit_mod.count_queued_per_file()
    baseline_path = REPO_ROOT / "artifacts" / "queued_baseline.json"
    baseline = audit_mod.load_baseline(baseline_path)
    assert audit_mod.diff_against_baseline(current, baseline) == []

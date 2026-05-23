"""Wave 0 (#75) regression: live_e2e_smoke wave grouping is well-formed."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def smoke_module():
    """Import scripts/live_e2e_smoke.py as a module without running main()."""
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "scripts" / "live_e2e_smoke.py"
    spec = importlib.util.spec_from_file_location("live_e2e_smoke_test", script)
    assert spec is not None and spec.loader is not None, f"spec failure for {script}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["live_e2e_smoke_test"] = module
    spec.loader.exec_module(module)
    return module


def test_wave_groups_table_is_a_dict(smoke_module):
    table = smoke_module.WAVE_GROUPS
    assert isinstance(table, dict)
    assert len(table) > 0
    for name, wave in table.items():
        assert isinstance(name, str) and name, f"invalid case name {name!r}"
        assert isinstance(wave, str) and wave, f"invalid wave label for {name!r}: {wave!r}"
        assert wave in {"core", "wave1", "wave2", "wave3", "wave4", "wave5"}, wave


def test_wave_for_defaults_to_core_for_unknown_case(smoke_module):
    assert smoke_module.wave_for("nonexistent_case_xyz") == "core"


def test_list_groups_contains_known_cases(smoke_module):
    groups = smoke_module.list_groups()
    assert "core" in groups
    flat = {name for names in groups.values() for name in names}
    # Spot-check a Wave 0 baseline case
    assert "ping" in flat
    # Spot-check a Wave 4 Cesium case present in the wave4 bucket
    assert "cesium_check_plugin" in groups.get("wave4", []), groups


def test_every_listed_case_exists_in_case_table(smoke_module):
    """Every entry in WAVE_GROUPS must point at an actual case from CASES + MANUAL_CASES."""
    known = {name for name, _r, _f in (smoke_module.CASES + smoke_module.MANUAL_CASES)}
    for name in smoke_module.WAVE_GROUPS:
        assert name in known, f"WAVE_GROUPS lists '{name}' which is not in CASES/MANUAL_CASES"

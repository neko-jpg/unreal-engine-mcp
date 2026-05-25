"""KPI tests per React-for-UE v3.0 plan."""

from __future__ import annotations

import time
from typing import Any, Dict, List

import pytest

import server.dialog_tools as dt
from helpers.fake_unreal_connection import FakeUnrealConnection
from server.planning.design_patch import (
    ComponentPatch,
    DesignPatch,
    Intent,
    new_patch_id,
)
from server.planning.patch_executor import PatchExecutor


# ---------------------------------------------------------------------------
# Plan KPI: dry_run < 2s (LLM/VLM excluded)
# ---------------------------------------------------------------------------


class _FakeClient:
    def __init__(self, objects):
        self.objects = objects

    def call_scene_syncd(self, path, payload):
        defaults = {
            "/objects/list": {"success": True, "data": {"objects": self.objects}},
            "/entities/list": {"success": True, "data": {"entities": []}},
            "/components/list": {"success": True, "data": {"components": []}},
            "/assets/list": {"success": True, "data": {"assets": []}},
            "/snapshots/list": {"success": True, "data": {"snapshots": []}},
            "/operations/recent": {"success": True, "data": {"operations": []}},
        }
        return defaults.get(path, {"success": True, "data": {}})


def test_kpi_dry_run_under_2s(monkeypatch):
    objects = [
        {"mcp_id": f"obj_{i:03d}", "kind": "light" if i % 4 == 0 else "wall",
         "name": f"obj_{i:03d}", "tags": ["torch" if i % 4 == 0 else "stone"]}
        for i in range(200)
    ]
    monkeypatch.setattr(dt, "_summarizer_client", lambda: _FakeClient(objects))

    t0 = time.perf_counter()
    res = dt.scene_edit("make this cave creepy", scene_id="kpi", mode="dry_run")
    elapsed = time.perf_counter() - t0
    assert res["success"]
    assert elapsed < 2.0, f"dry_run took {elapsed:.2f}s, exceeds 2s budget"


# ---------------------------------------------------------------------------
# Plan KPI: 100 actor sync < 500ms relaxed in CI
# ---------------------------------------------------------------------------


def _build_100_light_patch():
    dp = DesignPatch(
        patch_id=new_patch_id(),
        scene_id="kpi_apply",
        intent=Intent(raw_text="kpi", scene_id="kpi_apply"),
        component_patches=[
            ComponentPatch(
                scene_id="kpi_apply",
                entity_id=f"actor:torch_{i:03d}",
                component_type="light",
                name="primary",
                properties={"intensity_multiplier": 0.5, "index": i},
                capability_id="light.set_intensity",
            )
            for i in range(100)
        ],
        max_operations=500,
    )
    dp.fill_component_hashes()
    return dp


class _Mem:
    def __init__(self):
        self.calls = 0

    def __call__(self, path, payload):
        self.calls += 1
        return {"success": True, "data": {}}


def test_kpi_100_actor_apply_under_relaxed_2s_threshold():
    """Plan target is 500ms in real UE; CI uses relaxed 2s for the fake path."""
    dp = _build_100_light_patch()
    syncd = _Mem()
    fake = FakeUnrealConnection()
    executor = PatchExecutor(scene_syncd=syncd, unreal_connection=fake)
    t0 = time.perf_counter()
    report = executor.apply(dp, create_snapshot=False, require_safe_only=True)
    elapsed = time.perf_counter() - t0
    assert report.succeeded == 100
    assert elapsed < 2.0, f"100 actor apply took {elapsed:.2f}s, exceeds relaxed budget"


def test_kpi_idempotency_second_run_100_percent_noop():
    dp = _build_100_light_patch()
    syncd = _Mem()
    fake = FakeUnrealConnection()
    executor = PatchExecutor(scene_syncd=syncd, unreal_connection=fake)
    r1 = executor.apply(dp, create_snapshot=False, require_safe_only=True)
    r2 = executor.apply(dp, create_snapshot=False, require_safe_only=True)
    assert r1.succeeded == 100 and r2.noop == 100
    assert r2.succeeded == 0

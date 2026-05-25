"""Integration tests for PatchExecutor and apply_safe path."""

from __future__ import annotations

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
from server.planning.patch_compiler import PatchCompiler
from server.planning.patch_executor import PatchExecutor


def _intent(scene="cave_test", mood="creepy", domains=("lighting", "atmosphere")):
    return Intent(raw_text="test", scene_id=scene, action="modify", mood=mood, domains=list(domains))


def _component(scene="cave_test", entity="actor:torch_01", ctype="light", cap_id="light.set_intensity"):
    return ComponentPatch(
        scene_id=scene,
        entity_id=entity,
        component_type=ctype,
        name="primary",
        properties={"intensity_multiplier": 0.35},
        capability_id=cap_id,
    )


def _build_simple_patch():
    dp = DesignPatch(
        patch_id=new_patch_id(),
        scene_id="cave_test",
        intent=_intent(),
        component_patches=[_component()],
    )
    dp.fill_component_hashes()
    return dp


class _MemoryScenSyncd:
    def __init__(self):
        self.calls: List[tuple[str, Dict[str, Any]]] = []
        self.responses: Dict[str, Dict[str, Any]] = {}

    def __call__(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append((path, payload))
        return self.responses.get(path, {"success": True, "data": {}})

    def calls_for(self, path: str):
        return [c for c in self.calls if c[0] == path]


def test_compiler_produces_python_apply_for_lights_and_materials():
    cp_light = _component(ctype="light", cap_id="light.set_intensity")
    cp_mat = _component(ctype="material", cap_id="material.batch_update_parameters")
    dp = DesignPatch(
        patch_id=new_patch_id(),
        scene_id="cave_test",
        intent=_intent(),
        component_patches=[cp_light, cp_mat],
    )
    compiled = PatchCompiler().compile(dp)
    assert len(compiled.python_apply) == 2
    assert len(compiled.rust_apply_keys) == 2  # both are rust-handled by PR7


def test_executor_writes_components_and_calls_unreal():
    dp = _build_simple_patch()
    syncd = _MemoryScenSyncd()
    fake = FakeUnrealConnection()
    executor = PatchExecutor(scene_syncd=syncd, unreal_connection=fake)
    report = executor.apply(dp, create_snapshot=False, require_safe_only=True)
    assert report.succeeded == 1 and report.failed == 0
    assert syncd.calls_for("/components/upsert"), "component must be upserted"
    assert "set_light_intensity" in fake.commands()
    # operation log written
    assert syncd.calls_for("/operations/record")


def test_executor_is_idempotent_when_run_twice_with_same_executor():
    dp = _build_simple_patch()
    syncd = _MemoryScenSyncd()
    fake = FakeUnrealConnection()
    executor = PatchExecutor(scene_syncd=syncd, unreal_connection=fake)
    r1 = executor.apply(dp, create_snapshot=False, require_safe_only=True)
    r2 = executor.apply(dp, create_snapshot=False, require_safe_only=True)
    assert r1.succeeded == 1
    # Second run should be a no-op for the same operation_id
    assert r2.noop == 1
    assert r2.succeeded == 0


def test_executor_rejects_destructive_without_approval():
    dp = _build_simple_patch()
    dp.intent.risk_hint = "destructive"
    dp.risk_level = "destructive"
    # safety_report needs to be recomputed by the executor
    from server.planning.safety import SafetyChecker
    dp.safety_report = SafetyChecker().check(dp)
    syncd = _MemoryScenSyncd()
    fake = FakeUnrealConnection()
    executor = PatchExecutor(scene_syncd=syncd, unreal_connection=fake)
    report = executor.apply(dp, create_snapshot=False, require_safe_only=False, approve=False)
    assert report.errors and "destructive" in report.errors[0]


def test_executor_creates_snapshot_when_requested():
    dp = _build_simple_patch()
    syncd = _MemoryScenSyncd()
    syncd.responses["/snapshots/create"] = {"success": True, "data": {"id": "scene_snapshot:abc"}}
    fake = FakeUnrealConnection()
    executor = PatchExecutor(scene_syncd=syncd, unreal_connection=fake)
    report = executor.apply(dp, create_snapshot=True)
    assert report.snapshot_id == "scene_snapshot:abc"
    assert syncd.calls_for("/snapshots/create")


def test_scene_edit_apply_safe_invokes_executor(monkeypatch):
    """Integration: scene_edit(mode=apply_safe) goes through the executor."""

    class _Mem:
        def __init__(self):
            self.calls = []
            self.responses = {
                "/snapshots/create": {"success": True, "data": {"id": "scene_snapshot:test"}},
                "/objects/list": {"success": True, "data": {"objects": [
                    {"mcp_id": "torch_01", "kind": "light", "name": "t1", "tags": ["torch"]},
                ]}},
                "/entities/list": {"success": True, "data": {"entities": []}},
                "/components/list": {"success": True, "data": {"components": []}},
                "/assets/list": {"success": True, "data": {"assets": []}},
                "/snapshots/list": {"success": True, "data": {"snapshots": []}},
                "/operations/recent": {"success": True, "data": {"operations": []}},
            }

        def call_scene_syncd(self, path, payload):
            self.calls.append((path, payload))
            return self.responses.get(path, {"success": True, "data": {}})

    mem = _Mem()
    monkeypatch.setattr(dt, "_summarizer_client", lambda: mem)

    fake_unreal = FakeUnrealConnection()
    monkeypatch.setattr(
        "server.planning.patch_executor._default_scene_syncd",
        lambda: mem.call_scene_syncd,
    )
    monkeypatch.setattr(
        "server.planning.patch_executor._default_unreal_connection",
        lambda: fake_unreal,
    )

    res = dt.scene_edit("make this cave creepy", scene_id="cave_test", mode="apply_safe", create_snapshot=True)
    assert res["success"], res
    assert res["snapshot_id"] == "scene_snapshot:test"
    assert res["succeeded"] >= 1

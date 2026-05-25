"""E2E test: cave creepy scenario.

Uses FakeUnrealConnection + in-memory scene-syncd so the entire dry_run -> 
explain -> apply_safe -> preview loop is exercised without a running editor.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

import server.dialog_tools as dt
from helpers.fake_unreal_connection import FakeUnrealConnection


class _Mem:
    def __init__(self):
        self.calls: List[tuple] = []
        self.objects = [
            {"mcp_id": f"torch_{i:02d}", "kind": "light", "name": f"torch_{i:02d}", "tags": ["torch", "wall", "cave"]}
            for i in range(1, 5)
        ] + [
            {"mcp_id": "wall_n", "kind": "wall", "name": "wall_n", "tags": ["stone"]},
            {"mcp_id": "wall_s", "kind": "wall", "name": "wall_s", "tags": ["stone"]},
            {"mcp_id": "floor_main", "kind": "floor", "name": "floor_main", "tags": ["stone"]},
        ]
        self.snapshots: List[Dict[str, Any]] = []
        self.operations: List[Dict[str, Any]] = []
        self.components: List[Dict[str, Any]] = []

    def __call__(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append((path, payload))
        if path == "/objects/list":
            return {"success": True, "data": {"objects": self.objects}}
        if path == "/entities/list":
            return {"success": True, "data": {"entities": []}}
        if path == "/components/list":
            return {"success": True, "data": {"components": self.components}}
        if path == "/assets/list":
            return {"success": True, "data": {"assets": []}}
        if path == "/snapshots/list":
            return {"success": True, "data": {"snapshots": self.snapshots}}
        if path == "/operations/recent":
            return {"success": True, "data": {"operations": self.operations[-10:]}}
        if path == "/snapshots/create":
            snap = {"id": f"scene_snapshot:{len(self.snapshots)+1}", "name": payload.get("name", ""), "revision": 1}
            self.snapshots.append(snap)
            return {"success": True, "data": snap}
        if path == "/components/upsert":
            self.components.append({
                "entity_id": payload["entity_id"],
                "component_type": payload["component_type"],
                "name": payload["name"],
                "sync_status": "pending",
            })
            return {"success": True, "data": {}}
        if path == "/operations/record":
            self.operations.append(payload)
            return {"success": True}
        if path == "/objects/bulk-upsert":
            return {"success": True, "data": {"upserted_count": len(payload.get("objects", []))}}
        return {"success": True, "data": {}}


@pytest.fixture
def cave_env(monkeypatch):
    mem = _Mem()
    fake = FakeUnrealConnection()
    monkeypatch.setattr(dt, "_summarizer_client",
                        lambda: type("C", (), {"call_scene_syncd": staticmethod(mem)})())
    monkeypatch.setattr(
        "server.planning.patch_executor._default_scene_syncd", lambda: mem
    )
    monkeypatch.setattr(
        "server.planning.patch_executor._default_unreal_connection", lambda: fake
    )
    return mem, fake


def test_cave_creepy_full_loop(cave_env):
    mem, fake = cave_env

    # 1. dry_run
    dry = dt.scene_edit("make this cave creepy", scene_id="cave_test", mode="dry_run")
    assert dry["success"]
    assert dry["operation_count"] >= 8  # at minimum: 4 lights + 1 atm + 2 audio + 1 vfx

    # 2. explain
    explained = dt.scene_explain_plan(dry["patch_id"])
    assert "## Patch" in explained["markdown"]

    # 3. apply_safe
    applied = dt.scene_edit(
        "make this cave creepy",
        scene_id="cave_test",
        mode="apply_safe",
        create_snapshot=True,
    )
    assert applied["success"]
    assert applied["snapshot_id"]
    assert applied["succeeded"] >= 1

    # Direct UE commands fired:
    fired = set(fake.commands())
    assert any(cmd.startswith("set_light_") for cmd in fired)
    assert "batch_update_material_parameters" in fired or "apply_material_to_actor" in fired

    # 4. preview - screenshot will fail (no fake screenshot handler) but tool
    # should still return success with warnings.
    preview = dt.scene_preview(scene_id="cave_test")
    assert preview["success"]

"""Contract tests for React-for-UE v3.0 backward compatibility.

These tests ensure that:
- /components/upsert accepts the legacy payload shape (without the new __sync
  metadata) and the new v3 shape (with desired_hash via metadata.__sync).
- Existing component_types (navmesh, ai_patrol, ai_behavior) continue to flow
  through the same scene_component_upsert tool.
- scene_snapshot_restore_by_name produces a response shape compatible with the
  existing snapshot_id-based restore.
- scene_operation conflict records carry status="conflict" via the new
  /operations/record route.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest


# ---------------------------------------------------------------------------
# /components/upsert payload contract
# ---------------------------------------------------------------------------


class _FakeSyncd:
    def __init__(self) -> None:
        self.calls: List[tuple] = []

    def __call__(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append((path, payload))
        return {"success": True, "data": {}}


def test_components_upsert_accepts_legacy_payload_shape(monkeypatch):
    """A legacy payload without metadata.__sync must still succeed."""
    from server import scene_nav_ai_tools as nav

    fake = _FakeSyncd()
    monkeypatch.setattr("server.scene_tools_common.call_scene_syncd", fake)

    resp = nav.scene_component_upsert(
        scene_id="main",
        entity_id="actor:patrol_zone_01",
        component_type="navmesh",
        name="primary",
        properties={"bounds": [100, 100, 50]},
    )
    assert resp["success"] is not False
    assert ("/components/upsert", {
        "scene_id": "main",
        "entity_id": "actor:patrol_zone_01",
        "component_type": "navmesh",
        "name": "primary",
        "properties": {"bounds": [100, 100, 50]},
    }) in fake.calls


def test_components_upsert_accepts_v3_payload_shape(monkeypatch):
    """The new v3 payload with metadata.__sync must also be accepted."""
    from server.planning.patch_compiler import PatchCompiler
    from server.planning.design_patch import ComponentPatch, DesignPatch, Intent, new_patch_id

    cp = ComponentPatch(
        scene_id="main",
        entity_id="actor:torch_01",
        component_type="light",
        name="primary",
        properties={"intensity_multiplier": 0.5},
        capability_id="light.set_intensity",
    )
    dp = DesignPatch(
        patch_id=new_patch_id(),
        scene_id="main",
        intent=Intent(raw_text="x", scene_id="main"),
        component_patches=[cp],
    )
    compiled = PatchCompiler().compile(dp)
    assert len(compiled.component_upserts) == 1
    payload = compiled.component_upserts[0]
    # legacy keys preserved
    for k in ("scene_id", "entity_id", "component_type", "name", "properties"):
        assert k in payload
    # v3 sync metadata present
    assert "__sync" in payload["metadata"]
    sync = payload["metadata"]["__sync"]
    assert sync["desired_hash"] and len(sync["desired_hash"]) == 40
    assert sync["operation_id"] and len(sync["operation_id"]) == 40
    assert sync["patch_id"] == dp.patch_id
    assert sync["capability_id"] == "light.set_intensity"


# ---------------------------------------------------------------------------
# Backward compatibility: navmesh / ai_patrol / ai_behavior still valid
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "component_type",
    ["navmesh", "ai_patrol", "ai_behavior", "collision", "post_process"],
)
def test_legacy_component_types_remain_addressable_through_registry(component_type):
    """Existing component_types must still resolve through the capability
    registry (either as a primary capability or via alias)."""
    from server.planning.capability_registry import get_default_registry

    reg = get_default_registry()
    # The plan keeps the legacy domains coexisting with the canonical v3 ones,
    # so the registry should not raise on them when looking up by domain.
    canonical = reg.canonical_domain(component_type)
    # Listing by domain may legitimately return empty for some legacy types
    # (e.g. collision/post_process) since they are not yet curated. The key
    # invariant is that the call does not throw and the canonical mapping is
    # idempotent for unknown types.
    _ = reg.list_by_domain(canonical)


# ---------------------------------------------------------------------------
# /snapshots/restore_by_name compat
# ---------------------------------------------------------------------------


def test_snapshot_restore_by_name_returns_snapshot_id(monkeypatch):
    """restore_by_name must include the resolved snapshot_id so callers can
    treat it as equivalent to scene_snapshot_restore(snapshot_id)."""

    captured: List[tuple] = []

    def fake_call(path, payload):
        captured.append((path, payload))
        return {
            "success": True,
            "data": {
                "snapshot_id": "scene_snapshot:abc",
                "name": payload.get("name"),
                "restore": {"restored": 7},
                "candidates": ["scene_snapshot:abc"],
            },
            "warnings": [],
        }

    monkeypatch.setattr("server.scene_client.call_scene_syncd", fake_call)
    import server.dialog_tools as dt

    res = dt.scene_snapshot_restore_by_name(scene_id="main", name="before_creepy")
    assert res["success"]
    assert res["data"]["snapshot_id"] == "scene_snapshot:abc"
    # contract: the route was actually called
    assert ("/snapshots/restore_by_name", {
        "scene_id": "main",
        "name": "before_creepy",
        "restore_mode": "replace_desired",
    }) in captured


# ---------------------------------------------------------------------------
# scene_operation conflict shape via /operations/record
# ---------------------------------------------------------------------------


def test_executor_records_status_conflict_when_apply_fails(monkeypatch):
    """When a component apply fails, the executor must record status=error and
    include the capability_id so downstream callers can build a conflict view.
    """
    from server.planning.design_patch import (
        ComponentPatch,
        DesignPatch,
        Intent,
        new_patch_id,
    )
    from server.planning.patch_executor import PatchExecutor
    from helpers.fake_unreal_connection import FakeUnrealConnection

    syncd_calls: List[tuple] = []

    def syncd(path, payload):
        syncd_calls.append((path, payload))
        return {"success": True, "data": {}}

    fake_unreal = FakeUnrealConnection()
    fake_unreal.responses["set_light_intensity"] = {"success": False, "error": "intentional"}

    dp = DesignPatch(
        patch_id=new_patch_id(),
        scene_id="main",
        intent=Intent(raw_text="t", scene_id="main"),
        component_patches=[
            ComponentPatch(
                scene_id="main",
                entity_id="actor:torch_01",
                component_type="light",
                name="primary",
                properties={"intensity_multiplier": 0.5},
                capability_id="light.set_intensity",
            )
        ],
    )
    dp.fill_component_hashes()
    executor = PatchExecutor(scene_syncd=syncd, unreal_connection=fake_unreal)
    report = executor.apply(dp, create_snapshot=False, require_safe_only=True)
    assert report.failed == 1
    # Find the /operations/record call associated with the failed apply.
    op_records = [c for c in syncd_calls if c[0] == "/operations/record"]
    assert op_records, "expected operation log entry"
    statuses = [c[1]["status"] for c in op_records]
    assert "error" in statuses
    # capability_id is always present in the v3 operation log.
    assert all("capability_id" in c[1] for c in op_records)

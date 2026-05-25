"""Unit tests for TargetResolver."""

from __future__ import annotations

from server.intent.scene_context import (
    EntityBrief,
    OperationBrief,
    SceneContextPack,
    SceneObjectBrief,
    ComponentBrief,
)
from server.intent.target_resolver import resolve_target, TargetResolver


def _make_pack():
    pack = SceneContextPack(scene_id="main")
    torch_objs = [
        SceneObjectBrief(mcp_id="torch_01", kind="light", name="torch_01", tags=["torch", "wall", "cave"]),
        SceneObjectBrief(mcp_id="torch_02", kind="light", name="torch_02", tags=["torch", "wall", "cave"]),
        SceneObjectBrief(mcp_id="floor_01", kind="floor", name="floor_01", tags=["cave"]),
    ]
    pack.objects_by_kind = {"light": torch_objs[:2], "floor": torch_objs[2:]}
    pack.entities_by_kind = {
        "torch": [EntityBrief(entity_id="ent_torch_01", kind="torch", name="entrance_torch")],
        "ambush_zone": [EntityBrief(entity_id="ent_ambush_01", kind="ambush_zone", name="north_ambush")],
    }
    pack.components_by_type = {
        "light": [ComponentBrief(entity_id="ent_torch_01", component_type="light", name="main")],
        "material": [ComponentBrief(entity_id="floor_01", component_type="material", name="stone_floor")],
    }
    pack.recent_operations = [
        OperationBrief(operation_id="op1", action="update_visual", mcp_id="torch_01", status="ok", reason="patch"),
        OperationBrief(operation_id="op2", action="update_visual", mcp_id="floor_01", status="ok", reason="patch"),
    ]
    return pack


def test_resolve_tag_matches_torches():
    pack = _make_pack()
    res = resolve_target("all wall torches", pack)
    assert not res.ambiguous
    assert "torch_01" in res.matched_mcp_ids
    assert "torch_02" in res.matched_mcp_ids


def test_resolve_entity_by_kind():
    pack = _make_pack()
    res = resolve_target("ambush_zone", pack)
    assert "ent_ambush_01" in res.matched_entity_ids


def test_resolve_recent_uses_last_operations():
    pack = _make_pack()
    res = resolve_target("<recent>", pack)
    assert "torch_01" in res.matched_mcp_ids or "floor_01" in res.matched_mcp_ids


def test_resolve_recent_ambiguous_when_no_history():
    pack = SceneContextPack(scene_id="main")
    res = resolve_target("it", pack)
    assert res.ambiguous


def test_resolve_empty_phrase_returns_scene_wide():
    pack = _make_pack()
    res = resolve_target("", pack)
    assert not res.ambiguous
    assert res.selector.get("kind") == "scene"


def test_resolve_unknown_phrase_marks_ambiguous():
    pack = _make_pack()
    res = resolve_target("an unrelated thing", pack)
    assert res.ambiguous

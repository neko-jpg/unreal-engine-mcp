"""Snapshot-style unit tests for experts and mood profile loading."""

from __future__ import annotations

from typing import List

import pytest

from server.experts import (
    AtmosphereExpert,
    AudioExpert,
    LightingExpert,
    MaterialExpert,
    PostProcessExpert,
    VFXExpert,
    default_router,
    list_profiles,
    load_profile,
)
from server.intent.intent_types import Intent
from server.intent.scene_context import (
    ComponentBrief,
    EntityBrief,
    OperationBrief,
    SceneContextPack,
    SceneObjectBrief,
)
from server.planning.design_patch import ComponentPatch, AssetPatch, DirectCommandPatch


@pytest.fixture
def cave_pack():
    pack = SceneContextPack(scene_id="cave_test")
    pack.objects_by_kind = {
        "light": [
            SceneObjectBrief(mcp_id="torch_01", kind="light", name="torch_01", tags=["torch", "wall"]),
            SceneObjectBrief(mcp_id="torch_02", kind="light", name="torch_02", tags=["torch"]),
        ],
        "floor": [
            SceneObjectBrief(mcp_id="floor_main", kind="floor", name="floor_main", tags=["stone"]),
        ],
        "wall": [
            SceneObjectBrief(mcp_id="wall_n", kind="wall", name="wall_n", tags=["stone"]),
        ],
    }
    pack.entities_by_kind = {"torch": []}
    pack.components_by_type = {}
    pack.recent_operations = []
    pack.object_count = 4
    return pack


def _intent_creepy():
    return Intent(
        raw_text="make this cave creepy",
        scene_id="cave_test",
        action="modify",
        domains=["cave", "lighting", "material", "atmosphere", "audio", "vfx", "post_process"],
        mood="creepy",
    )


def test_creepy_profile_loads():
    profile = load_profile("creepy")
    assert profile is not None
    assert profile.lighting["intensity_multiplier"] < 1.0
    assert profile.material["roughness"] >= 0.9


def test_all_5_profiles_present():
    names = list_profiles()
    for n in ["creepy", "heroic", "moonlit", "osaka_castle", "cinematic_warm"]:
        assert n in names


def test_lighting_expert_emits_one_patch_per_light(cave_pack):
    intent = _intent_creepy()
    profile = load_profile("creepy")
    patches = LightingExpert().propose(intent, cave_pack, profile)
    assert len(patches) == 2
    assert all(isinstance(p, ComponentPatch) for p in patches)
    for p in patches:
        assert p.component_type == "light"
        assert p.properties["intensity_multiplier"] == pytest.approx(0.35)


def test_material_expert_emits_asset_and_per_actor_patches(cave_pack):
    intent = _intent_creepy()
    profile = load_profile("creepy")
    patches = MaterialExpert().propose(intent, cave_pack, profile)
    asset_count = sum(1 for p in patches if isinstance(p, AssetPatch))
    comp_count = sum(1 for p in patches if isinstance(p, ComponentPatch))
    assert asset_count == 1
    assert comp_count == 2  # floor_main + wall_n


def test_atmosphere_expert_emits_singleton(cave_pack):
    intent = _intent_creepy()
    profile = load_profile("creepy")
    patches = AtmosphereExpert().propose(intent, cave_pack, profile)
    assert len(patches) == 1
    assert patches[0].entity_id == "atmosphere:scene"


def test_audio_expert_emits_one_per_ambient(cave_pack):
    intent = _intent_creepy()
    profile = load_profile("creepy")
    patches = AudioExpert().propose(intent, cave_pack, profile)
    # creepy.yaml has 2 ambient sounds: drip, low_wind
    assert len(patches) == 2


def test_vfx_expert_emits_dust_and_embers(cave_pack):
    intent = _intent_creepy()
    profile = load_profile("creepy")
    patches = VFXExpert().propose(intent, cave_pack, profile)
    names = {p.name for p in patches}
    assert names == {"dust", "embers"}


def test_postprocess_expert_emits_spawn_and_apply(cave_pack):
    intent = _intent_creepy()
    profile = load_profile("creepy")
    patches = PostProcessExpert().propose(intent, cave_pack, profile)
    assert [p.command for p in patches] == ["spawn_post_process_volume", "set_post_process_volume"]
    assert all(isinstance(p, DirectCommandPatch) for p in patches)


def test_router_returns_aggregated_patches(cave_pack):
    intent = _intent_creepy()
    patches = default_router().propose_all(intent, cave_pack)
    # 3 cave + 2 lights + 1 asset + 2 materials + 1 atmosphere + 2 audio + 2 vfx + 2 post-process = 15
    assert len(patches) == 15

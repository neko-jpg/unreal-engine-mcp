"""Integration test: a single DesignPatch with mixed component types is
correctly split between the Rust path (material/light) and the Python path
(atmosphere/audio/vfx) by PatchCompiler. The Python PatchExecutor still
exercises every component_type in MVP, but the compiler must mark
material/light as rust-eligible so PR7's Rust applier can take over.
"""

from __future__ import annotations

from typing import List

import pytest

from helpers.fake_unreal_connection import FakeUnrealConnection
from server.planning.design_patch import (
    ComponentPatch,
    DesignPatch,
    Intent,
    new_patch_id,
)
from server.planning.patch_compiler import PatchCompiler
from server.planning.patch_executor import PatchExecutor


def _mixed_patch() -> DesignPatch:
    dp = DesignPatch(
        patch_id=new_patch_id(),
        scene_id="hybrid_test",
        intent=Intent(raw_text="hybrid", scene_id="hybrid_test", mood="creepy"),
        component_patches=[
            ComponentPatch(
                scene_id="hybrid_test",
                entity_id="actor:torch_01",
                component_type="light",
                name="primary",
                properties={"intensity_multiplier": 0.5, "actor_mcp_id": "torch_01"},
                capability_id="light.set_intensity",
            ),
            ComponentPatch(
                scene_id="hybrid_test",
                entity_id="actor:wall_n",
                component_type="material",
                name="slot_0",
                properties={
                    "actor_mcp_id": "wall_n",
                    "material_slot": 0,
                    "parameters": [{"name": "Roughness", "type": "scalar", "value": 0.9}],
                },
                capability_id="material.batch_update_parameters",
            ),
            ComponentPatch(
                scene_id="hybrid_test",
                entity_id="atmosphere:scene",
                component_type="atmosphere",
                name="primary",
                properties={"fog_density": 2.0},
                capability_id="atmosphere.set_height_fog",
            ),
            ComponentPatch(
                scene_id="hybrid_test",
                entity_id="audio:scene",
                component_type="audio",
                name="ambient_drip",
                properties={"sound_name": "drip", "volume": 0.4},
                capability_id="audio.spawn_ambient",
            ),
            ComponentPatch(
                scene_id="hybrid_test",
                entity_id="vfx:scene",
                component_type="vfx",
                name="dust",
                properties={"system_path": "/Game/MCP/VFX/NS_Dust", "density": 0.4},
                capability_id="vfx.add_niagara_component",
            ),
        ],
    )
    dp.fill_component_hashes()
    return dp


class _Memory:
    def __init__(self) -> None:
        self.calls: List[tuple] = []

    def __call__(self, path, payload):
        self.calls.append((path, payload))
        return {"success": True, "data": {}}


def test_compiler_marks_material_and_light_as_rust_eligible():
    compiled = PatchCompiler().compile(_mixed_patch())
    rust_types = {entry["component_type"] for entry in compiled.rust_apply_keys}
    assert rust_types == {"material", "light"}, (
        "PR7 Rust component_applier should only own material+light; "
        f"got {rust_types}"
    )


def test_compiler_python_apply_covers_all_v3_component_types():
    compiled = PatchCompiler().compile(_mixed_patch())
    py_types = {cp.component_type for cp, _ in compiled.python_apply}
    assert py_types == {"material", "light", "atmosphere", "audio", "vfx"}


def test_executor_drives_python_handled_types_via_direct_ue_commands():
    dp = _mixed_patch()
    syncd = _Memory()
    fake = FakeUnrealConnection()
    PatchExecutor(scene_syncd=syncd, unreal_connection=fake).apply(
        dp, create_snapshot=False, require_safe_only=True
    )
    fired = set(fake.commands())
    # Atmosphere / audio / vfx must execute via the Python path in MVP.
    assert "set_height_fog_properties" in fired
    assert "spawn_ambient_sound" in fired
    assert "add_niagara_component" in fired


def test_hybrid_executor_writes_one_components_upsert_per_component():
    dp = _mixed_patch()
    syncd = _Memory()
    fake = FakeUnrealConnection()
    PatchExecutor(scene_syncd=syncd, unreal_connection=fake).apply(
        dp, create_snapshot=False, require_safe_only=True
    )
    upserts = [c for c in syncd.calls if c[0] == "/components/upsert"]
    assert len(upserts) == 5

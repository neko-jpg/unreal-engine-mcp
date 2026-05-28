"""Unit tests for server.planning.capability_registry."""

import json
import pytest

from server.planning.capability_registry import (
    Capability,
    CapabilityRegistry,
    get_default_registry,
    reset_default_registry,
)


def test_default_registry_contains_core_capabilities():
    reg = get_default_registry()
    for cap_id in [
        "material.batch_update_parameters",
        "material.apply_to_actor",
        "light.set_intensity",
        "atmosphere.set_height_fog",
        "audio.spawn_ambient",
        "vfx.add_niagara_component",
        "viewport.focus_actor",
        "render.take_screenshot",
        "scene.snapshot_create",
        "scene.snapshot_restore",
        "scene.snapshot_restore_by_name",
        "scene.components_upsert",
        "navmesh.upsert",
        "ai_patrol.upsert",
        "ai_behavior.upsert",
        "cave.audit",
        "cave.generate_or_refine",
        "procedural.sdf_mesh",
        "pcg.configure_surface_sampler",
        "mesh.collision_generate",
        "validation.collision",
        "postprocess.spawn",
        "postprocess.apply",
    ]:
        assert cap_id in reg, f"missing capability: {cap_id}"


def test_alias_resolution_for_material_update_parameters():
    reg = get_default_registry()
    primary = reg.require("material.batch_update_parameters")
    aliased = reg.require("material.update_parameters")
    assert primary.command == aliased.command


def test_fog_domain_maps_to_atmosphere():
    reg = get_default_registry()
    caps = reg.list_by_domain("fog")
    assert any(c.capability_id.startswith("atmosphere.") for c in caps)


def test_register_duplicate_raises():
    reset_default_registry()
    reg = CapabilityRegistry()
    reg.register(Capability("x.y", "material", "direct_ue", "foo"))
    with pytest.raises(ValueError):
        reg.register(Capability("x.y", "material", "direct_ue", "bar"))


def test_to_json_round_trip():
    reg = get_default_registry()
    payload = json.loads(reg.to_json())
    ids = [c["capability_id"] for c in payload["capabilities"]]
    assert len(ids) == len(set(ids))
    assert "light.set_intensity" in ids


def test_canonical_domain_handles_aliases_and_passthrough():
    reg = get_default_registry()
    assert reg.canonical_domain("fog") == "atmosphere"
    assert reg.canonical_domain("material") == "material"


def test_cave_capabilities_use_existing_command_names():
    reg = get_default_registry()
    assert reg.require("mesh.collision_generate").command == "generate_collision"
    assert reg.require("mesh.nanite_enable").command == "set_nanite_settings"
    assert reg.require("postprocess.apply").command == "set_post_process_volume"

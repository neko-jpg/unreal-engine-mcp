"""Capability registry for React-for-UE v3.0.

Indexes every callable surface the experts can use:
- Python @mcp.tool() functions (high-level)
- C++ UE command names (low-level)
- scene-syncd HTTP endpoints (durable component / object writes)

Experts must NOT hard-code UE command names. They request a capability_id
through the registry, which returns a Capability with transport, command,
durable_model, risk, etc.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional

Transport = Literal["direct_ue", "component_apply", "scene_syncd", "python_tool"]


@dataclass
class Capability:
    capability_id: str
    domain: str
    transport: Transport
    command: str
    durable_model: Optional[str] = None
    risk: Literal["safe", "review", "destructive"] = "safe"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_BUILTIN_CAPABILITIES: List[Capability] = [
    Capability("material.batch_update_parameters", "material", "component_apply",
               "batch_update_material_parameters", "scene_component:material", "safe",
               "Update many material instance parameters in one call.",
               aliases=["material.update_parameters"]),
    Capability("material.create_instance", "material", "component_apply",
               "create_material_instance", "scene_asset:material_instance", "safe",
               "Create a new material instance asset."),
    Capability("material.apply_to_actor", "material", "component_apply",
               "apply_material_to_actor", "scene_component:material", "safe"),
    Capability("material.set_scalar", "material", "direct_ue",
               "set_material_scalar_parameter", "scene_component:material", "safe"),
    Capability("material.set_vector", "material", "direct_ue",
               "set_material_vector_parameter", "scene_component:material", "safe"),
    Capability("material.set_mesh_color", "material", "direct_ue",
               "set_mesh_material_color", "scene_component:material", "safe",
               "Quick per-actor color override (fallback)."),
    Capability("light.set_intensity", "light", "component_apply",
               "set_light_intensity", "scene_component:light", "safe"),
    Capability("light.set_color", "light", "component_apply",
               "set_light_color", "scene_component:light", "safe"),
    Capability("light.set_temperature", "light", "component_apply",
               "set_light_temperature", "scene_component:light", "safe"),
    Capability("light.set_attenuation_radius", "light", "component_apply",
               "set_light_attenuation_radius", "scene_component:light", "safe"),
    Capability("light.set_shadow_enabled", "light", "component_apply",
               "set_light_shadow_enabled", "scene_component:light", "safe"),
    Capability("light.set_volumetric_scattering", "light", "component_apply",
               "set_light_volumetric_scattering", "scene_component:light", "safe"),
    Capability("atmosphere.set_height_fog", "atmosphere", "direct_ue",
               "set_height_fog_properties", "scene_component:atmosphere", "safe"),
    Capability("atmosphere.set_sky_atmosphere", "atmosphere", "direct_ue",
               "set_sky_atmosphere_properties", "scene_component:atmosphere", "safe"),
    Capability("atmosphere.set_volumetric_fog", "atmosphere", "direct_ue",
               "set_volumetric_fog", "scene_component:atmosphere", "safe"),
    Capability("audio.spawn_ambient", "audio", "direct_ue",
               "spawn_ambient_sound", "scene_component:audio", "safe"),
    Capability("audio.add_component", "audio", "direct_ue",
               "add_audio_component", "scene_component:audio", "safe"),
    Capability("audio.set_attenuation", "audio", "direct_ue",
               "set_sound_attenuation", "scene_component:audio", "safe"),
    Capability("vfx.add_niagara_component", "vfx", "direct_ue",
               "add_niagara_component", "scene_component:vfx", "safe"),
    Capability("vfx.set_niagara_user_parameter", "vfx", "direct_ue",
               "set_niagara_user_parameter", "scene_component:vfx", "safe"),
    Capability("vfx.set_niagara_color", "vfx", "direct_ue",
               "set_niagara_color", "scene_component:vfx", "safe"),
    Capability("viewport.focus_actor", "viewport", "direct_ue",
               "viewport_action", None, "safe",
               "viewport_action with mode=focus_actor."),
    Capability("render.take_screenshot", "render", "direct_ue",
               "take_screenshot", None, "safe"),
    Capability("navmesh.upsert", "navmesh", "scene_syncd",
               "/components/upsert", "scene_component:navmesh", "safe"),
    Capability("ai_patrol.upsert", "ai_patrol", "scene_syncd",
               "/components/upsert", "scene_component:ai_patrol", "safe"),
    Capability("ai_behavior.upsert", "ai_behavior", "scene_syncd",
               "/components/upsert", "scene_component:ai_behavior", "safe"),
    Capability("scene.snapshot_create", "object", "scene_syncd",
               "/snapshots/create", None, "safe"),
    Capability("scene.snapshot_restore", "object", "scene_syncd",
               "/snapshots/restore", None, "review"),
    Capability("scene.snapshot_restore_by_name", "object", "scene_syncd",
               "/snapshots/restore_by_name", None, "review"),
    Capability("scene.components_upsert", "object", "scene_syncd",
               "/components/upsert", None, "safe"),
    Capability("scene.components_list", "object", "scene_syncd",
               "/components/list", None, "safe"),
    Capability("scene.components_delete", "object", "scene_syncd",
               "/components/delete", None, "review"),
    Capability("scene.objects_bulk_upsert", "object", "scene_syncd",
               "/objects/bulk-upsert", None, "safe"),
    Capability("scene.objects_delete", "object", "scene_syncd",
               "/objects/delete", None, "destructive"),
    Capability("scene.operations_record", "object", "scene_syncd",
               "/operations/record", None, "safe"),
    Capability("scene.operations_recent", "object", "scene_syncd",
               "/operations/recent", None, "safe"),

    # Cave domain
    Capability("cave.audit", "cave", "python_tool",
               "scene_cave_audit", None, "safe",
               "Audit scene structure as cave geometry."),
    Capability("cave.generate_sdf", "cave", "python_tool",
               "scene_create_cave_sdf", None, "safe",
               "Generate SDF cave geometry from skeleton graph."),
    Capability("cave.apply_pcg", "cave", "python_tool",
               "scene_apply_cave_pcg", None, "safe",
               "Apply PCG detail scatter to cave surfaces."),
    Capability("cave.validate", "cave", "python_tool",
               "scene_validate_cave", None, "safe",
               "Validate cave walkability and structure."),
    Capability("cave.refine_geometry", "cave", "python_tool",
               "scene_refine_cave_geometry", None, "safe",
               "Refine cave geometry parameters based on validation."),
    Capability("cave.generate_or_refine", "cave", "python_tool",
               "scene_cave_generate_or_refine", None, "safe",
               "Full cave orchestrator: audit, generate, mood, validate, refine."),

    # Procedural domain
    Capability("procedural.sdf_mesh", "procedural", "python_tool",
               "scene_create_sdf_mesh", None, "safe",
               "Generate mesh from SDF tree via marching cubes."),
    Capability("procedural.wfc_grid", "procedural", "python_tool",
               "scene_create_wfc_grid", None, "safe",
               "Run Wave Function Collapse on a tile grid."),
    Capability("procedural.lsystem_spline", "procedural", "python_tool",
               "scene_create_lsystem_spline", None, "safe",
               "Generate spline from L-System grammar."),
    Capability("procedural.mesh_upsert", "procedural", "python_tool",
               "scene_upsert_procedural_mesh", None, "safe",
               "Upsert raw vertex/index mesh data."),
    Capability("procedural.wfc_semantic", "procedural", "python_tool",
               "scene_wfc_to_semantic_layout", None, "safe",
               "Convert WFC grid to semantic scene layout."),

    # Mesh editing domain
    Capability("mesh.voxel_remesh", "mesh_editing", "direct_ue",
               "mesh_voxel_remesh", None, "safe",
               "Voxel-based mesh remeshing."),
    Capability("mesh.collision_generate", "mesh_editing", "direct_ue",
               "generate_collision", None, "safe",
               "Generate collision geometry for static mesh."),
    Capability("mesh.nanite_enable", "mesh_editing", "direct_ue",
               "set_nanite_settings", None, "safe",
               "Enable/disable Nanite on static mesh."),
    Capability("mesh.uv_unwrap", "mesh_editing", "direct_ue",
               "mesh_uv_unwrap", None, "safe",
               "UV unwrap a static mesh."),

    # Navigation domain
    Capability("nav.validate", "navigation", "direct_ue",
               "run_navigation_validation", None, "safe",
               "Validate NavMesh walkability."),
    Capability("nav.rebuild", "navigation", "direct_ue",
               "run_navigation_validation", None, "safe",
               "Request NavMesh rebuild."),

    # Validation domain
    Capability("validation.collision", "validation", "direct_ue",
               "run_collision_validation", None, "safe",
               "Validate collision geometry."),
    Capability("validation.screenshot", "validation", "direct_ue",
               "run_gameplay_screenshot_test", None, "safe",
               "Run gameplay screenshot test."),

    # PCG domain
    Capability("pcg.execute_graph", "pcg", "direct_ue",
               "execute_pcg_graph", None, "safe",
               "Execute a PCG graph."),
    Capability("pcg.create_graph", "pcg", "direct_ue",
               "create_pcg_graph", None, "safe",
               "Create a new PCG graph asset."),
    Capability("pcg.add_component", "pcg", "direct_ue",
               "add_pcg_component", None, "safe",
               "Add PCG component to an actor."),
    Capability("pcg.configure_surface_sampler", "pcg", "direct_ue",
               "configure_pcg_surface_sampler", None, "safe",
               "Configure a PCG graph surface sampler."),
    Capability("pcg.configure_static_mesh_spawner", "pcg", "direct_ue",
               "configure_pcg_static_mesh_spawner", None, "safe",
               "Configure a PCG graph static mesh spawner."),

    # Post process domain
    Capability("postprocess.spawn", "post_process", "direct_ue",
               "spawn_post_process_volume", None, "safe",
               "Spawn an unbound or bounded post-process volume."),
    Capability("postprocess.apply", "post_process", "direct_ue",
               "set_post_process_volume", None, "safe",
               "Configure a post-process volume."),
    Capability("postprocess.set_bloom", "post_process", "direct_ue",
               "set_post_process_volume", None, "safe",
               "Set bloom intensity."),
    Capability("postprocess.set_exposure", "post_process", "direct_ue",
               "set_post_process_volume", None, "safe",
               "Set exposure compensation."),
    Capability("postprocess.set_saturation", "post_process", "direct_ue",
               "set_post_process_volume", None, "safe",
               "Set color saturation."),
    Capability("postprocess.set_contrast", "post_process", "direct_ue",
               "set_post_process_volume", None, "safe",
               "Set contrast."),

    # Landscape domain
    Capability("landscape.create", "landscape", "python_tool",
               "create_landscape", None, "safe",
               "Create a new landscape terrain."),
    Capability("landscape.flatten", "landscape", "python_tool",
               "landscape_flatten", None, "safe",
               "Flatten terrain under structures."),
    Capability("landscape.sculpt", "landscape", "python_tool",
               "landscape_sculpt", None, "safe",
               "Sculpt terrain with brush strokes."),

    # Architecture domain
    Capability("architecture.house", "architecture", "python_tool",
               "construct_house", None, "safe",
               "Construct a house building."),
    Capability("architecture.mansion", "architecture", "python_tool",
               "construct_mansion", None, "safe",
               "Construct a mansion."),
    Capability("architecture.castle", "architecture", "python_tool",
               "create_castle_fortress", None, "safe",
               "Create a castle or fortress."),
    Capability("architecture.tower", "architecture", "python_tool",
               "create_tower", None, "safe",
               "Create a tower or spire."),
    Capability("architecture.bridge", "architecture", "python_tool",
               "create_suspension_bridge", None, "safe",
               "Create a suspension bridge."),
    Capability("architecture.wall", "architecture", "python_tool",
               "create_wall", None, "safe",
               "Create a wall or barrier."),
    Capability("architecture.pyramid", "architecture", "python_tool",
               "create_pyramid", None, "safe",
               "Create a pyramid or ziggurat."),
    Capability("architecture.maze", "architecture", "python_tool",
               "create_maze", None, "safe",
               "Create a maze or labyrinth."),
    Capability("architecture.town", "architecture", "python_tool",
               "create_town", None, "safe",
               "Create a town or settlement."),
    Capability("architecture.aqueduct", "architecture", "python_tool",
               "create_aqueduct", None, "safe",
               "Create an aqueduct or canal."),
]


_DOMAIN_ALIAS: Dict[str, str] = {
    "fog": "atmosphere",
    "sky": "atmosphere",
    "ambient_sound": "audio",
    "sfx": "audio",
    "niagara": "vfx",
    "particle": "vfx",
    "post_fx": "post_process",
    "post_process_volume": "post_process",
}


class CapabilityRegistry:
    def __init__(self, capabilities: Optional[List[Capability]] = None) -> None:
        self._by_id: Dict[str, Capability] = {}
        self._by_domain: Dict[str, List[Capability]] = {}
        self._primary_ids: List[str] = []
        for cap in capabilities or []:
            self.register(cap)

    def register(self, cap: Capability) -> None:
        if cap.capability_id in self._by_id:
            raise ValueError(f"duplicate capability id: {cap.capability_id}")
        self._by_id[cap.capability_id] = cap
        self._primary_ids.append(cap.capability_id)
        self._by_domain.setdefault(cap.domain, []).append(cap)
        for alias in cap.aliases:
            if alias in self._by_id:
                raise ValueError(f"alias collides with existing capability: {alias}")
            self._by_id[alias] = cap

    def get(self, capability_id: str) -> Optional[Capability]:
        return self._by_id.get(capability_id)

    def require(self, capability_id: str) -> Capability:
        cap = self.get(capability_id)
        if cap is None:
            raise KeyError(f"unknown capability id: {capability_id}")
        return cap

    def list_by_domain(self, domain: str) -> List[Capability]:
        canonical = _DOMAIN_ALIAS.get(domain, domain)
        return list(self._by_domain.get(canonical, []))

    def list_all(self) -> List[Capability]:
        return [self._by_id[pid] for pid in self._primary_ids]

    def canonical_domain(self, domain: str) -> str:
        return _DOMAIN_ALIAS.get(domain, domain)

    def __contains__(self, capability_id: str) -> bool:
        return capability_id in self._by_id

    def __len__(self) -> int:
        return len(self._primary_ids)

    def dump(self) -> List[Dict[str, Any]]:
        return [cap.to_dict() for cap in self.list_all()]

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps({"capabilities": self.dump()}, indent=indent, sort_keys=True)


_default_registry: Optional[CapabilityRegistry] = None


def get_default_registry() -> CapabilityRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = CapabilityRegistry(list(_BUILTIN_CAPABILITIES))
    return _default_registry


def reset_default_registry() -> None:
    global _default_registry
    _default_registry = None

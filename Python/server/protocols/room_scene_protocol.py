"""Room scene protocol."""

from __future__ import annotations

from server.protocols.base_scene_protocol import SceneTypeProtocol
from server.quality.quality_gate import ROOM_QUALITY_GATES


ROOM_PROTOCOL = SceneTypeProtocol(
    protocol_id="scene.room.v1",
    scene_type="room",
    anchors={
        "origin_strategy": "room_bounds_center",
        "forward_strategy": "doorway_to_room_center",
        "scale_strategy": "bounds_radius",
    },
    required_shots=[
        "doorway_wide",
        "corner_1",
        "corner_2",
        "human_eye_level",
        "ceiling_light",
        "floor_layout",
        "hero_composition",
        "diagnostic_unlit",
    ],
    required_metadata=["actors", "materials", "lights", "bounds", "walkable_area"],
    semantic_parts=["floor", "wall", "ceiling", "furniture", "windows", "lights", "walkable_area"],
    quality_gates=ROOM_QUALITY_GATES,
    metric_weights={
        "semantic_score": 0.15,
        "shape_score": 0.10,
        "composition_score": 0.18,
        "detail_score": 0.12,
        "material_score": 0.15,
        "lighting_score": 0.12,
        "topology_score": 0.05,
        "technical_score": 0.08,
        "performance_score": 0.05,
    },
    refinement_actions={
        "too_dark": {"agent": "lighting_domain", "operation": "increase_room_lighting"},
        "too_empty": {"agent": "architecture_domain", "operation": "add_furniture"},
        "default_material": {"agent": "material_domain", "operation": "apply_room_materials"},
    },
)

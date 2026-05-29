"""Cave scene protocol."""

from __future__ import annotations

from server.protocols.base_scene_protocol import SceneTypeProtocol
from server.quality.quality_gate import CAVE_QUALITY_GATES


CAVE_PROTOCOL = SceneTypeProtocol(
    protocol_id="scene.cave.v1",
    scene_type="cave",
    anchors={
        "origin_strategy": "bounds_center",
        "forward_strategy": "entrance_to_deepest_or_pca",
        "scale_strategy": "bounds_radius",
    },
    required_shots=[
        "entrance_wide",
        "main_axis_forward",
        "main_axis_reverse",
        "low_angle_scale",
        "ceiling_up",
        "floor_down",
        "left_wall_close",
        "right_wall_close",
        "branch_view",
        "hero_composition",
        "diagnostic_unlit",
        "diagnostic_depth_or_normal",
    ],
    required_metadata=["actors", "meshes", "materials", "lights", "pcg", "bounds"],
    semantic_parts=["entrance", "main_tunnel", "ceiling", "wall", "floor", "branch", "chamber", "detail_objects"],
    quality_gates=CAVE_QUALITY_GATES,
    metric_weights={
        "semantic_score": 0.18,
        "shape_score": 0.18,
        "composition_score": 0.12,
        "detail_score": 0.14,
        "material_score": 0.12,
        "lighting_score": 0.10,
        "topology_score": 0.08,
        "technical_score": 0.05,
        "performance_score": 0.03,
    },
)

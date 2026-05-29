"""City scene protocol."""

from __future__ import annotations

from server.protocols.base_scene_protocol import SceneTypeProtocol
from server.quality.quality_gate import CITY_QUALITY_GATES


CITY_PROTOCOL = SceneTypeProtocol(
    protocol_id="scene.city.v1",
    scene_type="city",
    anchors={
        "origin_strategy": "street_or_intersection_center",
        "forward_strategy": "street_axis_or_pca",
        "scale_strategy": "bounds_radius",
    },
    required_shots=[
        "street_forward",
        "intersection_wide",
        "building_facade_close",
        "sidewalk_human_scale",
        "skyline",
        "alley",
        "traffic_or_props",
        "diagnostic_depth",
    ],
    required_metadata=["actors", "buildings", "materials", "lights", "bounds", "navigation"],
    semantic_parts=["roads", "sidewalks", "buildings", "windows", "props", "lights", "signage", "navigation"],
    quality_gates=CITY_QUALITY_GATES,
    metric_weights={
        "semantic_score": 0.18,
        "shape_score": 0.08,
        "composition_score": 0.15,
        "detail_score": 0.14,
        "material_score": 0.12,
        "lighting_score": 0.10,
        "topology_score": 0.08,
        "technical_score": 0.08,
        "performance_score": 0.07,
    },
    refinement_actions={
        "too_empty": {"agent": "architecture_domain", "operation": "add_buildings"},
        "no_roads": {"agent": "architecture_domain", "operation": "generate_road_network"},
        "default_material": {"agent": "material_domain", "operation": "apply_city_materials"},
    },
)

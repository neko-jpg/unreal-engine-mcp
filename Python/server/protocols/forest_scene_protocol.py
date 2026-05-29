"""Forest scene protocol."""

from __future__ import annotations

from server.protocols.base_scene_protocol import SceneTypeProtocol
from server.quality.quality_gate import FOREST_QUALITY_GATES


FOREST_PROTOCOL = SceneTypeProtocol(
    protocol_id="scene.forest.v1",
    scene_type="forest",
    anchors={
        "origin_strategy": "bounds_center",
        "forward_strategy": "path_axis_or_pca",
        "scale_strategy": "bounds_radius",
    },
    required_shots=[
        "path_forward",
        "canopy_up",
        "ground_detail",
        "tree_density_left",
        "tree_density_right",
        "clearing_wide",
        "hero_composition",
        "diagnostic_depth",
    ],
    required_metadata=["actors", "foliage", "materials", "lights", "bounds"],
    semantic_parts=["trees", "canopy", "ground_cover", "rocks", "path", "fog", "sky_visibility"],
    quality_gates=FOREST_QUALITY_GATES,
    metric_weights={
        "semantic_score": 0.20,
        "shape_score": 0.08,
        "composition_score": 0.15,
        "detail_score": 0.18,
        "material_score": 0.10,
        "lighting_score": 0.10,
        "topology_score": 0.05,
        "technical_score": 0.07,
        "performance_score": 0.07,
    },
    refinement_actions={
        "too_sparse": {"agent": "foliage_domain", "operation": "increase_tree_density"},
        "no_canopy": {"agent": "foliage_domain", "operation": "add_canopy_cover"},
        "no_ground_cover": {"agent": "landscape_domain", "operation": "add_ground_foliage"},
    },
)

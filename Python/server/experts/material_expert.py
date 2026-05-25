"""MaterialExpert - emits ComponentPatch(material) entries.

Hybrid path: material is component_apply (Rust applier).
"""

from __future__ import annotations

from typing import Any, List, Optional

from server.experts.base_expert import BaseDomainExpert
from server.experts.mood_profiles import MoodProfile
from server.intent.intent_types import Intent
from server.intent.scene_context import SceneContextPack
from server.planning.design_patch import AssetPatch, ComponentPatch


class MaterialExpert(BaseDomainExpert):
    domain = "material"

    def propose(
        self,
        intent: Intent,
        context: SceneContextPack,
        profile: Optional[MoodProfile],
    ) -> List[Any]:
        params = (profile.material if profile else {}) or {}
        if not params:
            return []

        base_color = params.get("base_color_bias", [1.0, 1.0, 1.0, 1.0])
        roughness = params.get("roughness")
        metallic = params.get("metallic")
        wetness = params.get("wetness")

        # Stone-y candidates: floor/wall/stone tagged actors.
        candidates = []
        for kind, items in context.objects_by_kind.items():
            if kind.lower() in {"floor", "wall", "ceiling", "stone", "rock", "static_mesh"}:
                candidates.extend(items)

        if not candidates:
            return []

        mood = intent.mood or "default"
        material_asset_id = f"mi_{mood}_stone"

        # First, propose the shared material instance asset.
        patches: List[Any] = [
            AssetPatch(
                scene_id=intent.scene_id,
                asset_id=material_asset_id,
                kind="material_instance",
                properties={
                    "parent": "/Game/MCP/Materials/M_Stone",
                    "parameters": {
                        "BaseColor": base_color,
                        **({"Roughness": float(roughness)} if roughness is not None else {}),
                        **({"Metallic": float(metallic)} if metallic is not None else {}),
                        **({"Wetness": float(wetness)} if wetness is not None else {}),
                    },
                },
                reason=f"Material instance for mood {mood}",
            )
        ]

        for obj in candidates:
            actor_name = obj.name or obj.mcp_id
            properties = {
                "actor_mcp_id": obj.mcp_id,
                "actor_name": actor_name,
                "material_path": "/Engine/BasicShapes/BasicShapeMaterial",
                "material_slot": 0,
                "instance_id": material_asset_id,
                "parameters": [
                    {"name": "BaseColor", "type": "vector", "value": list(base_color)},
                ],
            }
            if roughness is not None:
                properties["parameters"].append(
                    {"name": "Roughness", "type": "scalar", "value": float(roughness)}
                )
            if metallic is not None:
                properties["parameters"].append(
                    {"name": "Metallic", "type": "scalar", "value": float(metallic)}
                )
            if wetness is not None:
                properties["parameters"].append(
                    {"name": "Wetness", "type": "scalar", "value": float(wetness)}
                )
            patches.append(
                ComponentPatch(
                    scene_id=intent.scene_id,
                    entity_id=f"actor:{obj.mcp_id}",
                    component_type="material",
                    name=f"slot_0_{mood}",
                    properties=properties,
                    capability_id="material.apply_to_actor",
                    reason=f"Apply {mood} stone material to {obj.mcp_id}",
                )
            )
        return patches

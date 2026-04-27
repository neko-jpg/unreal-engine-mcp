import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from server.specs.actor_spec import ActorSpec
from server.specs.asset_resolver import AssetResolver
from server.specs.asset_spec import AssetSpec
from server.specs.entity_spec import EntitySpec
from server.specs.realization_spec import RealizationPolicy, RealizationSpec
from server.specs.relation_spec import RelationSpec


@dataclass
class CostEstimate:
    actor_count: int = 0
    estimated_draw_calls: int = 0
    estimated_memory_mb: float = 0.0
    estimated_sync_time_ms: float = 0.0


@dataclass
class SpecGraph:
    """A graph of semantic specs produced by generators.

    Contains entities, actors, relations, assets, and realizations.
    Generators produce this; sinks and appliers consume it.
    """

    entities: List[EntitySpec] = field(default_factory=list)
    actors: List[ActorSpec] = field(default_factory=list)
    relations: List[RelationSpec] = field(default_factory=list)
    assets: List[AssetSpec] = field(default_factory=list)
    realizations: List[RealizationSpec] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Multipliers per realization policy relative to prototype baseline.
    # draw_calls, memory_mb, sync_time_ms are per-actor base costs.
    POLICY_COST_MULTIPLIERS = {
        RealizationPolicy.PROTOTYPE: {"draw_calls": 1.0, "memory_mb": 0.5, "sync_time_ms": 50.0},
        RealizationPolicy.EDITOR_PREVIEW: {"draw_calls": 1.5, "memory_mb": 0.7, "sync_time_ms": 60.0},
        RealizationPolicy.GAME_READY: {"draw_calls": 2.0, "memory_mb": 1.0, "sync_time_ms": 80.0},
        RealizationPolicy.CINEMATIC: {"draw_calls": 3.0, "memory_mb": 4.0, "sync_time_ms": 100.0},
        RealizationPolicy.RUNTIME: {"draw_calls": 2.0, "memory_mb": 1.2, "sync_time_ms": 70.0},
    }

    def estimate_cost(
        self,
        policy: RealizationPolicy = RealizationPolicy.PROTOTYPE,
    ) -> CostEstimate:
        """Estimate runtime cost of realizing this graph under the given policy."""
        n = len(self.actors)
        multipliers = self.POLICY_COST_MULTIPLIERS.get(policy, self.POLICY_COST_MULTIPLIERS[RealizationPolicy.PROTOTYPE])
        cost = CostEstimate(actor_count=n)
        cost.estimated_draw_calls = int(n * multipliers["draw_calls"])
        cost.estimated_memory_mb = n * multipliers["memory_mb"]
        cost.estimated_sync_time_ms = n * multipliers["sync_time_ms"]
        return cost

    def realize(
        self,
        policy: RealizationPolicy = RealizationPolicy.PROTOTYPE,
        scene_id: str = "main",
        group_id: Optional[str] = None,
    ) -> List[ActorSpec]:
        """Realize this graph into a list of ActorSpecs under the given policy.

        PROTOTYPE   -> Returns the pre-baked actors directly (Cube/Cylinder).
        EDITOR_PREVIEW -> Same as prototype but adds preview lights for key entities.
        GAME_READY  -> Adds collision proxies and marks HISM candidates.
        CINEMATIC   -> Replaces low-poly meshes with high-density placeholders.
        RUNTIME     -> Tags actors for streaming and world partition.
        """
        if policy == RealizationPolicy.PROTOTYPE:
            return self._realize_prototype(scene_id, group_id)
        if policy == RealizationPolicy.EDITOR_PREVIEW:
            return self._realize_editor_preview(scene_id, group_id)
        if policy == RealizationPolicy.GAME_READY:
            return self._realize_game_ready(scene_id, group_id)
        if policy == RealizationPolicy.CINEMATIC:
            return self._realize_cinematic(scene_id, group_id)
        if policy == RealizationPolicy.RUNTIME:
            return self._realize_runtime(scene_id, group_id)
        raise ValueError(f"Unknown realization policy: {policy}")

    POLICY_QUALITY_MAP = {
        RealizationPolicy.PROTOTYPE: "prototype",
        RealizationPolicy.EDITOR_PREVIEW: "prototype",
        RealizationPolicy.GAME_READY: "game_ready",
        RealizationPolicy.CINEMATIC: "cinematic",
        RealizationPolicy.RUNTIME: "runtime",
    }

    def _resolve_asset_path(self, path: str, quality: str) -> tuple:
        """Resolve a BasicShapes placeholder through the asset catalog.

        Returns (resolved_path, asset_id_or_none). If the catalog has no
        match, the original path is returned unchanged.
        """
        if "BasicShapes" not in path:
            return path, None
        resolved = AssetResolver.resolve(path, quality=quality)
        if resolved["status"] == "present":
            return resolved["path"], path
        return path, None

    def _realize_prototype(
        self, scene_id: str = "main", group_id: Optional[str] = None,
        quality: str = "prototype",
    ) -> List[ActorSpec]:
        """Prototype policy: return deep copies of actors, ensuring group_id is injected.

        Resolves BasicShapes placeholder paths through AssetResolver when possible,
        preserving the original path as asset_id for traceability.
        """
        result: List[ActorSpec] = []
        for actor in self.actors:
            copied = copy.deepcopy(actor)
            if group_id is not None and copied.group_id is None:
                copied.group_id = group_id
            path = copied.asset_ref.get("path", "")
            resolved_path, asset_id = self._resolve_asset_path(path, quality)
            if asset_id is not None:
                copied.asset_ref["path"] = resolved_path
                copied.asset_ref["asset_id"] = asset_id
            result.append(copied)
        return result

    def _realize_editor_preview(
        self, scene_id: str = "main", group_id: Optional[str] = None
    ) -> List[ActorSpec]:
        """Editor preview: prototype + preview lights for key entities."""
        actors = self._realize_prototype(scene_id, group_id, quality="prototype")
        key_kinds = {"keep", "gate", "tower", "courtyard"}
        light_actors: List[ActorSpec] = []
        for entity in self.entities:
            if entity.kind in key_kinds:
                for mcp_id in entity.mcp_ids[:1]:
                    # Position the light above the entity's first actor
                    light_x, light_y, light_z = 0.0, 0.0, 500.0
                    matching = [a for a in self.actors if a.mcp_id == mcp_id]
                    if matching:
                        loc = matching[0].transform.get("location", {})
                        light_x = loc.get("x", 0.0)
                        light_y = loc.get("y", 0.0)
                        light_z = loc.get("z", 0.0) + 500.0
                    light_actors.append(
                        ActorSpec(
                            mcp_id=f"{mcp_id}_PreviewLight",
                            desired_name=f"{entity.name}_PreviewLight",
                            actor_type="PointLight",
                            asset_ref={"path": "/Engine/EngineSky/BP_Sky_Sphere"},
                            transform={
                                "location": {"x": light_x, "y": light_y, "z": light_z},
                                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
                            },
                            tags=["preview_light", entity.kind],
                            group_id=group_id,
                            visual={"intensity": 5000.0, "color": [1.0, 0.9, 0.8]},
                        )
                    )
        return actors + light_actors

    def _find_entity_for_actor(self, actor: ActorSpec) -> Optional[EntitySpec]:
        """Find the entity whose mcp_ids include this actor's mcp_id."""
        for entity in self.entities:
            if actor.mcp_id in entity.mcp_ids:
                return entity
        return None

    def _realize_game_ready(
        self, scene_id: str = "main", group_id: Optional[str] = None
    ) -> List[ActorSpec]:
        """Game-ready: prototype + collision proxies and HISM tags.

        If entities have CollisionSpec or NavSpec components, those take
        precedence over the defaults.
        """
        from server.specs.component_spec import CollisionSpec, NavSpec

        actors = self._realize_prototype(scene_id, group_id, quality="game_ready")
        for actor in actors:
            if actor.actor_type == "StaticMeshActor":
                actor.visual["collision_profile"] = "BlockAllDynamic"
                actor.visual["hism_candidate"] = True
                actor.visual["navmesh_behavior"] = "walkable"
                # Override from entity components if available
                entity = self._find_entity_for_actor(actor)
                if entity is not None:
                    for comp in entity.components:
                        if isinstance(comp, CollisionSpec):
                            actor.visual["collision_profile"] = comp.profile
                            actor.visual["collision_shape"] = comp.shape
                        elif isinstance(comp, NavSpec):
                            actor.visual["navmesh_behavior"] = comp.behavior
        return actors

    def _realize_cinematic(
        self, scene_id: str = "main", group_id: Optional[str] = None
    ) -> List[ActorSpec]:
        """Cinematic: replace placeholder meshes with high-density variants."""
        actors = self._realize_prototype(scene_id, group_id, quality="cinematic")
        for actor in actors:
            path = actor.asset_ref.get("path", "")
            if "BasicShapes/Cube" in path:
                actor.asset_ref["path"] = path.replace("Cube", "HighResCube")
            if "BasicShapes/Cylinder" in path:
                actor.asset_ref["path"] = path.replace("Cylinder", "HighResCylinder")
            actor.visual["lod_level"] = 0
        return actors

    def _realize_runtime(
        self, scene_id: str = "main", group_id: Optional[str] = None
    ) -> List[ActorSpec]:
        """Runtime: tag actors for streaming and world partition."""
        actors = self._realize_prototype(scene_id, group_id, quality="runtime")
        for actor in actors:
            actor.metadata["streaming"] = True
            actor.metadata["world_partition"] = True
            actor.metadata["hlod_candidate"] = True
        return actors

    def get_entity_by_kind(self, kind: str) -> List[EntitySpec]:
        """Return all entities of a given kind."""
        return [e for e in self.entities if e.kind == kind]

    def get_related_entities(self, entity_id: str, relation_type: str) -> List[EntitySpec]:
        """Return all entities related to the given entity_id by relation_type."""
        related_ids = {
            r.target_entity_id
            for r in self.relations
            if r.source_entity_id == entity_id and r.relation_type == relation_type
        }
        return [e for e in self.entities if e.entity_id in related_ids]

    def summary(self) -> Dict[str, Any]:
        """Human-readable summary of this graph."""
        return {
            "entity_count": len(self.entities),
            "actor_count": len(self.actors),
            "relation_count": len(self.relations),
            "asset_count": len(self.assets),
            "warning_count": len(self.warnings),
            "entity_kinds": sorted({e.kind for e in self.entities}),
            "warnings": self.warnings,
        }

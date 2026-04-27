"""CastleFortressGenerator – produces a SpecGraph from castle parameters.

The generator uses existing helpers/castle_creation.py build_* functions
under the hood, but wraps their output in a semantic SpecGraph so that
the same design can be realized under different RealizationPolicies.
"""

import math
from typing import Any, Dict, List, Optional

from helpers.castle_creation import (
    add_decorative_flags,
    build_bailey_annexes,
    build_central_keep,
    build_corner_towers,
    build_courtyard_complex,
    build_drawbridge_and_moat,
    build_gate_complex,
    build_inner_bailey_walls,
    build_inner_corner_towers,
    build_intermediate_towers,
    build_outer_bailey_walls,
    build_siege_weapons,
    build_village_settlement,
    calculate_scaled_dimensions,
    get_castle_size_params,
)
from server.actor_sink import DryRunActorSink
from server.specs.actor_spec import ActorSpec
from server.specs.component_spec import CollisionSpec, NavSpec
from server.specs.entity_spec import EntitySpec
from server.specs.graph import SpecGraph
from server.specs.relation_spec import RelationSpec


class CastleFortressGenerator:
    """Generates a SpecGraph for a castle fortress."""

    def __init__(
        self,
        castle_size: str = "large",
        architectural_style: str = "medieval",
        location: Optional[List[float]] = None,
        name_prefix: str = "Castle",
        include_siege_weapons: bool = True,
        include_village: bool = True,
    ):
        self.castle_size = castle_size
        self.architectural_style = architectural_style
        self.location = location or [0.0, 0.0, 0.0]
        self.name_prefix = name_prefix
        self.include_siege_weapons = include_siege_weapons
        self.include_village = include_village

        params = get_castle_size_params(castle_size)
        self.dimensions = calculate_scaled_dimensions(params, scale_factor=2.0)

    def _extract_mcp_ids(self, sink: DryRunActorSink) -> List[str]:
        """Return mcp_ids spawned into the given sink."""
        return [spec.mcp_id for spec in sink.specs]

    def _build_and_extract(
        self, build_func, *args, **kwargs
    ) -> tuple[List[str], DryRunActorSink]:
        """Call a build_* function with a fresh DryRunActorSink and return mcp_ids + sink."""
        sink = DryRunActorSink()
        build_func(*args, **kwargs, sink=sink)
        return self._extract_mcp_ids(sink), sink

    def generate(self) -> SpecGraph:
        """Run all castle build helpers and produce a semantic SpecGraph."""
        entities: List[EntitySpec] = []
        relations: List[RelationSpec] = []
        all_actors: List[ActorSpec] = []
        warnings: List[str] = []

        # Root fortress
        fortress = EntitySpec(
            entity_id=f"{self.name_prefix}_Fortress",
            kind="castle",
            name=f"{self.name_prefix} Fortress",
            properties={
                "castle_size": self.castle_size,
                "architectural_style": self.architectural_style,
                "location": self.location,
                "dimensions": self.dimensions,
            },
            tags=["castle", self.architectural_style],
        )
        entities.append(fortress)

        # Outer Bailey --------------------------------------------------
        outer_mcp_ids, outer_sink = self._build_and_extract(
            build_outer_bailey_walls,
            None, self.name_prefix, self.location, self.dimensions, [],
        )
        outer_bailey = EntitySpec(
            entity_id=f"{self.name_prefix}_OuterBailey",
            kind="bailey",
            name="Outer Bailey",
            properties={"wall_count": len(outer_mcp_ids)},
            tags=["bailey", "outer"],
            mcp_ids=outer_mcp_ids,
            components=[CollisionSpec(profile="BlockAllDynamic", shape="complex_as_simple")],
        )
        entities.append(outer_bailey)
        relations.append(
            RelationSpec(
                relation_id=f"{self.name_prefix}_rel_fortress_outer",
                source_entity_id=fortress.entity_id,
                target_entity_id=outer_bailey.entity_id,
                relation_type="contains",
            )
        )
        all_actors.extend(outer_sink.specs)

        # Inner Bailey --------------------------------------------------
        inner_mcp_ids, inner_sink = self._build_and_extract(
            build_inner_bailey_walls,
            None, self.name_prefix, self.location, self.dimensions, [],
        )
        inner_bailey = EntitySpec(
            entity_id=f"{self.name_prefix}_InnerBailey",
            kind="bailey",
            name="Inner Bailey",
            properties={"wall_count": len(inner_mcp_ids)},
            tags=["bailey", "inner"],
            mcp_ids=inner_mcp_ids,
            components=[CollisionSpec(profile="BlockAllDynamic", shape="complex_as_simple")],
        )
        entities.append(inner_bailey)
        relations.append(
            RelationSpec(
                relation_id=f"{self.name_prefix}_rel_fortress_inner",
                source_entity_id=fortress.entity_id,
                target_entity_id=inner_bailey.entity_id,
                relation_type="contains",
            )
        )
        all_actors.extend(inner_sink.specs)

        # Gate Complex --------------------------------------------------
        gate_mcp_ids, gate_sink = self._build_and_extract(
            build_gate_complex,
            None, self.name_prefix, self.location, self.dimensions, [],
        )
        gate_complex = EntitySpec(
            entity_id=f"{self.name_prefix}_GateComplex",
            kind="gate",
            name="Main Gate Complex",
            properties={"component_count": len(gate_mcp_ids)},
            tags=["gate", "defense"],
            mcp_ids=gate_mcp_ids,
            components=[CollisionSpec(profile="BlockAllDynamic"), NavSpec(behavior="blocked")],
        )
        entities.append(gate_complex)
        relations.append(
            RelationSpec(
                relation_id=f"{self.name_prefix}_rel_outer_gate",
                source_entity_id=outer_bailey.entity_id,
                target_entity_id=gate_complex.entity_id,
                relation_type="contains",
            )
        )
        all_actors.extend(gate_sink.specs)

        # Corner Towers -------------------------------------------------
        corner_mcp_ids, corner_sink = self._build_and_extract(
            build_corner_towers,
            None, self.name_prefix, self.location, self.dimensions,
            self.architectural_style, [],
        )
        corner_towers = EntitySpec(
            entity_id=f"{self.name_prefix}_CornerTowers",
            kind="tower_group",
            name="Corner Towers",
            properties={"tower_count": 4},
            tags=["tower", "corner"],
            mcp_ids=corner_mcp_ids,
        )
        entities.append(corner_towers)
        relations.append(
            RelationSpec(
                relation_id=f"{self.name_prefix}_rel_outer_corner",
                source_entity_id=outer_bailey.entity_id,
                target_entity_id=corner_towers.entity_id,
                relation_type="contains",
            )
        )
        all_actors.extend(corner_sink.specs)

        # Inner Corner Towers -------------------------------------------
        inner_corner_mcp_ids, inner_corner_sink = self._build_and_extract(
            build_inner_corner_towers,
            None, self.name_prefix, self.location, self.dimensions, [],
        )
        inner_corner_towers = EntitySpec(
            entity_id=f"{self.name_prefix}_InnerCornerTowers",
            kind="tower_group",
            name="Inner Corner Towers",
            properties={"tower_count": 4},
            tags=["tower", "corner", "inner"],
            mcp_ids=inner_corner_mcp_ids,
        )
        entities.append(inner_corner_towers)
        relations.append(
            RelationSpec(
                relation_id=f"{self.name_prefix}_rel_inner_corner",
                source_entity_id=inner_bailey.entity_id,
                target_entity_id=inner_corner_towers.entity_id,
                relation_type="contains",
            )
        )
        all_actors.extend(inner_corner_sink.specs)

        # Intermediate Towers -------------------------------------------
        intermediate_mcp_ids, intermediate_sink = self._build_and_extract(
            build_intermediate_towers,
            None, self.name_prefix, self.location, self.dimensions, [],
        )
        if intermediate_mcp_ids:
            intermediate_towers = EntitySpec(
                entity_id=f"{self.name_prefix}_IntermediateTowers",
                kind="tower_group",
                name="Intermediate Wall Towers",
                properties={"tower_count": len(intermediate_mcp_ids) // 2},
                tags=["tower", "intermediate"],
                mcp_ids=intermediate_mcp_ids,
            )
            entities.append(intermediate_towers)
            relations.append(
                RelationSpec(
                    relation_id=f"{self.name_prefix}_rel_outer_intermediate",
                    source_entity_id=outer_bailey.entity_id,
                    target_entity_id=intermediate_towers.entity_id,
                    relation_type="contains",
                )
            )
            all_actors.extend(intermediate_sink.specs)

        # Central Keep --------------------------------------------------
        keep_mcp_ids, keep_sink = self._build_and_extract(
            build_central_keep,
            None, self.name_prefix, self.location, self.dimensions, [],
        )
        central_keep = EntitySpec(
            entity_id=f"{self.name_prefix}_CentralKeep",
            kind="keep",
            name="Central Keep",
            properties={"component_count": len(keep_mcp_ids)},
            tags=["keep", "central"],
            mcp_ids=keep_mcp_ids,
            components=[CollisionSpec(profile="BlockAllDynamic")],
        )
        entities.append(central_keep)
        relations.append(
            RelationSpec(
                relation_id=f"{self.name_prefix}_rel_inner_keep",
                source_entity_id=inner_bailey.entity_id,
                target_entity_id=central_keep.entity_id,
                relation_type="contains",
            )
        )
        all_actors.extend(keep_sink.specs)

        # Courtyard Complex ---------------------------------------------
        courtyard_mcp_ids, courtyard_sink = self._build_and_extract(
            build_courtyard_complex,
            None, self.name_prefix, self.location, self.dimensions, [],
        )
        courtyard = EntitySpec(
            entity_id=f"{self.name_prefix}_Courtyard",
            kind="courtyard",
            name="Courtyard Complex",
            properties={"building_count": len(courtyard_mcp_ids)},
            tags=["courtyard", "inner"],
            mcp_ids=courtyard_mcp_ids,
            components=[NavSpec(behavior="walkable")],
        )
        entities.append(courtyard)
        relations.append(
            RelationSpec(
                relation_id=f"{self.name_prefix}_rel_inner_courtyard",
                source_entity_id=inner_bailey.entity_id,
                target_entity_id=courtyard.entity_id,
                relation_type="contains",
            )
        )
        all_actors.extend(courtyard_sink.specs)

        # Bailey Annexes ------------------------------------------------
        annex_mcp_ids, annex_sink = self._build_and_extract(
            build_bailey_annexes,
            None, self.name_prefix, self.location, self.dimensions, [],
        )
        if annex_mcp_ids:
            annexes = EntitySpec(
                entity_id=f"{self.name_prefix}_BaileyAnnexes",
                kind="annex_group",
                name="Bailey Annexes",
                properties={"structure_count": len(annex_mcp_ids)},
                tags=["annex", "outer"],
                mcp_ids=annex_mcp_ids,
            )
            entities.append(annexes)
            relations.append(
                RelationSpec(
                    relation_id=f"{self.name_prefix}_rel_outer_annex",
                    source_entity_id=outer_bailey.entity_id,
                    target_entity_id=annexes.entity_id,
                    relation_type="contains",
                )
            )
            all_actors.extend(annex_sink.specs)

        # Siege Weapons -------------------------------------------------
        if self.include_siege_weapons:
            siege_mcp_ids, siege_sink = self._build_and_extract(
                build_siege_weapons,
                None, self.name_prefix, self.location, self.dimensions, [],
            )
            siege_weapons = EntitySpec(
                entity_id=f"{self.name_prefix}_SiegeWeapons",
                kind="siege_weapon_group",
                name="Siege Weapons",
                properties={"weapon_count": len(siege_mcp_ids)},
                tags=["siege", "weapon"],
                mcp_ids=siege_mcp_ids,
            )
            entities.append(siege_weapons)
            relations.append(
                RelationSpec(
                    relation_id=f"{self.name_prefix}_rel_outer_siege",
                    source_entity_id=outer_bailey.entity_id,
                    target_entity_id=siege_weapons.entity_id,
                    relation_type="contains",
                )
            )
            all_actors.extend(siege_sink.specs)

        # Village Settlement --------------------------------------------
        if self.include_village:
            village_mcp_ids, village_sink = self._build_and_extract(
                build_village_settlement,
                None, self.name_prefix, self.location, self.dimensions,
                self.castle_size, [],
            )
            village = EntitySpec(
                entity_id=f"{self.name_prefix}_Village",
                kind="settlement",
                name="Surrounding Village",
                properties={"house_count": len(village_mcp_ids) // 2},
                tags=["village", "settlement"],
                mcp_ids=village_mcp_ids,
            )
            entities.append(village)
            relations.append(
                RelationSpec(
                    relation_id=f"{self.name_prefix}_rel_fortress_village",
                    source_entity_id=fortress.entity_id,
                    target_entity_id=village.entity_id,
                    relation_type="contains",
                )
            )
            all_actors.extend(village_sink.specs)

        # Drawbridge & Moat ---------------------------------------------
        moat_mcp_ids, moat_sink = self._build_and_extract(
            build_drawbridge_and_moat,
            None, self.name_prefix, self.location, self.dimensions, [],
        )
        moat = EntitySpec(
            entity_id=f"{self.name_prefix}_MoatAndDrawbridge",
            kind="moat",
            name="Moat and Drawbridge",
            properties={"component_count": len(moat_mcp_ids)},
            tags=["moat", "drawbridge", "water"],
            mcp_ids=moat_mcp_ids,
            components=[NavSpec(behavior="blocked"), CollisionSpec(profile="BlockAllDynamic")],
        )
        entities.append(moat)
        relations.append(
            RelationSpec(
                relation_id=f"{self.name_prefix}_rel_outer_moat",
                source_entity_id=outer_bailey.entity_id,
                target_entity_id=moat.entity_id,
                relation_type="contains",
            )
        )
        all_actors.extend(moat_sink.specs)

        # Decorative Flags ----------------------------------------------
        flag_mcp_ids, flag_sink = self._build_and_extract(
            add_decorative_flags,
            None, self.name_prefix, self.location, self.dimensions, [],
        )
        flags = EntitySpec(
            entity_id=f"{self.name_prefix}_DecorativeFlags",
            kind="decoration_group",
            name="Decorative Flags",
            properties={"flag_count": len(flag_mcp_ids) // 2},
            tags=["decoration", "flag"],
            mcp_ids=flag_mcp_ids,
        )
        entities.append(flags)
        relations.append(
            RelationSpec(
                relation_id=f"{self.name_prefix}_rel_fortress_flags",
                source_entity_id=fortress.entity_id,
                target_entity_id=flags.entity_id,
                relation_type="contains",
            )
        )
        all_actors.extend(flag_sink.specs)

        return SpecGraph(
            entities=entities,
            actors=all_actors,
            relations=relations,
            warnings=warnings,
        )

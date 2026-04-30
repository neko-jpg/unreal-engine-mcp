"""CapitalCityGenerator – produces a SpecGraph for a massive medieval capital city.

The generator uses the semantic layout graph pipeline (EntitySpec + RelationSpec)
which is fed into the Rust denormalizer.  The denormalizer turns each entity into
SceneObjects with proper `layout_kind:` tags, layers, and transforms.  The Rust
validation engine then checks overlap, bridge-moat crossing, tower-wall connectivity,
etc.  Because the Rust denormalizer handles geometry, the Python side only needs to
provide correct `location`, `size`, `from`/`to`, and relations.

Zones
-----
1. Central District (Castle Fortress)
   - Epic-scale double bailey with outer/inner walls, 8 corner towers, keep,
     gatehouse, moat, drawbridge.
   - ~1,500 denormalized objects (high segment counts on walls).

2. Noble Quarter
   - 4-6 Legendary-scale mansions placed radially outside the moat.
   - Each mansion has perimeter walls, corner towers, main hall, wings, gardens,
     fountains, and a private road.
   - ~800 denormalized objects.

3. Commoner Quarter
   - Dense town grid surrounding the noble quarter.
   - Houses, shops, market square, blacksmith, chapel, wells, fountains,
     street lamps, trees, and a grid of roads.
   - ~1,500 denormalized objects.

Total target: 3,000 – 5,000 SceneObjects.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from server.specs.entity_spec import EntitySpec
from server.specs.relation_spec import RelationSpec
from server.specs.graph import SpecGraph


def _vec3(x: float, y: float, z: float) -> Dict[str, float]:
    return {"x": x, "y": y, "z": z}


def _size(sx: float, sy: float, sz: float) -> Dict[str, float]:
    return {"x": sx, "y": sy, "z": sz}


def _circle_point(cx: float, cy: float, radius: float, angle_deg: float) -> Tuple[float, float]:
    rad = math.radians(angle_deg)
    return cx + radius * math.cos(rad), cy + radius * math.sin(rad)


class CapitalCityGenerator:
    """Generates a semantic SpecGraph for a massive medieval capital city."""

    def __init__(
        self,
        city_size: str = "large",
        location: Optional[List[float]] = None,
        name_prefix: str = "CapitalCity",
        include_noble_quarter: bool = True,
        include_commoner_quarter: bool = True,
    ):
        self.city_size = city_size
        self.location = location or [0.0, 0.0, 0.0]
        self.name_prefix = name_prefix
        self.include_noble_quarter = include_noble_quarter
        self.include_commoner_quarter = include_commoner_quarter

        # Scale factors per city size.
        self._scale = {
            "small": 0.6,
            "medium": 0.85,
            "large": 1.0,
            "epic": 1.4,
        }.get(city_size, 1.0)

        # Base castle dimensions (cm) – epic default.
        base = {
            "outer_width": 16000,
            "outer_depth": 16000,
            "inner_width": 8000,
            "inner_depth": 8000,
            "wall_height": 1600,
            "wall_thickness": 300,
            "tower_height": 2800,
            "tower_size": 500,
            "keep_width": 4800,
            "keep_depth": 4800,
            "keep_height": 5600,
            "moat_margin": 1200,
            "gatehouse_width": 800,
            "gatehouse_depth": 800,
        }
        self.dim = {k: int(v * self._scale) for k, v in base.items()}

        # Derived convenience values (half-extents, i.e. distance from center to wall).
        self.ow = self.dim["outer_width"] / 2.0
        self.od = self.dim["outer_depth"] / 2.0
        self.iw = self.dim["inner_width"] / 2.0
        self.id = self.dim["inner_depth"] / 2.0
        self.loc = self.location

    def generate_semantic(self) -> SpecGraph:
        """Generate a semantic layout graph for the entire capital city."""
        entities: List[EntitySpec] = []
        relations: List[RelationSpec] = []
        prefix = self.name_prefix
        loc = self.loc

        # ================================================================
        # 1. CENTRAL DISTRICT – Castle Fortress
        # ================================================================

        # --- Ground -------------------------------------------------------
        ground = EntitySpec(
            entity_id=f"{prefix}_Ground",
            kind="ground",
            name="Capital City Ground",
            properties={
                "width": self.ow * 6.0,
                "depth": self.od * 6.0,
            },
            tags=["capital_city", "ground"],
        )
        entities.append(ground)

        # --- Moat ---------------------------------------------------------
        moat_width = self.ow * 2.0 + self.dim["moat_margin"] * 2.0
        moat_depth = self.od * 2.0 + self.dim["moat_margin"] * 2.0
        moat = EntitySpec(
            entity_id=f"{prefix}_Moat",
            kind="moat",
            name="Castle Moat",
            properties={
                "width": moat_width,
                "depth": moat_depth,
            },
            tags=["capital_city", "moat", "water"],
        )
        entities.append(moat)

        # --- Outer corner towers ------------------------------------------
        outer_corners = self._corner_positions(self.ow, self.od)
        outer_tower_entities: List[EntitySpec] = []
        for i, (cx, cy) in enumerate(outer_corners):
            tid = ["NW", "NE", "SE", "SW"][i]
            t = EntitySpec(
                entity_id=f"{prefix}_OuterTower{tid}",
                kind="tower",
                name=f"Outer {tid} Tower",
                properties={
                    "location": _vec3(cx, cy, loc[2]),
                    "size": _size(
                        self.dim["tower_size"] / 100.0,
                        self.dim["tower_size"] / 100.0,
                        self.dim["tower_height"] / 100.0,
                    ),
                },
                tags=["capital_city", "tower", "outer", tid.lower()],
            )
            entities.append(t)
            outer_tower_entities.append(t)

        # --- Outer bailey walls -------------------------------------------
        # High segment count for massive object counts.
        outer_segments = max(80, int(self.ow / 50))  # e.g. 320 segments for epic
        wall_pairs = [
            ("OuterNorth", outer_tower_entities[0], outer_tower_entities[1]),
            ("OuterEast", outer_tower_entities[1], outer_tower_entities[2]),
            ("OuterSouth", outer_tower_entities[2], outer_tower_entities[3]),
            ("OuterWest", outer_tower_entities[3], outer_tower_entities[0]),
        ]
        for wall_name, t1, t2 in wall_pairs:
            wall = EntitySpec(
                entity_id=f"{prefix}_{wall_name}Wall",
                kind="curtain_wall",
                name=f"Outer Bailey {wall_name} Wall",
                properties={
                    "height": self.dim["wall_height"],
                    "thickness": self.dim["wall_thickness"],
                    "segments": outer_segments,
                    "crenellations": {"enabled": True, "count": outer_segments // 2},
                },
                tags=["capital_city", "wall", "outer", wall_name.lower()],
            )
            entities.append(wall)
            relations.append(
                RelationSpec(
                    relation_id=f"{prefix}_rel_{wall_name.lower()}_w1",
                    source_entity_id=wall.entity_id,
                    target_entity_id=t1.entity_id,
                    relation_type="connected_by",
                    properties={"order": 0},
                )
            )
            relations.append(
                RelationSpec(
                    relation_id=f"{prefix}_rel_{wall_name.lower()}_w2",
                    source_entity_id=wall.entity_id,
                    target_entity_id=t2.entity_id,
                    relation_type="connected_by",
                    properties={"order": 1},
                )
            )

        # --- Inner corner towers ------------------------------------------
        inner_corners = self._corner_positions(self.iw, self.id)
        inner_tower_entities: List[EntitySpec] = []
        for i, (cx, cy) in enumerate(inner_corners):
            tid = ["NW", "NE", "SE", "SW"][i]
            t = EntitySpec(
                entity_id=f"{prefix}_InnerTower{tid}",
                kind="tower",
                name=f"Inner {tid} Tower",
                properties={
                    "location": _vec3(cx, cy, loc[2]),
                    "size": _size(
                        self.dim["tower_size"] * 1.2 / 100.0,
                        self.dim["tower_size"] * 1.2 / 100.0,
                        self.dim["tower_height"] * 1.4 / 100.0,
                    ),
                },
                tags=["capital_city", "tower", "inner", tid.lower()],
            )
            entities.append(t)
            inner_tower_entities.append(t)

        # --- Inner bailey walls -------------------------------------------
        inner_segments = max(40, int(self.iw / 50))
        inner_wall_pairs = [
            ("InnerNorth", inner_tower_entities[0], inner_tower_entities[1]),
            ("InnerEast", inner_tower_entities[1], inner_tower_entities[2]),
            ("InnerSouth", inner_tower_entities[2], inner_tower_entities[3]),
            ("InnerWest", inner_tower_entities[3], inner_tower_entities[0]),
        ]
        for wall_name, t1, t2 in inner_wall_pairs:
            wall = EntitySpec(
                entity_id=f"{prefix}_{wall_name}Wall",
                kind="curtain_wall",
                name=f"Inner Bailey {wall_name} Wall",
                properties={
                    "height": self.dim["wall_height"] * 1.3,
                    "thickness": self.dim["wall_thickness"],
                    "segments": inner_segments,
                    "crenellations": {"enabled": True, "count": inner_segments // 2},
                },
                tags=["capital_city", "wall", "inner"],
            )
            entities.append(wall)
            relations.append(
                RelationSpec(
                    relation_id=f"{prefix}_rel_{wall_name.lower()}_w1",
                    source_entity_id=wall.entity_id,
                    target_entity_id=t1.entity_id,
                    relation_type="connected_by",
                    properties={"order": 0},
                )
            )
            relations.append(
                RelationSpec(
                    relation_id=f"{prefix}_rel_{wall_name.lower()}_w2",
                    source_entity_id=wall.entity_id,
                    target_entity_id=t2.entity_id,
                    relation_type="connected_by",
                    properties={"order": 1},
                )
            )

        # --- Central Keep -------------------------------------------------
        keep = EntitySpec(
            entity_id=f"{prefix}_CentralKeep",
            kind="keep",
            name="Central Keep",
            properties={
                "location": _vec3(loc[0], loc[1], loc[2]),
                "size": _size(
                    self.dim["keep_width"] / 100.0,
                    self.dim["keep_depth"] / 100.0,
                    self.dim["keep_height"] / 100.0,
                ),
            },
            tags=["capital_city", "keep", "central"],
        )
        entities.append(keep)

        # Keep corner mini-towers
        keep_offsets = [
            (-self.dim["keep_width"] / 3, -self.dim["keep_depth"] / 3),
            (self.dim["keep_width"] / 3, -self.dim["keep_depth"] / 3),
            (self.dim["keep_width"] / 3, self.dim["keep_depth"] / 3),
            (-self.dim["keep_width"] / 3, self.dim["keep_depth"] / 3),
        ]
        for i, (kx, ky) in enumerate(keep_offsets):
            kt = EntitySpec(
                entity_id=f"{prefix}_KeepTower{i}",
                kind="building",
                name=f"Keep Corner Tower {i}",
                properties={
                    "location": _vec3(loc[0] + kx, loc[1] + ky, loc[2]),
                    "size": _size(3.0, 3.0, self.dim["keep_height"] * 0.8 / 100.0),
                },
                tags=["capital_city", "tower", "keep"],
            )
            entities.append(kt)

        # --- Gatehouse (West wall midpoint) -------------------------------
        gate_x = loc[0] - self.ow
        gatehouse = EntitySpec(
            entity_id=f"{prefix}_Gatehouse",
            kind="gatehouse",
            name="Main Gatehouse",
            properties={
                "location": _vec3(gate_x, loc[1], loc[2]),
                "size": _size(
                    self.dim["gatehouse_width"] / 100.0,
                    self.dim["gatehouse_depth"] / 100.0,
                    self.dim["tower_height"] / 100.0,
                ),
            },
            tags=["capital_city", "gate", "main"],
        )
        entities.append(gatehouse)

        # Gate towers flanking the gatehouse
        for side in [-1, 1]:
            gt = EntitySpec(
                entity_id=f"{prefix}_GateTower{side}",
                kind="tower",
                name=f"Gate Tower {side}",
                properties={
                    "location": _vec3(
                        gate_x,
                        loc[1] + side * self.dim["gatehouse_depth"] * 0.8,
                        loc[2],
                    ),
                    "size": _size(4.0, 4.0, self.dim["tower_height"] / 100.0),
                },
                tags=["capital_city", "tower", "gate"],
            )
            entities.append(gt)

        # --- Bridge -------------------------------------------------------
        # Bridge spans from gatehouse outward across the moat.
        # The bridge_end is placed beyond the moat so the bridge segment crosses it.
        bridge_end_x = gate_x - self.dim["moat_margin"] * 2.5
        bridge = EntitySpec(
            entity_id=f"{prefix}_Drawbridge",
            kind="bridge",
            name="Main Drawbridge",
            properties={
                "width": 600.0,
                "height": 20.0,
            },
            tags=["capital_city", "bridge", "drawbridge"],
        )
        entities.append(bridge)
        relations.append(
            RelationSpec(
                relation_id=f"{prefix}_rel_bridge_gate",
                source_entity_id=bridge.entity_id,
                target_entity_id=gatehouse.entity_id,
                relation_type="connected_by",
                properties={"order": 0},
            )
        )

        bridge_end = EntitySpec(
            entity_id=f"{prefix}_BridgeEnd",
            kind="decoration",
            name="Bridge Far End",
            properties={
                "location": _vec3(bridge_end_x, loc[1], loc[2]),
                "size": _size(2.0, 2.0, 2.0),
            },
            tags=["capital_city", "bridge_end"],
        )
        entities.append(bridge_end)
        relations.append(
            RelationSpec(
                relation_id=f"{prefix}_rel_bridge_end",
                source_entity_id=bridge.entity_id,
                target_entity_id=bridge_end.entity_id,
                relation_type="connected_by",
                properties={"order": 1},
            )
        )

        # --- Courtyard buildings ------------------------------------------
        courtyard_buildings = [
            ("Stables", [-self.iw / 3, self.id / 3, 150], [8.0, 4.0, 3.0]),
            ("Barracks", [self.iw / 3, self.id / 3, 150], [10.0, 6.0, 3.0]),
            ("Blacksmith", [self.iw / 3, -self.id / 3, 100], [6.0, 6.0, 2.0]),
            ("Well", [-self.iw / 4, 0, 50], [3.0, 3.0, 2.0]),
            ("Armory", [-self.iw / 3, -self.id / 3, 150], [6.0, 4.0, 3.0]),
            ("Chapel", [0, -self.id / 3, 200], [8.0, 5.0, 4.0]),
            ("Kitchen", [-self.iw / 4, self.id / 4, 120], [5.0, 4.0, 2.5]),
            ("Treasury", [self.iw / 4, self.id / 4, 100], [3.0, 3.0, 2.0]),
            ("Granary", [self.iw / 4, -self.id / 4, 180], [4.0, 6.0, 3.5]),
            ("GuardHouse", [-self.iw / 4, -self.id / 4, 150], [4.0, 4.0, 3.0]),
        ]
        for bname, offset, bsize in courtyard_buildings:
            b = EntitySpec(
                entity_id=f"{prefix}_{bname}",
                kind="building",
                name=f"Courtyard {bname}",
                properties={
                    "location": _vec3(
                        loc[0] + offset[0], loc[1] + offset[1], loc[2] + offset[2]
                    ),
                    "size": _size(bsize[0], bsize[1], bsize[2]),
                },
                tags=["capital_city", "courtyard", bname.lower()],
            )
            entities.append(b)

        # --- Decorative flags ---------------------------------------------
        flag_count = max(16, int(32 * self._scale))
        for i in range(flag_count):
            angle = i * 360.0 / flag_count
            fx, fy = _circle_point(loc[0], loc[1], self.ow * 0.95, angle)
            flag = EntitySpec(
                entity_id=f"{prefix}_Flag{i}",
                kind="decoration",
                name=f"Flag {i}",
                properties={
                    "location": _vec3(fx, fy, loc[2] + self.dim["wall_height"] + 200),
                    "size": _size(0.5, 0.5, 2.0),
                },
                tags=["capital_city", "decoration", "flag"],
            )
            entities.append(flag)

        # ================================================================
        # 2. NOBLE QUARTER
        # ================================================================
        if self.include_noble_quarter:
            noble_radius = self.ow + self.dim["moat_margin"] + 4000 * self._scale
            mansion_count = 4 if self.city_size in ("small", "medium") else 6
            mansion_angles = [i * 360.0 / mansion_count for i in range(mansion_count)]

            for m_idx, angle in enumerate(mansion_angles):
                mx, my = _circle_point(loc[0], loc[1], noble_radius, angle)
                m_prefix = f"{prefix}_Mansion{m_idx}"

                # Mansion main body (keep-like)
                m_main = EntitySpec(
                    entity_id=f"{m_prefix}_Main",
                    kind="building",
                    name=f"Noble Mansion {m_idx} Main Hall",
                    properties={
                        "location": _vec3(mx, my, loc[2]),
                        "size": _size(18.0, 14.0, 12.0),
                    },
                    tags=["capital_city", "mansion", "noble"],
                )
                entities.append(m_main)

                # Mansion wings
                wing_dist = 1600 * self._scale
                for w_idx, w_angle_offset in enumerate([0, 90, 180, 270]):
                    w_angle = angle + w_angle_offset
                    wx, wy = _circle_point(mx, my, wing_dist, w_angle)
                    wing = EntitySpec(
                        entity_id=f"{m_prefix}_Wing{w_idx}",
                        kind="building",
                        name=f"Mansion {m_idx} Wing {w_idx}",
                        properties={
                            "location": _vec3(wx, wy, loc[2]),
                            "size": _size(8.0, 8.0, 8.0),
                        },
                        tags=["capital_city", "mansion", "wing"],
                    )
                    entities.append(wing)

                # Mansion garden (ground)
                garden = EntitySpec(
                    entity_id=f"{m_prefix}_Garden",
                    kind="ground",
                    name=f"Mansion {m_idx} Garden",
                    properties={
                        "location": _vec3(mx, my, loc[2] + 0.1),
                        "width": 5000.0 * self._scale,
                        "depth": 5000.0 * self._scale,
                    },
                    tags=["capital_city", "mansion", "garden"],
                )
                entities.append(garden)

                # Mansion fountain
                fountain = EntitySpec(
                    entity_id=f"{m_prefix}_Fountain",
                    kind="decoration",
                    name=f"Mansion {m_idx} Fountain",
                    properties={
                        "location": _vec3(mx + 300, my + 300, loc[2]),
                        "size": _size(2.0, 2.0, 3.0),
                    },
                    tags=["capital_city", "mansion", "fountain"],
                )
                entities.append(fountain)

                # Mansion perimeter wall
                mw_size = 2500 * self._scale
                mw_segments = max(10, int(mw_size / 150))
                mw_corners = [
                    (f"{m_prefix}_WallNW", mx - mw_size, my - mw_size),
                    (f"{m_prefix}_WallNE", mx + mw_size, my - mw_size),
                    (f"{m_prefix}_WallSE", mx + mw_size, my + mw_size),
                    (f"{m_prefix}_WallSW", mx - mw_size, my + mw_size),
                ]
                mw_tower_entities: List[EntitySpec] = []
                for ci, (cid, cx, cy) in enumerate(mw_corners):
                    mt = EntitySpec(
                        entity_id=cid,
                        kind="tower",
                        name=f"Mansion {m_idx} Corner {['NW','NE','SE','SW'][ci]}",
                        properties={
                            "location": _vec3(cx, cy, loc[2]),
                            "size": _size(2.0, 2.0, 6.0),
                        },
                        tags=["capital_city", "mansion", "tower"],
                    )
                    entities.append(mt)
                    mw_tower_entities.append(mt)

                for wi in range(4):
                    wn = f"{m_prefix}_MansionWall{wi}"
                    w1 = mw_tower_entities[wi]
                    w2 = mw_tower_entities[(wi + 1) % 4]
                    mwall = EntitySpec(
                        entity_id=wn,
                        kind="curtain_wall",
                        name=f"Mansion {m_idx} Wall {wi}",
                        properties={
                            "height": 400.0,
                            "thickness": 50.0,
                            "segments": mw_segments,
                            "crenellations": {"enabled": True, "count": mw_segments // 2},
                        },
                        tags=["capital_city", "mansion", "wall"],
                    )
                    entities.append(mwall)
                    relations.append(
                        RelationSpec(
                            relation_id=f"{m_prefix}_rel_mw{wi}_1",
                            source_entity_id=mwall.entity_id,
                            target_entity_id=w1.entity_id,
                            relation_type="connected_by",
                            properties={"order": 0},
                        )
                    )
                    relations.append(
                        RelationSpec(
                            relation_id=f"{m_prefix}_rel_mw{wi}_2",
                            source_entity_id=mwall.entity_id,
                            target_entity_id=w2.entity_id,
                            relation_type="connected_by",
                            properties={"order": 1},
                        )
                    )

        # ================================================================
        # 3. COMMONER QUARTER
        # ================================================================
        if self.include_commoner_quarter:
            town_inner_r = noble_radius + 3000 * self._scale
            town_outer_r = town_inner_r + 6000 * self._scale
            grid_step = 350.0 * self._scale
            road_width = 200.0

            # Grid-based town layout.
            grid_count = int((town_outer_r - town_inner_r) / grid_step)
            if grid_count < 3:
                grid_count = 3

            houses: List[EntitySpec] = []
            for gx in range(-grid_count, grid_count + 1):
                for gy in range(-grid_count, grid_count + 1):
                    cx = loc[0] + gx * grid_step
                    cy = loc[1] + gy * grid_step
                    dist = math.hypot(cx - loc[0], cy - loc[1])

                    # Skip if inside noble/castle zone.
                    if dist < town_inner_r:
                        continue
                    if dist > town_outer_r:
                        continue

                    # Random building type based on position.
                    abs_gx, abs_gy = abs(gx), abs(gy)
                    if abs_gx <= 1 and abs_gy <= 1:
                        # Market square in the center of town.
                        if gx == 0 and gy == 0:
                            market = EntitySpec(
                                entity_id=f"{prefix}_MarketSquare",
                                kind="ground",
                                name="Market Square",
                                properties={
                                    "location": _vec3(cx, cy, loc[2] + 0.2),
                                    "width": grid_step * 2.5,
                                    "depth": grid_step * 2.5,
                                },
                                tags=["capital_city", "market", "plaza"],
                            )
                            entities.append(market)
                            # Market stalls around the square.
                            for si in range(8):
                                sa = si * 45.0
                                sx, sy = _circle_point(cx, cy, grid_step * 0.8, sa)
                                stall = EntitySpec(
                                    entity_id=f"{prefix}_MarketStall{si}",
                                    kind="building",
                                    name=f"Market Stall {si}",
                                    properties={
                                        "location": _vec3(sx, sy, loc[2]),
                                        "size": _size(1.5, 1.5, 2.0),
                                    },
                                    tags=["capital_city", "market", "stall"],
                                )
                                entities.append(stall)
                        continue

                    # Road grid (every 3rd block).
                    if gx % 3 == 0 or gy % 3 == 0:
                        road_ent = EntitySpec(
                            entity_id=f"{prefix}_Road_{gx}_{gy}",
                            kind="ground",
                            name=f"Street {gx}_{gy}",
                            properties={
                                "location": _vec3(cx, cy, loc[2] + 0.3),
                                "width": grid_step if gx % 3 == 0 else road_width,
                                "depth": grid_step if gy % 3 == 0 else road_width,
                            },
                            tags=["capital_city", "road", "street"],
                        )
                        entities.append(road_ent)
                        continue

                    # Building.
                    btype = "house"
                    if abs_gx % 5 == 0 and abs_gy % 5 == 0:
                        btype = "chapel"
                    elif abs_gx % 4 == 0 and abs_gy % 4 == 0:
                        btype = "well"
                    elif abs_gx % 3 == 0 and abs_gy % 3 == 0:
                        btype = "fountain"

                    if btype == "house":
                        hsize = _size(
                            (grid_step * 0.7) / 100.0,
                            (grid_step * 0.7) / 100.0,
                            random_building_height(self._scale),
                        )
                    elif btype == "chapel":
                        hsize = _size(6.0, 8.0, 10.0)
                    elif btype == "well":
                        hsize = _size(1.5, 1.5, 2.0)
                    else:  # fountain
                        hsize = _size(2.0, 2.0, 3.0)

                    house = EntitySpec(
                        entity_id=f"{prefix}_House_{gx}_{gy}",
                        kind="building",
                        name=f"{btype.capitalize()} {gx}_{gy}",
                        properties={
                            "location": _vec3(cx, cy, loc[2]),
                            "size": hsize,
                        },
                        tags=["capital_city", btype, "building"],
                    )
                    entities.append(house)
                    houses.append(house)

            # Street lamps along main roads.
            lamp_r = town_inner_r + 500 * self._scale
            lamp_count = max(16, int(32 * self._scale))
            for li in range(lamp_count):
                la = li * 360.0 / lamp_count
                lx, ly = _circle_point(loc[0], loc[1], lamp_r, la)
                lamp = EntitySpec(
                    entity_id=f"{prefix}_Lamp{li}",
                    kind="decoration",
                    name=f"Street Lamp {li}",
                    properties={
                        "location": _vec3(lx, ly, loc[2]),
                        "size": _size(0.3, 0.3, 4.0),
                    },
                    tags=["capital_city", "lamp", "street"],
                )
                entities.append(lamp)

        return SpecGraph(
            entities=entities,
            actors=[],
            relations=relations,
            warnings=[],
        )

    def _corner_positions(self, half_w: float, half_d: float) -> List[Tuple[float, float]]:
        loc = self.location
        return [
            (loc[0] - half_w, loc[1] - half_d),  # NW
            (loc[0] + half_w, loc[1] - half_d),  # NE
            (loc[0] + half_w, loc[1] + half_d),  # SE
            (loc[0] - half_w, loc[1] + half_d),  # SW
        ]


def random_building_height(scale: float) -> float:
    """Return a random building height in Unreal scale units (meters)."""
    import random
    base = random.uniform(3.0, 6.0)
    return round(base * scale, 1)

"""
Building creation helper functions for town generation.
Handles creation of individual buildings of various types.
"""
from typing import Dict, Any, List, Optional
import logging
import random

logger = logging.getLogger(__name__)

try:
    from server.actor_sink import ActorSink, _spawn_actor_via_sink_or_direct
except ImportError:
    ActorSink = None  # type: ignore[assignment,misc]
    _spawn_actor_via_sink_or_direct = None  # type: ignore[assignment]


def _create_town_building(
    building_type: str, location: List[float], max_size: float,
    max_height: int, name_prefix: str, building_id: int,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create a single building with variety."""
    try:
        from helpers.advanced_buildings import (
            _create_skyscraper, _create_office_tower, _create_apartment_complex,
            _create_shopping_mall, _create_parking_garage, _create_hotel,
            _create_restaurant, _create_store, _create_apartment_building
        )
        from helpers.house_construction import build_house

        if sink is None:
            import unreal_mcp_server_advanced as server
            construct_house = server.construct_house
            create_tower = server.create_tower
        else:
            construct_house = None
            create_tower = None

        offset_x = random.uniform(-max_size/4, max_size/4)
        offset_y = random.uniform(-max_size/4, max_size/4)
        building_loc = [location[0] + offset_x, location[1] + offset_y, location[2]]

        if building_type == "house":
            styles = ["modern", "cottage"]
            width = random.randint(800, 1200)
            depth = random.randint(600, 1000)
            height = random.randint(300, 500)

            if sink is not None:
                return build_house(
                    None, width, depth, height, building_loc,
                    f"{name_prefix}_{building_id}", "/Engine/BasicShapes/Cube.Cube",
                    random.choice(styles), sink=sink
                )
            else:
                return construct_house(
                    width=width, depth=depth, height=height,
                    location=building_loc,
                    name_prefix=f"{name_prefix}_{building_id}",
                    house_style=random.choice(styles)
                )

        elif building_type == "mansion":
            if sink is not None:
                return build_house(
                    None,
                    random.randint(1500, 2000),
                    random.randint(1200, 1600),
                    random.randint(500, 700),
                    building_loc,
                    f"{name_prefix}_Mansion_{building_id}",
                    "/Engine/BasicShapes/Cube.Cube",
                    "mansion", sink=sink
                )
            else:
                return construct_house(
                    width=random.randint(1500, 2000),
                    depth=random.randint(1200, 1600),
                    height=random.randint(500, 700),
                    location=building_loc,
                    name_prefix=f"{name_prefix}_Mansion_{building_id}",
                    house_style="mansion"
                )

        elif building_type == "tower":
            tower_height = random.randint(max_height//2, max_height)
            base_size = random.randint(3, 6)
            styles = ["cylindrical", "square", "tapered"]

            if sink is not None:
                # Towers via sink use a basic cylinder tower representation
                from server.actor_sink import params_to_spec
                tower_height_local = random.randint(max_height//2, max_height)
                base_size = random.randint(3, 6)
                sink.spawn(params_to_spec({
                    "name": f"{name_prefix}_Tower_{building_id}",
                    "type": "StaticMeshActor",
                    "location": building_loc,
                    "scale": [base_size, base_size, tower_height_local/100],
                    "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
                }, tags=["building", "tower"]))
                return {"success": True, "actors": [f"{name_prefix}_Tower_{building_id}"]}
            else:
                return create_tower(
                    height=tower_height, base_size=base_size,
                    location=building_loc,
                    name_prefix=f"{name_prefix}_Tower_{building_id}",
                    tower_style=random.choice(styles)
                )

        elif building_type == "skyscraper":
            min_height = min(20, max_height//2)
            return _create_skyscraper(
                height=random.randint(min_height, max_height),
                base_width=random.randint(600, 1000),
                base_depth=random.randint(600, 1000),
                location=building_loc,
                name_prefix=f"{name_prefix}_Skyscraper_{building_id}",
                all_actors=all_actors, sink=sink
            )

        elif building_type == "office_tower":
            min_floors = min(15, max_height//2)
            return _create_office_tower(
                floors=random.randint(10, max(min_floors, 10)),
                width=random.randint(800, 1200),
                depth=random.randint(800, 1200),
                location=building_loc,
                name_prefix=f"{name_prefix}_Office_{building_id}",
                all_actors=all_actors, sink=sink
            )

        elif building_type == "apartment_complex":
            min_floors = min(10, max_height//3)
            return _create_apartment_complex(
                floors=random.randint(5, max(min_floors, 5)),
                units_per_floor=random.randint(4, 8),
                location=building_loc,
                name_prefix=f"{name_prefix}_Apartments_{building_id}",
                all_actors=all_actors, sink=sink
            )

        elif building_type == "shopping_mall":
            return _create_shopping_mall(
                width=random.randint(1500, 2500),
                depth=random.randint(1500, 2500),
                floors=random.randint(2, 4),
                location=building_loc,
                name_prefix=f"{name_prefix}_Mall_{building_id}",
                all_actors=all_actors, sink=sink
            )

        elif building_type == "parking_garage":
            return _create_parking_garage(
                levels=random.randint(3, 6),
                width=random.randint(1000, 1500),
                depth=random.randint(800, 1200),
                location=building_loc,
                name_prefix=f"{name_prefix}_Parking_{building_id}",
                all_actors=all_actors, sink=sink
            )

        elif building_type == "hotel":
            min_floors = min(20, max_height//2)
            return _create_hotel(
                floors=random.randint(10, max(min_floors, 10)),
                width=random.randint(1000, 1500),
                depth=random.randint(800, 1200),
                location=building_loc,
                name_prefix=f"{name_prefix}_Hotel_{building_id}",
                all_actors=all_actors, sink=sink
            )

        elif building_type == "restaurant":
            return _create_restaurant(
                width=random.randint(600, 1000),
                depth=random.randint(500, 800),
                location=building_loc,
                name_prefix=f"{name_prefix}_Restaurant_{building_id}",
                all_actors=all_actors, sink=sink
            )

        elif building_type == "store":
            return _create_store(
                width=random.randint(500, 800),
                depth=random.randint(400, 600),
                location=building_loc,
                name_prefix=f"{name_prefix}_Store_{building_id}",
                all_actors=all_actors, sink=sink
            )

        elif building_type == "apartment_building":
            return _create_apartment_building(
                floors=random.randint(3, 5),
                width=random.randint(800, 1200),
                depth=random.randint(600, 1000),
                location=building_loc,
                name_prefix=f"{name_prefix}_AptBuilding_{building_id}",
                all_actors=all_actors, sink=sink
            )

        else:  # commercial fallback
            if sink is not None:
                return build_house(
                    None,
                    random.randint(1000, 1500),
                    random.randint(800, 1200),
                    random.randint(400, 600),
                    building_loc,
                    f"{name_prefix}_Commercial_{building_id}",
                    "/Engine/BasicShapes/Cube.Cube",
                    "modern", sink=sink
                )
            else:
                return construct_house(
                    width=random.randint(1000, 1500),
                    depth=random.randint(800, 1200),
                    height=random.randint(400, 600),
                    location=building_loc,
                    name_prefix=f"{name_prefix}_Commercial_{building_id}",
                    house_style="modern"
                )

    except Exception as e:
        logger.error(f"_create_town_building error: {e}")
        return {"success": False, "actors": []}
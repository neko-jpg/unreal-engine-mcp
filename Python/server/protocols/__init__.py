"""Scene type protocols."""

from __future__ import annotations

from server.protocols.base_scene_protocol import SceneTypeProtocol
from server.protocols.cave_scene_protocol import CAVE_PROTOCOL
from server.protocols.city_scene_protocol import CITY_PROTOCOL
from server.protocols.forest_scene_protocol import FOREST_PROTOCOL
from server.protocols.room_scene_protocol import ROOM_PROTOCOL

SCENE_PROTOCOLS = {
    "cave": CAVE_PROTOCOL,
    "room": ROOM_PROTOCOL,
    "forest": FOREST_PROTOCOL,
    "city": CITY_PROTOCOL,
}

__all__ = [
    "CAVE_PROTOCOL",
    "CITY_PROTOCOL",
    "FOREST_PROTOCOL",
    "ROOM_PROTOCOL",
    "SCENE_PROTOCOLS",
    "SceneTypeProtocol",
]

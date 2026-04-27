from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MeshComponentSpec:
    mesh_path: str
    material_path: Optional[str] = None
    lod_level: int = 0


@dataclass
class CollisionSpec:
    profile: str = "BlockAllDynamic"
    shape: str = "simple_box"  # simple_box | complex_as_simple | custom_convex


@dataclass
class NavSpec:
    behavior: str = "walkable"  # walkable | blocked | jump_link


@dataclass
class AISpec:
    faction: str = "neutral"
    behavior_tree: Optional[str] = None
    patrol_points: List[List[float]] = field(default_factory=list)
    perception_radius: float = 1000.0


@dataclass
class LightSpec:
    light_type: str = "point"  # point | spot | directional
    intensity: float = 5000.0
    color: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    radius: float = 1000.0

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class RealizationPolicy(Enum):
    PROTOTYPE = "prototype"  # Cube/Cylinder, fast
    EDITOR_PREVIEW = "editor_preview"  # Key parts blueprinted, lit
    GAME_READY = "game_ready"  # HISM, collision, NavMesh, LOD
    CINEMATIC = "cinematic"  # High-density mesh, lights, fog
    RUNTIME = "runtime"  # Streaming, World Partition, HLOD


@dataclass
class RealizationSpec:
    policy: RealizationPolicy = RealizationPolicy.PROTOTYPE
    lod_distance: Optional[float] = None
    cull_distance: Optional[float] = None
    streaming_priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

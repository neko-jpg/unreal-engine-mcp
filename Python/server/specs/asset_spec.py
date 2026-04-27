from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AssetSpec:
    """Asset reference with fallback and missing status."""

    asset_id: str
    kind: str  # static_mesh | material | blueprint | texture | sound
    status: str = "present"  # present | missing | generated
    fallback: str = ""
    semantic_tags: List[str] = field(default_factory=list)
    quality: str = "prototype"  # prototype | game_ready | cinematic
    variants: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

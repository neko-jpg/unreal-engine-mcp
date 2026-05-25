"""MoodProfile loader.

A MoodProfile is a YAML file under server/experts/profiles/<name>.yaml. It
contains deterministic, opinionated parameter targets that experts use as their
"home base" for a mood. Experts may further adjust values based on context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("UnrealMCP_Advanced")

_PROFILES_DIR = Path(__file__).parent / "profiles"


@dataclass
class MoodProfile:
    name: str
    description: str = ""
    lighting: Dict[str, Any] = field(default_factory=dict)
    material: Dict[str, Any] = field(default_factory=dict)
    atmosphere: Dict[str, Any] = field(default_factory=dict)
    audio: Dict[str, Any] = field(default_factory=dict)
    vfx: Dict[str, Any] = field(default_factory=dict)
    post_process: Dict[str, Any] = field(default_factory=dict)

    def domain(self, name: str) -> Dict[str, Any]:
        return getattr(self, name, {}) or {}


def _safe_load_yaml(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except Exception:
        # Minimal fallback YAML reader for our flat key: value style.
        data: Dict[str, Any] = {}
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if ":" in line:
                k, _, v = line.partition(":")
                data[k.strip()] = v.strip()
        return data


def list_profiles() -> List[str]:
    if not _PROFILES_DIR.exists():
        return []
    return sorted(p.stem for p in _PROFILES_DIR.glob("*.yaml"))


def load_profile(name: str) -> Optional[MoodProfile]:
    if not name:
        return None
    path = _PROFILES_DIR / f"{name}.yaml"
    if not path.exists():
        logger.warning("MoodProfile %s not found at %s", name, path)
        return None
    raw = _safe_load_yaml(path)
    return MoodProfile(
        name=str(raw.get("name", name)),
        description=str(raw.get("description", "")),
        lighting=dict(raw.get("lighting") or {}),
        material=dict(raw.get("material") or {}),
        atmosphere=dict(raw.get("atmosphere") or {}),
        audio=dict(raw.get("audio") or {}),
        vfx=dict(raw.get("vfx") or {}),
        post_process=dict(raw.get("post_process") or {}),
    )

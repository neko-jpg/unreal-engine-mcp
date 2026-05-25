"""SceneContextPack and small Brief dataclasses for v3.0."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SceneObjectBrief:
    mcp_id: str
    kind: Optional[str] = None
    name: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    group: Optional[str] = None
    sync_status: Optional[str] = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "SceneObjectBrief":
        tags = [t for t in (raw.get("tags") or []) if isinstance(t, str)]
        return cls(
            mcp_id=str(raw.get("mcp_id", "")),
            kind=_infer_object_kind(raw, tags),
            name=raw.get("name") or raw.get("desired_name"),
            tags=tags,
            group=raw.get("group"),
            sync_status=raw.get("sync_status"),
        )


def _infer_object_kind(raw: Dict[str, Any], tags: List[str]) -> Optional[str]:
    direct = raw.get("kind") or raw.get("type")
    if direct:
        return str(direct)

    metadata = raw.get("metadata")
    if isinstance(metadata, dict):
        meta_kind = metadata.get("kind") or metadata.get("scene_kind")
        if meta_kind:
            return str(meta_kind)

    for tag in tags:
        lower = tag.lower()
        for prefix in ("kind:", "scene_kind:", "layout_kind:"):
            if lower.startswith(prefix):
                return lower[len(prefix):]

    known = {
        "floor",
        "wall",
        "ceiling",
        "stone",
        "rock",
        "light",
        "torch",
        "fog",
        "atmosphere",
    }
    for tag in tags:
        lower = tag.lower()
        if lower in known:
            return lower

    actor_type = raw.get("actor_type")
    return str(actor_type) if actor_type else None


@dataclass
class EntityBrief:
    entity_id: str
    kind: Optional[str] = None
    name: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "EntityBrief":
        return cls(
            entity_id=str(raw.get("entity_id") or raw.get("id") or ""),
            kind=raw.get("kind"),
            name=raw.get("name"),
            tags=[t for t in (raw.get("tags") or []) if isinstance(t, str)],
        )


@dataclass
class ComponentBrief:
    entity_id: str
    component_type: str
    name: str
    sync_status: Optional[str] = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ComponentBrief":
        return cls(
            entity_id=str(raw.get("entity_id", "")),
            component_type=str(raw.get("component_type", "")),
            name=str(raw.get("name", "")),
            sync_status=raw.get("sync_status"),
        )


@dataclass
class AssetBrief:
    asset_id: str
    kind: Optional[str] = None
    quality: Optional[str] = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "AssetBrief":
        return cls(
            asset_id=str(raw.get("asset_id", "")),
            kind=raw.get("kind"),
            quality=raw.get("quality"),
        )


@dataclass
class SnapshotBrief:
    snapshot_id: str
    name: str
    revision: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "SnapshotBrief":
        return cls(
            snapshot_id=str(raw.get("id") or raw.get("snapshot_id") or ""),
            name=str(raw.get("name", "")),
            revision=raw.get("revision"),
            created_at=str(raw.get("created_at")) if raw.get("created_at") else None,
        )


@dataclass
class OperationBrief:
    operation_id: Optional[str]
    action: Optional[str]
    mcp_id: Optional[str]
    status: Optional[str]
    reason: Optional[str]
    patch_id: Optional[str] = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "OperationBrief":
        return cls(
            operation_id=raw.get("operation_id") or raw.get("id"),
            action=raw.get("action"),
            mcp_id=raw.get("mcp_id"),
            status=raw.get("status"),
            reason=raw.get("reason"),
            patch_id=raw.get("patch_id"),
        )


@dataclass
class SceneContextPack:
    """Compact aggregate view of a scene used by the IntentResolver / experts."""

    scene_id: str
    object_count: int = 0
    entity_count: int = 0
    component_count: int = 0
    asset_count: int = 0
    objects_by_kind: Dict[str, List[SceneObjectBrief]] = field(default_factory=dict)
    entities_by_kind: Dict[str, List[EntityBrief]] = field(default_factory=dict)
    components_by_type: Dict[str, List[ComponentBrief]] = field(default_factory=dict)
    assets_by_kind: Dict[str, List[AssetBrief]] = field(default_factory=dict)
    snapshots: List[SnapshotBrief] = field(default_factory=list)
    recent_operations: List[OperationBrief] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        def _pack(items: List[Any]) -> List[Dict[str, Any]]:
            return [item.__dict__ for item in items]

        return {
            "scene_id": self.scene_id,
            "object_count": self.object_count,
            "entity_count": self.entity_count,
            "component_count": self.component_count,
            "asset_count": self.asset_count,
            "objects_by_kind": {k: _pack(v) for k, v in self.objects_by_kind.items()},
            "entities_by_kind": {k: _pack(v) for k, v in self.entities_by_kind.items()},
            "components_by_type": {k: _pack(v) for k, v in self.components_by_type.items()},
            "assets_by_kind": {k: _pack(v) for k, v in self.assets_by_kind.items()},
            "snapshots": _pack(self.snapshots),
            "recent_operations": _pack(self.recent_operations),
            "warnings": list(self.warnings),
        }

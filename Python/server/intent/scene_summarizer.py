"""SceneSummarizer - builds SceneContextPack from scene-syncd data.

Token budget: target 2k tokens for 200 actors/components.
We approximate tokens as len(json) / 4 (English-ish rule of thumb).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List, Optional

from server.intent.scene_context import (
    AssetBrief,
    ComponentBrief,
    EntityBrief,
    OperationBrief,
    SceneContextPack,
    SceneObjectBrief,
    SnapshotBrief,
)

logger = logging.getLogger("UnrealMCP_Advanced")

# Hard caps so a 1000-object scene still fits under 2k tokens.
MAX_PER_KIND = 4
MAX_PER_COMPONENT_TYPE = 5
MAX_PER_ASSET_KIND = 4
MAX_SNAPSHOTS = 5
MAX_OPERATIONS = 10


def estimate_tokens(payload: Any) -> int:
    """Rough token estimator: 4 chars ~= 1 token for English/JSON."""
    text = payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True)
    return max(1, len(text) // 4)


def _group_by(items: Iterable[Any], key: str) -> Dict[str, List[Any]]:
    out: Dict[str, List[Any]] = {}
    for item in items:
        bucket = getattr(item, key, None) or "unknown"
        out.setdefault(str(bucket), []).append(item)
    return out


def _sample(items: List[Any], cap: int) -> List[Any]:
    if len(items) <= cap:
        return items
    keep = list(items[:cap])
    return keep


class SceneSummarizer:
    """Pulls scene-syncd data and produces a SceneContextPack."""

    def __init__(self, client=None):
        """``client`` is any object with ``call_scene_syncd(path, payload)``.

        When None, we lazy-import the default scene-syncd client.
        """
        self._client = client

    def _call(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self._client is not None:
            return self._client.call_scene_syncd(path, payload)
        from server.scene_client import call_scene_syncd
        return call_scene_syncd(path, payload)

    @staticmethod
    def _data(raw: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(raw, dict):
            data = raw.get("data")
            if isinstance(data, dict):
                return data
        return raw or {}

    def build(self, scene_id: str) -> SceneContextPack:
        warnings: List[str] = []

        objects_raw = self._fetch_objects(scene_id, warnings)
        entities_raw = self._fetch_entities(scene_id, warnings)
        components_raw = self._fetch_components(scene_id, warnings)
        assets_raw = self._fetch_assets(scene_id, warnings)
        snapshots_raw = self._fetch_snapshots(scene_id, warnings)
        operations_raw = self._fetch_recent_operations(scene_id, warnings)

        objects = [SceneObjectBrief.from_dict(o) for o in objects_raw]
        entities = [EntityBrief.from_dict(e) for e in entities_raw]
        components = [ComponentBrief.from_dict(c) for c in components_raw]
        assets = [AssetBrief.from_dict(a) for a in assets_raw]
        snapshots = [SnapshotBrief.from_dict(s) for s in snapshots_raw][-MAX_SNAPSHOTS:]
        operations = [OperationBrief.from_dict(o) for o in operations_raw][-MAX_OPERATIONS:]

        pack = SceneContextPack(
            scene_id=scene_id,
            object_count=len(objects),
            entity_count=len(entities),
            component_count=len(components),
            asset_count=len(assets),
            objects_by_kind={
                k: _sample(v, MAX_PER_KIND) for k, v in _group_by(objects, "kind").items()
            },
            entities_by_kind={
                k: _sample(v, MAX_PER_KIND) for k, v in _group_by(entities, "kind").items()
            },
            components_by_type={
                k: _sample(v, MAX_PER_COMPONENT_TYPE)
                for k, v in _group_by(components, "component_type").items()
            },
            assets_by_kind={
                k: _sample(v, MAX_PER_ASSET_KIND) for k, v in _group_by(assets, "kind").items()
            },
            snapshots=snapshots,
            recent_operations=operations,
            warnings=warnings,
        )
        return pack

    # ---- individual fetchers ----------------------------------------------
    def _fetch_objects(self, scene_id: str, warnings: List[str]) -> List[Dict[str, Any]]:
        raw = self._call("/objects/list", {"scene_id": scene_id})
        data = self._data(raw)
        items = data.get("objects") if isinstance(data, dict) else None
        if not isinstance(items, list):
            warnings.append("scene-syncd /objects/list returned no objects array")
            return []
        return items

    def _fetch_entities(self, scene_id: str, warnings: List[str]) -> List[Dict[str, Any]]:
        raw = self._call("/entities/list", {"scene_id": scene_id})
        data = self._data(raw)
        items = data.get("entities") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        return items

    def _fetch_components(self, scene_id: str, warnings: List[str]) -> List[Dict[str, Any]]:
        raw = self._call("/components/list", {"scene_id": scene_id})
        data = self._data(raw)
        items = data.get("components") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        return items

    def _fetch_assets(self, scene_id: str, warnings: List[str]) -> List[Dict[str, Any]]:
        try:
            raw = self._call("/assets/list", {"scene_id": scene_id})
        except Exception as exc:
            warnings.append(f"assets/list call failed: {exc}")
            return []
        data = self._data(raw)
        items = data.get("assets") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        return items

    def _fetch_snapshots(self, scene_id: str, warnings: List[str]) -> List[Dict[str, Any]]:
        raw = self._call("/snapshots/list", {"scene_id": scene_id})
        data = self._data(raw)
        items = data.get("snapshots") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        return items

    def _fetch_recent_operations(self, scene_id: str, warnings: List[str]) -> List[Dict[str, Any]]:
        try:
            raw = self._call("/operations/recent", {"scene_id": scene_id, "limit": MAX_OPERATIONS})
        except Exception as exc:
            warnings.append(f"operations/recent call failed: {exc}")
            return []
        data = self._data(raw)
        items = data.get("operations") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        return items


def summarize_scene(scene_id: str, client=None) -> SceneContextPack:
    """Convenience helper."""
    return SceneSummarizer(client=client).build(scene_id)

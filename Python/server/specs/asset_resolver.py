"""Asset catalog loader and resolver.

Reads Python/assets/asset_catalog.yaml and resolves assets by ID,
variant, and quality level.
"""

import os
from typing import Any, Dict, List, Optional

import yaml


class AssetResolver:
    """Resolves asset IDs to paths using the asset catalog YAML."""

    _catalog: Optional[Dict[str, Any]] = None

    @classmethod
    def _load_catalog(cls) -> Dict[str, Any]:
        if cls._catalog is not None:
            return cls._catalog
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "assets", "asset_catalog.yaml")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            cls._catalog = data.get("assets", {})
        else:
            cls._catalog = {}
        return cls._catalog

    @classmethod
    def resolve(
        cls,
        asset_id: str,
        variant: str = "medieval",
        quality: str = "prototype",
    ) -> Dict[str, Any]:
        """Resolve an asset ID to its path and metadata.

        Returns a dict with:
        - path: the resolved asset path (mesh, blueprint, or material)
        - kind: static_mesh | material | blueprint | texture | sound
        - fallback: fallback path if the primary is missing
        - collision_profile: collision setting
        - navmesh: navmesh behavior
        - default_scale: [x, y, z]
        - status: "present" if found in catalog, "missing" otherwise
        """
        catalog = cls._load_catalog()
        entry = catalog.get(asset_id, {})

        if not entry:
            return {
                "path": "",
                "kind": "static_mesh",
                "fallback": "/Engine/BasicShapes/Cube.Cube",
                "collision_profile": "BlockAll",
                "navmesh": "obstacle",
                "default_scale": [1.0, 1.0, 1.0],
                "status": "missing",
                "variant": variant,
                "quality": quality,
            }

        variants = entry.get("variants", {})
        variant_data = variants.get(variant, next(iter(variants.values()), {}))

        kind = entry.get("kind", "static_mesh")
        path = ""
        if kind == "static_mesh":
            path = variant_data.get("mesh", "")
        elif kind == "material":
            path = variant_data.get("material", "")
        elif kind == "blueprint":
            path = variant_data.get("blueprint", "")

        fallback = entry.get("fallback", "/Engine/BasicShapes/Cube.Cube")
        status = "present" if path else "missing"
        if status == "missing":
            path = fallback

        return {
            "path": path,
            "kind": kind,
            "fallback": fallback,
            "collision_profile": entry.get("collision_profile", "BlockAll"),
            "navmesh": entry.get("navmesh", "obstacle"),
            "default_scale": entry.get("default_scale", [1.0, 1.0, 1.0]),
            "status": status,
            "variant": variant,
            "quality": quality,
        }

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the cached catalog, forcing a reload on next access."""
        cls._catalog = None

    @classmethod
    def reload(cls) -> Dict[str, Any]:
        """Clear cache and reload the catalog from disk."""
        cls.clear_cache()
        return cls._load_catalog()

    @classmethod
    def list_assets(cls) -> List[str]:
        """Return all registered asset IDs."""
        return list(cls._load_catalog().keys())

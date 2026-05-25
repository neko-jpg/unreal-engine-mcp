"""PatchCompiler - lowers a DesignPatch to scene-syncd / UE calls.

For PR6 we:
- write ComponentPatches via POST /components/upsert (carries desired_hash,
  revision, operation_id in properties.__sync metadata).
- write ObjectPatches via /objects/bulk-upsert (delegates to existing
  scene_crud helpers).
- emit a list of (component_patch, capability) tuples for the executor to
  consume so the same patch can be applied via direct UE commands in MVP.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from server.planning.capability_registry import (
    Capability,
    CapabilityRegistry,
    get_default_registry,
)
from server.planning.design_patch import (
    AssetPatch,
    ComponentPatch,
    DesignPatch,
    DirectCommandPatch,
    ObjectPatch,
)

logger = logging.getLogger("UnrealMCP_Advanced")


@dataclass
class CompiledPatch:
    """Lowered patch ready for execution."""

    patch_id: str
    scene_id: str
    component_upserts: List[Dict[str, Any]] = field(default_factory=list)
    asset_upserts: List[Dict[str, Any]] = field(default_factory=list)
    object_upserts: List[Dict[str, Any]] = field(default_factory=list)
    direct_commands: List[Tuple[Capability, Dict[str, Any]]] = field(default_factory=list)
    rust_apply_keys: List[Dict[str, str]] = field(default_factory=list)
    python_apply: List[Tuple[ComponentPatch, Capability]] = field(default_factory=list)


def _sync_metadata(cp: ComponentPatch, patch_id: str) -> Dict[str, Any]:
    return {
        "desired_hash": cp.desired_hash,
        "operation_id": cp.operation_id,
        "patch_id": patch_id,
        "capability_id": cp.capability_id,
    }


class PatchCompiler:
    """Lowers a DesignPatch into network-shaped payloads."""

    # component_types that should go through the Rust component_applier when
    # available (PR7). For PR6 these are also handled by the Python executor as
    # a fallback so the apply_safe path works without Rust changes.
    RUST_HANDLED = {"material", "light"}

    def __init__(self, registry: Optional[CapabilityRegistry] = None) -> None:
        self.registry = registry or get_default_registry()

    def compile(self, patch: DesignPatch) -> CompiledPatch:
        patch.fill_component_hashes()
        compiled = CompiledPatch(patch_id=patch.patch_id, scene_id=patch.scene_id)

        for cp in patch.component_patches:
            payload = self._component_payload(cp, patch.patch_id)
            compiled.component_upserts.append(payload)
            if cp.capability_id:
                cap = self.registry.get(cp.capability_id)
                if cap is not None:
                    if cp.component_type in self.RUST_HANDLED:
                        compiled.rust_apply_keys.append({
                            "scene_id": cp.scene_id,
                            "entity_id": cp.entity_id,
                            "component_type": cp.component_type,
                            "name": cp.name,
                        })
                    compiled.python_apply.append((cp, cap))

        for ap in patch.asset_patches:
            compiled.asset_upserts.append(self._asset_payload(ap))

        for op in patch.object_patches:
            compiled.object_upserts.append(self._object_payload(op))

        for dc in patch.direct_commands:
            cap = self.registry.get(dc.capability_id)
            if cap is None:
                logger.warning("Unknown direct capability id: %s", dc.capability_id)
                continue
            compiled.direct_commands.append((cap, dict(dc.params)))

        return compiled

    # ------------------------------------------------------------------
    def _component_payload(self, cp: ComponentPatch, patch_id: str) -> Dict[str, Any]:
        properties = dict(cp.properties)
        metadata = dict(cp.metadata)
        # Embed the sync metadata into both properties (for downstream apply)
        # and the top-level metadata (so Rust planner can see it without a
        # schema change).
        sync_md = _sync_metadata(cp, patch_id)
        metadata.setdefault("__sync", sync_md)
        return {
            "scene_id": cp.scene_id,
            "entity_id": cp.entity_id,
            "component_type": cp.component_type,
            "name": cp.name,
            "properties": properties,
            "metadata": metadata,
        }

    def _asset_payload(self, ap: AssetPatch) -> Dict[str, Any]:
        metadata = dict(ap.metadata)
        if ap.properties:
            metadata.setdefault("properties", ap.properties)
        return {
            "scene_id": ap.scene_id,
            "asset_id": ap.asset_id,
            "kind": ap.kind,
            "metadata": metadata,
            "variants": ap.properties.get("variants", {}) if isinstance(ap.properties, dict) else {},
            "semantic_tags": ap.metadata.get("semantic_tags", []) if isinstance(ap.metadata, dict) else [],
        }

    def _object_payload(self, op: ObjectPatch) -> Dict[str, Any]:
        return {
            "mcp_id": op.mcp_id,
            "action": op.action,
            "properties": op.properties,
            "tags": list(op.tags),
            "reason": op.reason,
        }


def compile_patch(patch: DesignPatch) -> CompiledPatch:
    return PatchCompiler().compile(patch)

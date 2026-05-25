"""DesignPatch dataclasses for React-for-UE v3.0."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional

RiskLevel = Literal["safe", "review", "destructive"]
PatchAction = Literal["create", "update", "delete"]


def new_patch_id() -> str:
    rand = uuid.uuid4().hex[:8]
    ts = int(time.time())
    return f"patch_{ts}_{rand}"


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def compute_desired_hash(properties: Dict[str, Any]) -> str:
    payload = _canonical_json(properties)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def compute_component_key(scene_id: str, entity_id: str, component_type: str, name: str) -> str:
    return f"{scene_id}|{entity_id}|{component_type}|{name}"


def compute_operation_id(patch_id: str, component_key: str, desired_hash: str) -> str:
    payload = f"{patch_id}|{component_key}|{desired_hash}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


@dataclass
class Intent:
    raw_text: str
    scene_id: str
    action: Literal["create", "modify", "refine", "restore", "describe", "compare"] = "modify"
    domains: List[str] = field(default_factory=list)
    target_selector: Optional[Dict[str, Any]] = None
    mood: Optional[str] = None
    style_profile: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    risk_hint: Optional[RiskLevel] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ObjectPatch:
    mcp_id: str
    action: PatchAction = "update"
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    reason: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class EntityPatch:
    entity_id: str
    kind: str
    action: PatchAction = "update"
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    reason: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class ComponentPatch:
    scene_id: str
    entity_id: str
    component_type: str
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    action: PatchAction = "update"
    capability_id: Optional[str] = None
    reason: Optional[str] = None
    desired_hash: Optional[str] = None
    operation_id: Optional[str] = None

    def component_key(self) -> str:
        return compute_component_key(self.scene_id, self.entity_id, self.component_type, self.name)

    def fill_derived(self, patch_id: str) -> None:
        self.desired_hash = compute_desired_hash(self.properties)
        self.operation_id = compute_operation_id(patch_id, self.component_key(), self.desired_hash)

    def to_dict(self):
        return asdict(self)


@dataclass
class AssetPatch:
    scene_id: str
    asset_id: str
    kind: str
    action: PatchAction = "update"
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class DirectCommandPatch:
    capability_id: str
    command: str
    params: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class ValidationProbe:
    probe_id: str
    description: str
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


PatchOperation = Any


@dataclass
class PatchSafetyReport:
    risk_level: RiskLevel = "safe"
    requires_approval: bool = False
    operation_count: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    capability_misses: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class DesignPatch:
    patch_id: str
    scene_id: str
    intent: Intent
    summary: str = ""
    risk_level: RiskLevel = "safe"
    max_operations: int = 100
    object_patches: List[ObjectPatch] = field(default_factory=list)
    entity_patches: List[EntityPatch] = field(default_factory=list)
    component_patches: List[ComponentPatch] = field(default_factory=list)
    asset_patches: List[AssetPatch] = field(default_factory=list)
    direct_commands: List[DirectCommandPatch] = field(default_factory=list)
    validation_probes: List[ValidationProbe] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    safety_report: Optional[PatchSafetyReport] = None

    def operation_count(self) -> int:
        return (
            len(self.object_patches)
            + len(self.entity_patches)
            + len(self.component_patches)
            + len(self.asset_patches)
            + len(self.direct_commands)
        )

    def to_dict(self):
        def _serialize_list(items):
            return [item.to_dict() for item in items]
        return {
            "patch_id": self.patch_id,
            "scene_id": self.scene_id,
            "intent": self.intent.to_dict(),
            "summary": self.summary,
            "risk_level": self.risk_level,
            "max_operations": self.max_operations,
            "operation_count": self.operation_count(),
            "object_patches": _serialize_list(self.object_patches),
            "entity_patches": _serialize_list(self.entity_patches),
            "component_patches": _serialize_list(self.component_patches),
            "asset_patches": _serialize_list(self.asset_patches),
            "direct_commands": _serialize_list(self.direct_commands),
            "validation_probes": _serialize_list(self.validation_probes),
            "warnings": list(self.warnings),
            "safety_report": self.safety_report.to_dict() if self.safety_report else None,
        }

    def fill_component_hashes(self) -> None:
        for cp in self.component_patches:
            cp.fill_derived(self.patch_id)

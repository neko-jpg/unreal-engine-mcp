"""PatchExecutor - applies a CompiledPatch via Hybrid (Python+Rust) path.

PR6 ships the Python side: writes desired state to scene-syncd, executes
direct UE commands (fog/atmosphere/audio/vfx and the material/light fallback),
records every step into scene_operation, and enforces idempotency via
operation_id.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from server.planning.capability_registry import Capability
from server.planning.design_patch import (
    ComponentPatch,
    DesignPatch,
)
from server.planning.patch_compiler import CompiledPatch, PatchCompiler
from server.planning.safety import SafetyChecker

logger = logging.getLogger("UnrealMCP_Advanced")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class OperationResult:
    operation_id: Optional[str]
    capability_id: str
    command: str
    status: str  # ok|skipped|noop|error|conflict
    reason: str = ""
    target: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutorReport:
    patch_id: str
    scene_id: str
    snapshot_id: Optional[str] = None
    succeeded: int = 0
    failed: int = 0
    noop: int = 0
    operations: List[OperationResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patch_id": self.patch_id,
            "scene_id": self.scene_id,
            "snapshot_id": self.snapshot_id,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "noop": self.noop,
            "operations": [o.to_dict() for o in self.operations],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


# ---------------------------------------------------------------------------
# Transport adapters
# ---------------------------------------------------------------------------


def _default_scene_syncd():
    from server.scene_client import call_scene_syncd
    return call_scene_syncd


def _default_unreal_connection():
    from server.core import get_unreal_connection
    return get_unreal_connection()


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


class PatchExecutor:
    """Apply a DesignPatch using the Hybrid path."""

    def __init__(
        self,
        scene_syncd: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
        unreal_connection: Any = None,
    ) -> None:
        self._sd = scene_syncd
        self._unreal = unreal_connection
        # Track operation ids seen in this process run so the *same* executor
        # instance can deduplicate even before scene-syncd records them.
        self._seen_op_ids: set[str] = set()

    # ------------------------------------------------------------------
    @property
    def scene_syncd(self):
        return self._sd or _default_scene_syncd()

    @property
    def unreal(self):
        return self._unreal or _default_unreal_connection()

    # ------------------------------------------------------------------
    def apply(
        self,
        patch: DesignPatch,
        *,
        create_snapshot: bool = True,
        require_safe_only: bool = True,
        approve: bool = False,
    ) -> ExecutorReport:
        import time as _time

        safety = patch.safety_report or SafetyChecker().check(patch)
        report = ExecutorReport(patch_id=patch.patch_id, scene_id=patch.scene_id)
        report.warnings.extend(patch.warnings)

        t_start = _time.perf_counter()
        logger.info(
            "patch.apply start",
            extra={
                "patch_id": patch.patch_id,
                "scene_id": patch.scene_id,
                "risk_level": safety.risk_level,
                "operation_count": safety.operation_count,
                "require_safe_only": require_safe_only,
                "approve": approve,
            },
        )

        if safety.errors:
            report.errors.extend(safety.errors)
            logger.warning(
                "patch.apply rejected (safety errors)",
                extra={"patch_id": patch.patch_id, "errors": safety.errors},
            )
            return report

        if safety.risk_level == "destructive" and not approve:
            report.errors.append("destructive patch requires approve=True")
            logger.warning(
                "patch.apply rejected (destructive without approval)",
                extra={"patch_id": patch.patch_id},
            )
            return report

        if require_safe_only and safety.risk_level == "destructive":
            report.errors.append("apply_safe rejects destructive patches; use apply_all with approve=True")
            logger.warning(
                "patch.apply rejected (destructive in apply_safe)",
                extra={"patch_id": patch.patch_id},
            )
            return report

        if create_snapshot:
            snap = self._create_snapshot(patch)
            if snap is not None:
                report.snapshot_id = snap

        compiled = PatchCompiler().compile(patch)

        # 1. write desired state to DB
        self._upsert_components(compiled, report)
        self._upsert_assets(compiled, report)
        self._upsert_objects(compiled, report)

        # 2. apply via direct UE commands for the Python-handled portion
        self._apply_python(compiled, report)

        # 3. fire any explicit direct commands the experts emitted
        self._apply_direct_commands(compiled, report)

        elapsed_ms = (_time.perf_counter() - t_start) * 1000.0
        logger.info(
            "patch.apply done",
            extra={
                "patch_id": patch.patch_id,
                "scene_id": patch.scene_id,
                "snapshot_id": report.snapshot_id,
                "succeeded": report.succeeded,
                "noop": report.noop,
                "failed": report.failed,
                "elapsed_ms": round(elapsed_ms, 2),
            },
        )
        return report

    # ------------------------------------------------------------------
    def _create_snapshot(self, patch: DesignPatch) -> Optional[str]:
        payload = {
            "scene_id": patch.scene_id,
            "name": f"before_{patch.patch_id}",
            "description": f"Auto-snapshot before {patch.patch_id}",
        }
        raw = self.scene_syncd("/snapshots/create", payload)
        data = raw.get("data") if isinstance(raw, dict) else None
        snap = None
        if isinstance(data, dict):
            snap = data.get("snapshot_id") or data.get("id") or (data.get("snapshot") or {}).get("id")
        return snap

    def _upsert_components(self, compiled: CompiledPatch, report: ExecutorReport) -> None:
        for payload in compiled.component_upserts:
            raw = self.scene_syncd("/components/upsert", payload)
            if isinstance(raw, dict) and raw.get("success", True) is False:
                report.warnings.append(
                    f"components/upsert failed for {payload.get('component_type')}"
                )

    def _upsert_assets(self, compiled: CompiledPatch, report: ExecutorReport) -> None:
        # Best-effort: not all deployments expose /assets/upsert. Skip silently
        # if missing so MVP works even without that route.
        for payload in compiled.asset_upserts:
            try:
                self.scene_syncd("/assets/upsert", payload)
            except Exception as exc:  # noqa: BLE001
                report.warnings.append(f"asset_upsert failed: {exc}")

    def _upsert_objects(self, compiled: CompiledPatch, report: ExecutorReport) -> None:
        if not compiled.object_upserts:
            return
        # Translate to /objects/bulk-upsert shape.
        payload = {
            "scene_id": compiled.scene_id,
            "objects": [
                {
                    "mcp_id": o["mcp_id"],
                    "tags": o["tags"],
                    "properties": o["properties"],
                    "deleted": o["action"] == "delete",
                }
                for o in compiled.object_upserts
            ],
        }
        self.scene_syncd("/objects/bulk-upsert", payload)

    def _record_operation(
        self,
        report: ExecutorReport,
        cp: ComponentPatch,
        cap: Capability,
        status: str,
        reason: str,
    ) -> None:
        op = OperationResult(
            operation_id=cp.operation_id,
            capability_id=cap.capability_id,
            command=cap.command,
            status=status,
            reason=reason,
            target={
                "scene_id": cp.scene_id,
                "entity_id": cp.entity_id,
                "component_type": cp.component_type,
                "name": cp.name,
            },
        )
        report.operations.append(op)
        if status == "ok":
            report.succeeded += 1
        elif status == "noop":
            report.noop += 1
        elif status in {"error", "conflict"}:
            report.failed += 1
        # Try to persist to scene-syncd; ignore errors (operations log is best-effort)
        try:
            self.scene_syncd(
                "/operations/record",
                {
                    "scene_id": cp.scene_id,
                    "operation_id": cp.operation_id,
                    "patch_id": report.patch_id,
                    "capability_id": cap.capability_id,
                    "command": cap.command,
                    "status": status,
                    "reason": reason,
                    "target": op.target,
                },
            )
        except Exception:  # noqa: BLE001
            pass

    def _apply_python(self, compiled: CompiledPatch, report: ExecutorReport) -> None:
        for cp, cap in compiled.python_apply:
            if cp.operation_id and cp.operation_id in self._seen_op_ids:
                self._record_operation(report, cp, cap, "noop", "duplicate operation_id in process cache")
                continue
            try:
                command_params = self._command_params(cp, cap)
                if self._should_noop_placeholder_asset(cap, command_params):
                    self._record_operation(report, cp, cap, "noop", "placeholder asset is not installed in this project")
                    continue
                result = self.unreal.send_command(cap.command, command_params)
                ok = bool(result.get("success", True)) if isinstance(result, dict) else True
                status = "ok" if ok else "error"
                reason = (result or {}).get("error", "") if isinstance(result, dict) and not ok else f"executed {cap.command}"
                self._record_operation(report, cp, cap, status, reason)
                if cp.operation_id:
                    self._seen_op_ids.add(cp.operation_id)
            except Exception as exc:  # noqa: BLE001
                self._record_operation(report, cp, cap, "error", f"{type(exc).__name__}: {exc}")

    @staticmethod
    def _should_noop_placeholder_asset(cap: Capability, command_params: Dict[str, Any]) -> bool:
        if cap.command == "spawn_ambient_sound":
            sound_path = str(command_params.get("sound_path", ""))
            return sound_path.startswith("/Game/MCP/Audio/")
        if cap.command == "add_niagara_component":
            system_path = str(command_params.get("system_path", ""))
            return system_path.startswith("/Game/MCP/VFX/")
        return False

    def _apply_direct_commands(
        self, compiled: CompiledPatch, report: ExecutorReport
    ) -> None:
        for cap, params in compiled.direct_commands:
            try:
                result = self.unreal.send_command(cap.command, params)
                ok = bool(result.get("success", True)) if isinstance(result, dict) else True
                report.operations.append(
                    OperationResult(
                        operation_id=None,
                        capability_id=cap.capability_id,
                        command=cap.command,
                        status="ok" if ok else "error",
                        reason="direct command",
                    )
                )
                if ok:
                    report.succeeded += 1
                else:
                    report.failed += 1
            except Exception as exc:  # noqa: BLE001
                report.failed += 1
                report.errors.append(f"{cap.capability_id}: {exc}")

    # ------------------------------------------------------------------
    @staticmethod
    def _command_params(cp: ComponentPatch, cap: Capability) -> Dict[str, Any]:
        """Translate ComponentPatch.properties into UE command param shape.

        We deliberately keep this small for MVP and let the UE handlers ignore
        extra keys. Anything UE does not understand is dropped on the floor at
        the bridge layer with a warning.
        """
        props = dict(cp.properties)
        actor_name = props.get("actor_name") or props.get("desired_name") or props.get("actor_mcp_id")
        params: Dict[str, Any] = dict(props)
        if cap.command == "set_light_intensity":
            return {
                "actor_name": actor_name,
                "intensity": float(props.get("intensity", 5000.0 * float(props.get("intensity_multiplier", 1.0)))),
            }
        if cap.command == "apply_material_to_actor":
            return {
                "actor_name": actor_name,
                "material_path": props.get("material_path", "/Engine/BasicShapes/BasicShapeMaterial"),
                "material_slot": int(props.get("material_slot", 0)),
            }
        if cap.command == "set_height_fog_properties":
            mapped: Dict[str, Any] = {"actor_name": actor_name or "Cave_Fog"}
            for key in ("fog_density", "fog_height_falloff", "fog_max_opacity", "start_distance"):
                if key in props:
                    mapped[key] = props[key]
            color = props.get("light_inscattering_color") or props.get("fog_color")
            if color:
                mapped["light_inscattering_color"] = color
            return mapped
        if cap.command == "add_niagara_component":
            params.setdefault("actor_name", actor_name or "Cave_Floor")
            params.setdefault("component_name", cp.name)
        if cap.command == "spawn_ambient_sound":
            params.setdefault("actor_name", f"Cave_Ambient_{cp.name}")
            if "sound_name" in params and "sound_path" not in params:
                params["sound_path"] = f"/Game/MCP/Audio/{params['sound_name']}"
        params.setdefault("__component", {
            "scene_id": cp.scene_id,
            "entity_id": cp.entity_id,
            "component_type": cp.component_type,
            "name": cp.name,
            "operation_id": cp.operation_id,
        })
        return params


# ---------------------------------------------------------------------------
# scene_edit(apply_safe / apply_all) entry points consumed by dialog_tools
# ---------------------------------------------------------------------------


def apply_patch_safe(
    patch: DesignPatch,
    *,
    create_snapshot: bool,
    approve: bool,
    response: Dict[str, Any],
) -> Dict[str, Any]:
    return _apply(patch, create_snapshot=create_snapshot, require_safe_only=True, approve=approve, response=response)


def apply_patch_all(
    patch: DesignPatch,
    *,
    create_snapshot: bool,
    approve: bool,
    response: Dict[str, Any],
) -> Dict[str, Any]:
    return _apply(patch, create_snapshot=create_snapshot, require_safe_only=False, approve=approve, response=response)


def _apply(
    patch: DesignPatch,
    *,
    create_snapshot: bool,
    require_safe_only: bool,
    approve: bool,
    response: Dict[str, Any],
) -> Dict[str, Any]:
    executor = PatchExecutor()
    report = executor.apply(
        patch,
        create_snapshot=create_snapshot,
        require_safe_only=require_safe_only,
        approve=approve,
    )
    response = dict(response)
    response["snapshot_id"] = report.snapshot_id
    response["succeeded"] = report.succeeded
    response["failed"] = report.failed
    response["noop"] = report.noop
    response["operations"] = [o.to_dict() for o in report.operations]
    if report.errors:
        response["success"] = False
        response.setdefault("errors", []).extend(report.errors)
    return response

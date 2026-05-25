"""Safety analysis of a DesignPatch.

SafetyChecker walks every PatchOperation in a DesignPatch and produces a
PatchSafetyReport (risk_level, requires_approval, warnings, errors,
capability_misses). It does NOT mutate the patch.
"""

from __future__ import annotations

import logging
from typing import Iterable, List

from server.planning.capability_registry import CapabilityRegistry, get_default_registry
from server.planning.design_patch import (
    ComponentPatch,
    DesignPatch,
    DirectCommandPatch,
    ObjectPatch,
    PatchSafetyReport,
    RiskLevel,
)

logger = logging.getLogger("UnrealMCP_Advanced")


_RISK_ORDER = {"safe": 0, "review": 1, "destructive": 2}


def _max_risk(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    if _RISK_ORDER[b] > _RISK_ORDER[a]:
        return b
    return a


class SafetyChecker:
    def __init__(self, registry: CapabilityRegistry = None) -> None:
        self.registry = registry or get_default_registry()

    def check(self, patch: DesignPatch) -> PatchSafetyReport:
        report = PatchSafetyReport()

        # operation count
        op_count = patch.operation_count()
        report.operation_count = op_count

        # 1. max_operations enforcement
        if op_count > patch.max_operations:
            report.errors.append(
                f"operation_count {op_count} exceeds max_operations {patch.max_operations}"
            )

        # 2. intent.risk_hint propagates upward
        if patch.intent.risk_hint:
            report.risk_level = _max_risk(report.risk_level, patch.intent.risk_hint)

        # 3. capability resolution per ComponentPatch / DirectCommandPatch
        for cp in patch.component_patches:
            self._check_component(cp, report)

        for dc in patch.direct_commands:
            self._check_direct(dc, report)

        # 4. ObjectPatch deletes are destructive
        for op in patch.object_patches:
            if op.action == "delete":
                report.risk_level = _max_risk(report.risk_level, "destructive")
                report.warnings.append(f"ObjectPatch delete on {op.mcp_id} is destructive")

        # 5. Promote risk_level using highest of declared + intent + delete checks
        report.risk_level = _max_risk(report.risk_level, patch.risk_level)

        # 6. requires_approval rules:
        #    - destructive => approval required
        #    - errors present => approval required (still cannot apply unless fixed)
        if report.risk_level == "destructive":
            report.requires_approval = True
        if report.errors:
            report.requires_approval = True

        return report

    # -------- per-operation helpers --------
    def _check_component(self, cp: ComponentPatch, report: PatchSafetyReport) -> None:
        if not cp.capability_id:
            return  # PatchCompiler may set one later via scene.components_upsert
        cap = self.registry.get(cp.capability_id)
        if cap is None:
            report.capability_misses.append(cp.capability_id)
            report.errors.append(
                f"unknown capability_id on ComponentPatch: {cp.capability_id}"
            )
            return
        if cap.risk != "safe":
            report.risk_level = _max_risk(report.risk_level, cap.risk)
        if cp.action == "delete" and cap.risk == "safe":
            # delete demotes to review at minimum
            report.risk_level = _max_risk(report.risk_level, "review")

    def _check_direct(self, dc: DirectCommandPatch, report: PatchSafetyReport) -> None:
        cap = self.registry.get(dc.capability_id)
        if cap is None:
            report.capability_misses.append(dc.capability_id)
            report.errors.append(
                f"unknown capability_id on DirectCommandPatch: {dc.capability_id}"
            )
            return
        if cap.risk != "safe":
            report.risk_level = _max_risk(report.risk_level, cap.risk)


def check_patch(patch: DesignPatch) -> PatchSafetyReport:
    """Convenience helper used by dialog_tools."""
    return SafetyChecker().check(patch)


def explain_plan_markdown(patch: DesignPatch) -> str:
    """Build a human-readable markdown summary of a DesignPatch."""
    lines: List[str] = [f"## Patch {patch.patch_id}",
                        f"- Scene: `{patch.scene_id}`",
                        f"- Intent: {patch.intent.raw_text}",
                        f"- Mood: {patch.intent.mood or '-'}",
                        f"- Risk: **{patch.risk_level}**",
                        f"- Operations: {patch.operation_count()}",
                        ""]
    if patch.summary:
        lines.append(f"> {patch.summary}\n")

    if patch.component_patches:
        lines.append("### Components")
        for cp in patch.component_patches:
            lines.append(
                f"- `{cp.action}` **{cp.component_type}** on `{cp.entity_id}` ({cp.capability_id or 'no-cap'})"
            )
        lines.append("")

    if patch.object_patches:
        lines.append("### Objects")
        for op in patch.object_patches:
            lines.append(f"- `{op.action}` actor `{op.mcp_id}` reason={op.reason or '-'}")
        lines.append("")

    if patch.asset_patches:
        lines.append("### Assets")
        for ap in patch.asset_patches:
            lines.append(f"- `{ap.action}` {ap.kind} `{ap.asset_id}`")
        lines.append("")

    if patch.direct_commands:
        lines.append("### Direct Commands")
        for dc in patch.direct_commands:
            lines.append(f"- {dc.capability_id} -> `{dc.command}` reason={dc.reason or '-'}")
        lines.append("")

    if patch.safety_report and patch.safety_report.warnings:
        lines.append("### Warnings")
        for w in patch.safety_report.warnings:
            lines.append(f"- {w}")
        lines.append("")
    if patch.warnings:
        lines.append("### Patch Warnings")
        for w in patch.warnings:
            lines.append(f"- {w}")
    return "\n".join(lines).rstrip() + "\n"

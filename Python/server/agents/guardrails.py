"""Guardrails — input, output, and tool-call validation for agent safety.

References:
- OpenAI Agents SDK Guardrails
- LlamaFirewall (Meta)
- SecAlign (Meta)

All guardrails are **opt-in** via AgentContext.constraints so existing tests
are unaffected.  Set ``context.constraints["guardrails"] = True`` to enable.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("agents.guardrails")

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class GuardrailViolation:
    """Single guardrail violation."""

    guardrail: str
    message: str
    severity: str  # "block" | "warn" | "review"
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "guardrail": self.guardrail,
            "message": self.message,
            "severity": self.severity,
            "context": self.context,
        }


@dataclass
class GuardrailResult:
    """Result of running one or more guardrails."""

    passed: bool = True
    violations: List[GuardrailViolation] = field(default_factory=list)
    risk_level: str = "safe"  # safe | review | destructive

    def merge(self, other: "GuardrailResult") -> "GuardrailResult":
        return GuardrailResult(
            passed=self.passed and other.passed,
            violations=self.violations + other.violations,
            risk_level=_max_risk(self.risk_level, other.risk_level),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "risk_level": self.risk_level,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _max_risk(a: str, b: str) -> str:
    order = ["safe", "review", "destructive"]
    return max(a, b, key=lambda x: order.index(x))


def _enabled(context: Optional[Dict[str, Any]]) -> bool:
    if context is None:
        return False
    guardrails = context.get("guardrails")
    if isinstance(guardrails, bool):
        return guardrails
    if isinstance(guardrails, dict):
        return guardrails.get("enabled", False)
    return False


# ---------------------------------------------------------------------------
# Input guardrail
# ---------------------------------------------------------------------------

# Patterns that suggest command injection or prompt injection attempts
_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore previous instructions", re.I),
    re.compile(r"disregard (all|your) instructions", re.I),
    re.compile(r"you are now .* mode", re.I),
    re.compile(r"DAN\b", re.I),
    re.compile(r"system prompt", re.I),
    re.compile(r"```\s*(?:system|python|bash|shell|cmd)", re.I),
]

# Dangerous operations that should trigger review
_DANGEROUS_INTENTS: Set[str] = {
    "delete all", "remove all", "drop all", "clear all",
    "nuke", "wipe everything", "destroy everything",
    "exec(", "eval(", "os.system", "subprocess",
    "import os", "import subprocess", "__import__",
}


class InputGuardrail:
    """Validate user intent before it reaches the agent system."""

    @classmethod
    def check(cls, intent_text: str, constraints: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        if not _enabled(constraints):
            return GuardrailResult()

        violations: List[GuardrailViolation] = []
        text_lower = intent_text.lower()

        # Injection detection
        for pat in _INJECTION_PATTERNS:
            if pat.search(intent_text):
                violations.append(
                    GuardrailViolation(
                        guardrail="input.injection",
                        message=f"Potential prompt injection detected: {pat.pattern[:40]}...",
                        severity="block",
                    )
                )

        # Dangerous intent detection
        for dangerous in _DANGEROUS_INTENTS:
            if dangerous in text_lower:
                violations.append(
                    GuardrailViolation(
                        guardrail="input.dangerous_intent",
                        message=f"Potentially dangerous intent keyword: '{dangerous}'",
                        severity="block" if "all" in dangerous else "review",
                    )
                )

        # Length check
        if len(intent_text) > 10000:
            violations.append(
                GuardrailViolation(
                    guardrail="input.length",
                    message=f"Intent too long: {len(intent_text)} chars (max 10000)",
                    severity="warn",
                )
            )

        passed = not any(v.severity == "block" for v in violations)
        risk = "safe"
        if any(v.severity == "block" for v in violations):
            risk = "destructive"
        elif any(v.severity == "review" for v in violations):
            risk = "review"

        return GuardrailResult(passed=passed, violations=violations, risk_level=risk)


# ---------------------------------------------------------------------------
# Tool guardrail
# ---------------------------------------------------------------------------

# Tools that require explicit approval
_RESTRICTED_TOOLS: Set[str] = set()

# Parameter validation rules: {tool_name: {param_name: (min, max)}}
_PARAM_BOUNDS: Dict[str, Dict[str, tuple]] = {
    "set_light_intensity": {"intensity": (0.0, 100000.0)},
    "set_light_attenuation_radius": {"radius": (0.0, 50000.0)},
    "landscape_flatten": {"brush_radius": (0.0, 10000.0)},
    "foliage_paint": {"radius": (0.0, 50000.0)},
}

# Maximum parameter string length (prevent injection via params)
_MAX_PARAM_STR_LEN = 1000


class ToolGuardrail:
    """Validate tool calls before execution."""

    @classmethod
    def check(
        cls,
        tool_name: str,
        params: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None,
    ) -> GuardrailResult:
        if not _enabled(constraints):
            return GuardrailResult()

        violations: List[GuardrailViolation] = []

        # Restricted tool check
        if tool_name in _RESTRICTED_TOOLS:
            violations.append(
                GuardrailViolation(
                    guardrail="tool.restricted",
                    message=f"Tool '{tool_name}' requires explicit approval",
                    severity="block",
                )
            )

        # Parameter bounds check
        bounds = _PARAM_BOUNDS.get(tool_name, {})
        for param_name, (min_val, max_val) in bounds.items():
            val = params.get(param_name)
            if val is not None:
                try:
                    fval = float(val)
                    if fval < min_val or fval > max_val:
                        violations.append(
                            GuardrailViolation(
                                guardrail="tool.param_bounds",
                                message=(
                                    f"Parameter '{param_name}' out of bounds "
                                    f"({min_val}..{max_val}): {fval}"
                                ),
                                severity="block",
                                context={"param": param_name, "value": fval, "bounds": (min_val, max_val)},
                            )
                        )
                except (TypeError, ValueError):
                    pass

        # String param length check (anti-injection)
        for key, val in params.items():
            if isinstance(val, str) and len(val) > _MAX_PARAM_STR_LEN:
                violations.append(
                    GuardrailViolation(
                        guardrail="tool.param_length",
                        message=f"Parameter '{key}' too long: {len(val)} chars",
                        severity="block",
                    )
                )

        passed = not any(v.severity == "block" for v in violations)
        return GuardrailResult(
            passed=passed,
            violations=violations,
            risk_level="destructive" if not passed else "safe",
        )


# ---------------------------------------------------------------------------
# Output guardrail
# ---------------------------------------------------------------------------

# Thresholds for output validation
_MAX_ERRORS_PER_BATCH = 3
_MAX_WARNINGS_PER_BATCH = 10


class OutputGuardrail:
    """Validate agent output before returning to user."""

    @classmethod
    def check(
        cls,
        result: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None,
    ) -> GuardrailResult:
        if not _enabled(constraints):
            return GuardrailResult()

        violations: List[GuardrailViolation] = []

        # Check for destructive operations in result
        data = result.get("data", {})
        if isinstance(data, dict):
            # Detect bulk deletions
            deleted = data.get("deleted_count") or data.get("deleted")
            if isinstance(deleted, int) and deleted > 10:
                violations.append(
                    GuardrailViolation(
                        guardrail="output.bulk_deletion",
                        message=f"Large deletion detected: {deleted} items",
                        severity="review",
                    )
                )

        # Error rate check
        errors = result.get("errors", [])
        if isinstance(errors, list) and len(errors) > _MAX_ERRORS_PER_BATCH:
            violations.append(
                GuardrailViolation(
                    guardrail="output.error_rate",
                    message=f"Too many errors: {len(errors)} (max {_MAX_ERRORS_PER_BATCH})",
                    severity="review",
                )
            )

        # Warning rate check
        warnings = result.get("warnings", [])
        if isinstance(warnings, list) and len(warnings) > _MAX_WARNINGS_PER_BATCH:
            violations.append(
                GuardrailViolation(
                    guardrail="output.warning_rate",
                    message=f"Too many warnings: {len(warnings)} (max {_MAX_WARNINGS_PER_BATCH})",
                    severity="warn",
                )
            )

        passed = not any(v.severity == "block" for v in violations)
        risk = "destructive" if any(v.severity == "block" for v in violations) else "review" if violations else "safe"

        return GuardrailResult(passed=passed, violations=violations, risk_level=risk)


class QualityGateGuardrail:
    """Convert quality-gate blockers into guardrail-style diagnostics."""

    @classmethod
    def check(cls, result: Dict[str, Any], constraints: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        if not _enabled(constraints):
            return GuardrailResult()
        data = result.get("data", result)
        gate = data.get("quality_gate") if isinstance(data, dict) else None
        if not isinstance(gate, dict) or gate.get("passed", True):
            return GuardrailResult()
        violations = [
            GuardrailViolation(
                guardrail="quality.gate",
                message=f"Quality gate blocker: {blocker}",
                severity="review",
                context={"blocker": blocker},
            )
            for blocker in gate.get("blockers", [])
        ]
        return GuardrailResult(passed=True, violations=violations, risk_level="review" if violations else "safe")


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------


class Guardrails:
    """Unified guardrails runner."""

    @classmethod
    def check_input(cls, intent_text: str, constraints: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        return InputGuardrail.check(intent_text, constraints)

    @classmethod
    def check_tool(cls, tool_name: str, params: Dict[str, Any], constraints: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        return ToolGuardrail.check(tool_name, params, constraints)

    @classmethod
    def check_output(cls, result: Dict[str, Any], constraints: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        return OutputGuardrail.check(result, constraints).merge(QualityGateGuardrail.check(result, constraints))

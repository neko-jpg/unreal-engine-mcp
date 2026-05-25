"""VLM rubric definitions for React-for-UE v3.0.

Providers (OpenAI, Anthropic) have been removed. The MCP server returns
images as MCP ImageContent and lets the calling agent (which is itself a
multimodal LLM) evaluate them directly.  ``VlmRubric`` and ``VlmResult``
are kept so that rubric definitions can still be shared between the server
and agent-side evaluation code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class VlmRubric:
    rubric_id: str
    goal: str
    criteria: List[str] = field(default_factory=list)
    measurable_hints: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VlmResult:
    rubric_id: str
    provider: str
    model: str
    score: float = 0.0  # 0..1
    notes: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NullProvider:
    """No-op provider kept for backward compatibility in tests."""
    name = "null"
    model = "n/a"

    def analyze(self, image_path: str, rubric: VlmRubric) -> VlmResult:
        return VlmResult(
            rubric_id=rubric.rubric_id,
            provider=self.name,
            model=self.model,
            score=0.0,
            notes="vlm disabled (NullProvider) — agent evaluates images directly",
        )

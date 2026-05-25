"""BaseDomainExpert - common interface for all experts.

Experts must not hard-code UE command names. They use the CapabilityRegistry
to resolve capability ids into Capability objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from server.intent.scene_context import SceneContextPack
from server.intent.intent_types import Intent
from server.planning.capability_registry import CapabilityRegistry, get_default_registry


class BaseDomainExpert(ABC):
    """All experts inherit from this base."""

    domain: str = ""

    def __init__(self, registry: Optional[CapabilityRegistry] = None) -> None:
        self.registry = registry or get_default_registry()

    def applies_to(self, intent: Intent) -> bool:
        """Return True if this expert should run for the given intent."""
        return self.domain in intent.domains

    @abstractmethod
    def propose(
        self,
        intent: Intent,
        context: SceneContextPack,
        profile: Optional["MoodProfile"],  # noqa: F821 (forward decl)
    ) -> List[Any]:
        """Return a list of ComponentPatch / DirectCommandPatch / AssetPatch."""
        ...

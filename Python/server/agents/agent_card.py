"""A2A Protocol — Agent Cards for capability advertisement.

References:
- Google A2A Protocol (April 2025)
- https://github.com/google/A2A

Agent Cards let agents advertise their capabilities so orchestrators
can make intelligent routing decisions without hard-coding agent names.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentCard:
    """A2A-compliant agent capability advertisement.

    This is a simplified implementation of the A2A Agent Card spec
    adapted for the Unreal MCP agent system.
    """

    name: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    input_modes: List[str] = field(default_factory=lambda: ["text"])
    output_modes: List[str] = field(default_factory=lambda: ["scene_delta", "validation_report"])
    version: str = "1.0"
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "domains": self.domains,
            "input_modes": self.input_modes,
            "output_modes": self.output_modes,
            "version": self.version,
            "url": self.url,
        }

    @classmethod
    def from_agent(cls, agent: Any) -> "AgentCard":
        """Generate an AgentCard from a BaseAgent instance."""
        return cls(
            name=getattr(agent, "name", "unknown"),
            description=getattr(agent, "description", ""),
            capabilities=list(getattr(agent, "capabilities", [])),
            domains=list(getattr(agent, "domains", [])),
        )


class AgentCardDirectory:
    """Collects and serves Agent Cards for all registered agents."""

    def __init__(self) -> None:
        self._cards: Dict[str, AgentCard] = {}

    def register(self, card: AgentCard) -> None:
        self._cards[card.name] = card

    def get(self, name: str) -> Optional[AgentCard]:
        return self._cards.get(name)

    def list_all(self) -> List[AgentCard]:
        return list(self._cards.values())

    def find_by_capability(self, capability_id: str) -> List[AgentCard]:
        """Find all agents that advertise a given capability."""
        return [c for c in self._cards.values() if capability_id in c.capabilities]

    def find_by_domain(self, domain: str) -> List[AgentCard]:
        """Find all agents that handle a given domain."""
        return [c for c in self._cards.values() if domain in c.domains]

    def to_json(self) -> Dict[str, Any]:
        return {
            "agents": [c.to_dict() for c in self._cards.values()],
            "count": len(self._cards),
        }


def build_directory_from_orchestrator(orchestrator: Any) -> AgentCardDirectory:
    """Build an AgentCardDirectory from a MasterOrchestrator instance."""
    directory = AgentCardDirectory()
    for name, agent in getattr(orchestrator, "sub_agents", {}).items():
        directory.register(AgentCard.from_agent(agent))
    return directory

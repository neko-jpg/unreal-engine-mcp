"""Architecture Domain Agent - Expert in building and structure creation."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.architecture_domain")


class ArchitectureDomainAgent(BaseAgent):
    """Domain agent for architectural structures.
    
    Capabilities:
    - Houses, mansions, castles
    - Towers, bridges, aqueducts
    - Walls, pyramids, mazes
    - Towns and cities
    """

    name = "architecture_domain"
    description = "Expert in architectural structure creation"
    capabilities = [
        "architecture.house",
        "architecture.mansion",
        "architecture.castle",
        "architecture.tower",
        "architecture.bridge",
        "architecture.wall",
        "architecture.pyramid",
        "architecture.maze",
        "architecture.town",
        "architecture.aqueduct",
    ]
    domains = ["architecture", "world_building"]

    def __init__(self, tool_registry: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(tool_registry)
        # Register worker agents for post-construction coordination
        from server.agents.worker_agents.nav_worker import NavWorkerAgent
        from server.agents.worker_agents.pcg_worker import PCGWorkerAgent
        from server.agents.worker_agents.validation_worker import ValidationWorkerAgent

        self.register_sub_agent(NavWorkerAgent(tool_registry))
        self.register_sub_agent(PCGWorkerAgent(tool_registry))
        self.register_sub_agent(ValidationWorkerAgent(tool_registry))

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute architecture operations."""
        self.logger.info(f"ArchitectureDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        # Structure type detection
        if any(kw in text_lower for kw in ["house", "home", "building"]):
            return await self._create_structure("house", context)
        elif any(kw in text_lower for kw in ["mansion", "villa", "estate"]):
            return await self._create_structure("mansion", context)
        elif any(kw in text_lower for kw in ["castle", "fortress", "fort", "palace"]):
            return await self._create_structure("castle", context)
        elif any(kw in text_lower for kw in ["tower", "spire", "obelisk"]):
            return await self._create_structure("tower", context)
        elif any(kw in text_lower for kw in ["bridge", "crossing"]):
            return await self._create_structure("bridge", context)
        elif any(kw in text_lower for kw in ["wall", "fence", "barrier"]):
            return await self._create_structure("wall", context)
        elif any(kw in text_lower for kw in ["pyramid", "ziggurat"]):
            return await self._create_structure("pyramid", context)
        elif any(kw in text_lower for kw in ["maze", "labyrinth"]):
            return await self._create_structure("maze", context)
        elif any(kw in text_lower for kw in ["town", "city", "village", "settlement"]):
            return await self._create_structure("town", context)
        elif any(kw in text_lower for kw in ["aqueduct", "channel", "canal"]):
            return await self._create_structure("aqueduct", context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown architecture type in intent: {intent}",
            )

    async def _create_structure(self, structure_type: str, context: AgentContext) -> AgentResult:
        """Create a specific structure type with post-construction coordination."""
        tool_map = {
            "house": "construct_house",
            "mansion": "construct_mansion",
            "castle": "create_castle_fortress",
            "tower": "create_tower",
            "bridge": "create_suspension_bridge",
            "wall": "create_wall",
            "pyramid": "create_pyramid",
            "maze": "create_maze",
            "town": "create_town",
            "aqueduct": "create_aqueduct",
        }

        tool_name = tool_map.get(structure_type)
        if not tool_name:
            return AgentResult(success=False, error=f"Unknown structure type: {structure_type}")

        result = await self.call_tool_async(tool_name)

        if isinstance(result, dict) and result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", f"{structure_type} creation failed"),
                data={"raw_result": result},
            )

        steps = []
        steps.append({"step": "create_structure", "result": result})

        # Post-construction: update navmesh for walkable structures
        if structure_type in {"house", "mansion", "castle", "town"}:
            nav_result = await self.delegate(
                "nav_worker",
                f"update navmesh after {structure_type} construction",
                context,
            )
            steps.append({"step": "navmesh_update", "result": nav_result.to_dict()})

        # Post-construction: scatter PCG details around structure
        if structure_type in {"castle", "town", "mansion"}:
            pcg_result = await self.delegate(
                "pcg_worker",
                f"scatter details around {structure_type}",
                context,
            )
            steps.append({"step": "pcg_details", "result": pcg_result.to_dict()})

        # Post-construction: validate structure
        val_result = await self.delegate(
            "validation_worker",
            f"validate {structure_type} construction",
            context,
        )
        steps.append({"step": "validation", "result": val_result.to_dict()})

        failures = [s for s in steps if not s["result"].get("success", True)]

        return AgentResult(
            success=len(failures) < len(steps),
            data={
                "structure_type": structure_type,
                "result": result if isinstance(result, dict) else {"created": True},
                "post_construction_steps": steps,
            },
            warnings=[f"{s['step']}: {s['result'].get('error')}" for s in failures],
        )

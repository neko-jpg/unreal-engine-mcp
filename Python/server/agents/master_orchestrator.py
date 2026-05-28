"""Master Orchestrator - Top-level agent that routes requests to domain experts."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from server.agents.agent_card import AgentCardDirectory, build_directory_from_orchestrator
from server.agents.base_agent import AgentContext, AgentResult, BaseAgent, ToolRegistry
from server.agents.guardrails import Guardrails
from server.agents.planner import TaskPlanner
from server.agents.tracing import is_tracing_enabled, get_tracer
from server.intent.intent_resolver import IntentResolver
from server.intent.intent_types import Intent

logger = logging.getLogger("agents.master_orchestrator")


class MasterOrchestrator(BaseAgent):
    """Master orchestrator that routes all user requests to appropriate domain agents.
    
    This is the entry point for the entire agent system. It:
    1. Parses user intent
    2. Determines which domain(s) are involved
    3. Delegates to domain agents
    4. Coordinates multi-domain workflows
    5. Returns consolidated results
    """

    name = "master_orchestrator"
    description = "Top-level orchestrator for all Unreal MCP operations"
    capabilities = [
        "orchestrate",
        "route",
        "coordinate",
        "multi_domain",
    ]
    domains = [
        "cave",
        "architecture",
        "lighting",
        "material",
        "atmosphere",
        "landscape",
        "foliage",
        "npc",
        "cinematic",
        "ui",
        "physics",
        "audio",
        "vfx",
        "animation",
        "gameplay",
        "networking",
        "validation",
        "import_export",
        "asset_management",
        "level_management",
        "project_editor",
    ]

    def __init__(self, tool_registry: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(tool_registry)
        self.intent_resolver = IntentResolver()
        self._domain_agent_map: Dict[str, str] = {
            "cave": "cave_domain",
            "architecture": "architecture_domain",
            "lighting": "lighting_domain",
            "material": "material_domain",
            "atmosphere": "atmosphere_domain",
            "landscape": "landscape_domain",
            "foliage": "foliage_domain",
            "npc": "npc_domain",
            "cinematic": "cinematic_domain",
            "ui": "ui_domain",
            "physics": "physics_domain",
            "audio": "audio_domain",
            "vfx": "vfx_domain",
            "animation": "animation_domain",
            "gameplay": "gameplay_domain",
            "networking": "networking_domain",
            "validation": "validation_domain",
            "import_export": "import_export_domain",
            "asset_management": "asset_management_domain",
            "level_management": "level_management_domain",
            "project_editor": "project_editor_domain",
            "post_process": "postprocess_domain",
            "camera": "cinematic_domain",
            "procedural": "procedural_domain",
            "mesh_editing": "mesh_domain",
            "navigation": "npc_domain",
        }
        self.mode = "react"  # "react" | "plan_and_execute"
        self.planner = TaskPlanner()

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute user intent by routing to appropriate domain agents.
        
        Args:
            intent: Natural language user request
            context: Execution context
            
        Returns:
            Consolidated AgentResult from all involved domains
        """
        self.logger.info(f"Orchestrating intent: {intent[:80]}...")

        # Tracing
        span = None
        if is_tracing_enabled(context.constraints):
            span = self._tracer.start_span(
                "agent.workflow.orchestrate",
                self.name,
            )
            self._current_span = span

        # Input guardrails
        gr = Guardrails.check_input(intent, context.constraints)
        if not gr.passed:
            violations = "; ".join(f"{v.guardrail}: {v.message}" for v in gr.violations)
            self.logger.warning(f"Input guardrail blocked intent: {violations}")
            if span is not None:
                self._tracer.finish_span(span)
                self._current_span = None
            return AgentResult(
                success=False,
                error=f"Input guardrail blocked: {violations}",
                data={"guardrail_violations": [v.to_dict() for v in gr.violations]},
            )

        # Resolve intent
        resolution = self.intent_resolver.resolve(
            intent,
            scene_id=context.scene_id,
            target=context.target,
            style_profile=context.style_profile,
            constraints=context.constraints,
        )
        
        resolved_intent = resolution.intent
        self.logger.info(
            f"Resolved: action={resolved_intent.action}, domains={resolved_intent.domains}, "
            f"mood={resolved_intent.mood}"
        )

        # Determine which domain agents to invoke
        domain_agents = self._select_domain_agents(resolved_intent)
        
        if not domain_agents:
            return AgentResult(
                success=False,
                error=f"No domain agent found for intent: {intent}",
                data={"resolved_intent": resolved_intent.__dict__},
            )

        # Plan-and-Execute mode for multi-domain tasks
        if self.mode == "plan_and_execute" and len(domain_agents) > 1:
            self.logger.info(
                f"Using plan-and-execute for {len(domain_agents)} domains"
            )
            plan = self.planner.create_plan(
                resolved_intent.raw_text,
                domain_agents,
            )
            return await self.planner.execute_plan(plan, context, self)

        # Execute domain agents (ReAct-style sequential)
        results: List[AgentResult] = []

        try:
            for domain, agent_name in domain_agents:
                self.logger.info(f"Invoking domain agent: {agent_name} for domain: {domain}")

                # Create domain-specific intent
                domain_intent = self._create_domain_intent(resolved_intent, domain)

                result = await self.delegate(agent_name, domain_intent, context)
                results.append(result)

                # Store domain result in context for cross-domain coordination
                context.metadata[f"{domain}_result"] = result.to_dict()

            # If multiple domains and all succeeded, run coordination pass
            if len(results) > 1 and all(r.success for r in results):
                coord_result = await self._coordinate_domains(resolved_intent, context, results)
                if coord_result:
                    results.append(coord_result)

            merged = self._merge_results(results)
            merged.data["resolved_intent"] = {
                "action": resolved_intent.action,
                "domains": resolved_intent.domains,
                "mood": resolved_intent.mood,
                "target_selector": resolved_intent.target_selector,
            }

            return merged
        finally:
            if span is not None:
                self._tracer.finish_span(span)
                self._current_span = None

    def _select_domain_agents(self, intent: Intent) -> List[tuple]:
        """Select which domain agents to invoke based on intent.
        
        Returns:
            List of (domain, agent_name) tuples
        """
        selected: List[tuple] = []
        seen_agents: set = set()

        # Primary domains from intent
        for domain in intent.domains:
            agent_name = self._domain_agent_map.get(domain)
            if agent_name and agent_name not in seen_agents:
                selected.append((domain, agent_name))
                seen_agents.add(agent_name)

        # If no domains matched, try keyword matching
        if not selected:
            text_lower = intent.raw_text.lower()
            for domain, agent_name in self._domain_agent_map.items():
                if agent_name in seen_agents:
                    continue
                # Simple keyword check
                keywords = self._get_domain_keywords(domain)
                if any(kw in text_lower for kw in keywords):
                    selected.append((domain, agent_name))
                    seen_agents.add(agent_name)

        return selected

    def _get_domain_keywords(self, domain: str) -> List[str]:
        """Get keywords for a domain."""
        keywords = {
            "cave": ["cave", "cavern", "dungeon", "洞窟", "洞穴", "鍾乳洞", "ダンジョン"],
            "architecture": ["house", "building", "castle", "mansion", "tower", "bridge", "arch", "wall", "pyramid", "maze", "town", "aqueduct"],
            "lighting": ["light", "torch", "lamp", "bright", "dark", "shadow", "illumination"],
            "material": ["material", "stone", "metal", "wood", "wet", "rough", "texture"],
            "atmosphere": ["fog", "mist", "haze", "sky", "weather", "cloud", "volumetric"],
            "landscape": ["landscape", "terrain", "heightmap", "mountain", "hill", "ground"],
            "foliage": ["foliage", "tree", "grass", "plant", "vegetation", "forest"],
            "npc": ["npc", "ai", "enemy", "character", "pawn", "behavior", "navmesh", "patrol"],
            "cinematic": ["camera", "sequencer", "cutscene", "movie", "render", "shot", "cinematic"],
            "ui": ["ui", "widget", "menu", "hud", "button", "text", "interface"],
            "physics": ["physics", "collision", "ragdoll", "destruction", "chaos", "constraint"],
            "audio": ["sound", "audio", "music", "ambient", "drip", "footstep"],
            "vfx": ["particle", "niagara", "dust", "smoke", "effect", "vfx"],
            "animation": ["animation", "skeletal", "rig", "blendspace", "montage", "morph"],
            "gameplay": ["gameplay", "gamemode", "ability", "savegame", "checkpoint"],
            "networking": ["network", "multiplayer", "replicate", "rpc", "session", "server"],
            "validation": ["validate", "test", "check", "audit", "verify", "performance"],
            "import_export": ["import", "export", "fbx", "texture", "mesh", "gltf"],
            "asset_management": ["asset", "folder", "content", "browser", "redirector"],
            "level_management": ["level", "map", "sublevel", "stream", "world partition"],
            "project_editor": ["project", "editor", "settings", "plugin", "build", "package"],
            "procedural": ["procedural", "sdf", "wfc", "generate", "marching cubes"],
            "mesh_editing": ["remesh", "uv", "collision", "nanite", "simplify", "bake"],
            "navigation": ["navmesh", "nav", "walkable", "path", "waypoint"],
        }
        return keywords.get(domain, [domain])

    def _create_domain_intent(self, intent: Intent, domain: str) -> str:
        """Create a domain-specific intent string.
        
        This preserves the original intent but makes it more specific
        for the domain agent.
        """
        # For now, pass the original intent - domain agents will parse themselves
        # In the future, we could add domain-specific prefixes
        return intent.raw_text

    async def _coordinate_domains(
        self,
        intent: Intent,
        context: AgentContext,
        results: List[AgentResult],
    ) -> Optional[AgentResult]:
        """Coordinate between multiple domain results.

        This is called when multiple domains succeed and need
        cross-domain synchronization (e.g., lighting after geometry changes).
        """
        domains = set(intent.domains)
        coord_actions: List[str] = []
        coord_data: Dict[str, Any] = {}
        coord_warnings: List[str] = []

        # Cave + Lighting coordination: ensure cave has appropriate lighting
        if "cave" in domains and "lighting" in domains:
            self.logger.info("Coordinating cave-lighting cross-domain pass")
            coord_actions.append("cave_lighting")
            # Trigger dark ambient lighting for cave if not already present
            try:
                light_result = await self.call_tool_async(
                    "set_light_intensity",
                    actor_name="Cave_AmbientLight",
                    intensity=500.0,
                )
                coord_data["cave_lighting"] = light_result
            except Exception as exc:  # noqa: BLE001
                coord_warnings.append(f"cave lighting coordination failed: {exc}")

        # Architecture + Landscape coordination: flatten terrain under buildings
        if "architecture" in domains and "landscape" in domains:
            self.logger.info("Coordinating architecture-landscape cross-domain pass")
            coord_actions.append("architecture_landscape")
            try:
                flatten_result = await self.call_tool_async(
                    "landscape_flatten",
                    actor_name="Landscape",
                    brush_radius=500.0,
                    target_height=0.0,
                )
                coord_data["architecture_landscape"] = flatten_result
            except Exception as exc:  # noqa: BLE001
                coord_warnings.append(f"architecture-landscape coordination failed: {exc}")

        # Lighting + Atmosphere coordination: sync fog with light temperature
        if "lighting" in domains and "atmosphere" in domains:
            self.logger.info("Coordinating lighting-atmosphere cross-domain pass")
            coord_actions.append("lighting_atmosphere")
            try:
                fog_result = await self.call_tool_async(
                    "set_height_fog_properties",
                    actor_name="ExponentialHeightFog",
                    fog_density=0.05,
                    start_distance=500.0,
                )
                coord_data["lighting_atmosphere"] = fog_result
            except Exception as exc:  # noqa: BLE001
                coord_warnings.append(f"lighting-atmosphere coordination failed: {exc}")

        # Landscape + Foliage coordination: paint foliage after terrain changes
        if "landscape" in domains and "foliage" in domains:
            self.logger.info("Coordinating landscape-foliage cross-domain pass")
            coord_actions.append("landscape_foliage")
            try:
                foliage_result = await self.call_tool_async(
                    "foliage_paint",
                    foliage_type_path="/Game/Foliage/Grass_Default",
                    location_xyz=[0.0, 0.0, 0.0],
                    radius=2000.0,
                )
                coord_data["landscape_foliage"] = foliage_result
            except Exception as exc:  # noqa: BLE001
                coord_warnings.append(f"landscape-foliage coordination failed: {exc}")

        # Validation coordination: run validation after multi-domain changes
        if "validation" in domains:
            self.logger.info("Coordinating validation cross-domain pass")
            coord_actions.append("validation")
            try:
                val_result = await self.call_tool_async(
                    "run_collision_validation",
                    scope="Level",
                )
                coord_data["validation"] = val_result
            except Exception as exc:  # noqa: BLE001
                coord_warnings.append(f"validation coordination failed: {exc}")

        if not coord_actions:
            return None

        return AgentResult(
            success=True,
            data={
                "coordination_actions": coord_actions,
                "coordination_results": coord_data,
            },
            warnings=coord_warnings,
        )

    def register_all_domain_agents(self, agents: List[BaseAgent]) -> None:
        """Register all domain agents at once."""
        for agent in agents:
            self.register_sub_agent(agent)
            logger.info(f"Registered domain agent: {agent.name}")

    def get_agent_cards(self) -> AgentCardDirectory:
        """Build an AgentCardDirectory from all registered sub-agents."""
        return build_directory_from_orchestrator(self)


# Singleton instance
_master_orchestrator_instance: Optional[MasterOrchestrator] = None


def get_master_orchestrator(tool_registry: Optional[Dict[str, Any]] = None) -> MasterOrchestrator:
    """Get or create the master orchestrator singleton."""
    global _master_orchestrator_instance
    if _master_orchestrator_instance is None:
        _master_orchestrator_instance = MasterOrchestrator(tool_registry)
    elif tool_registry is not None:
        # Update existing instance with new tool registry (re-initialization)
        _master_orchestrator_instance.tool_registry = tool_registry
    return _master_orchestrator_instance


def reset_master_orchestrator() -> None:
    """Reset the master orchestrator."""
    global _master_orchestrator_instance
    _master_orchestrator_instance = None

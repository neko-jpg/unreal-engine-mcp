"""Agent system initialization and orchestration.

This module provides the entry point for the entire AI agent ecosystem.
It:
1. Registers all MCP tools with the tool registry
2. Creates and configures all domain agents
3. Initializes the master orchestrator
4. Provides a simple API for executing intents
"""

from __future__ import annotations

import asyncio
import importlib
import logging
from typing import Any, Dict, List, Optional

from server.agents.agent_card import AgentCard, AgentCardDirectory
from server.agents.base_agent import AgentContext, AgentResult, ToolRegistry, get_tool_registry
from server.agents.memory import AgentMemory
from server.agents.planner import TaskPlanner
from server.agents.domain_agents import (
    AnimationDomainAgent,
    ArchitectureDomainAgent,
    AssetManagementDomainAgent,
    AudioDomainAgent,
    CaveDomainAgent,
    CinematicDomainAgent,
    FoliageDomainAgent,
    GameplayDomainAgent,
    ImportExportDomainAgent,
    LandscapeDomainAgent,
    LevelManagementDomainAgent,
    LightingDomainAgent,
    MaterialDomainAgent,
    NetworkingDomainAgent,
    NpcDomainAgent,
    PhysicsDomainAgent,
    PostProcessDomainAgent,
    ProjectEditorDomainAgent,
    UiDomainAgent,
    ValidationDomainAgent,
    VfxDomainAgent,
)
from server.agents.master_orchestrator import MasterOrchestrator, get_master_orchestrator

logger = logging.getLogger("agents")


def _try_get_tool(module_name: str, func_name: str) -> Optional[Any]:
    """Try to import a tool function from a module."""
    try:
        module = importlib.import_module(f"server.{module_name}")
        return getattr(module, func_name, None)
    except Exception:
        return None


def register_all_tools(registry: ToolRegistry) -> None:
    """Register all available MCP tools with the tool registry.
    
    This binds the actual MCP tool functions to the registry so agents can call them.
    Tools are discovered dynamically from server modules.
    """
    # Cave tools
    cave_tools = [
        ("scene_cave_tools", "scene_cave_audit"),
        ("scene_cave_tools", "scene_create_cave_sdf"),
        ("scene_cave_tools", "scene_apply_cave_pcg"),
        ("scene_cave_tools", "scene_apply_cave_mood"),
        ("scene_cave_tools", "scene_validate_cave"),
        ("scene_cave_tools", "scene_refine_cave_geometry"),
        ("scene_cave_tools", "scene_cave_generate_or_refine"),
    ]
    
    # Procedural tools
    proc_tools = [
        ("scene_procedural_tools", "scene_create_sdf_mesh"),
        ("scene_procedural_tools", "scene_create_wfc_grid"),
        ("scene_procedural_tools", "scene_wfc_to_semantic_layout"),
        ("scene_procedural_tools", "scene_create_lsystem_spline"),
        ("scene_procedural_tools", "scene_create_superformula_mesh"),
        ("scene_procedural_tools", "scene_upsert_procedural_mesh"),
    ]
    
    # Validation tools
    val_tools = [
        ("testing_validation_tools", "run_collision_validation"),
        ("testing_validation_tools", "run_navigation_validation"),
        ("testing_validation_tools", "run_performance_budget_validation"),
        ("testing_validation_tools", "run_gameplay_screenshot_test"),
    ]
    
    # Scene tools
    scene_tools = [
        ("actor_tools", "spawn_actor"),
        ("scene_nav_ai_tools", "scene_create_navmesh_volume"),
        ("scene_nav_ai_tools", "scene_create_patrol_route"),
        ("scene_nav_ai_tools", "scene_set_ai_behavior"),
        ("dialog_tools", "scene_preview"),
    ]
    
    # Domain-specific tools
    domain_tools = [
        ("lighting_tools", "set_light_intensity", ["lighting"]),
        ("lighting_tools", "set_light_color", ["lighting"]),
        ("lighting_tools", "set_light_temperature", ["lighting"]),
        ("lighting_tools", "set_height_fog_properties", ["atmosphere"]),
        ("lighting_tools", "set_volumetric_fog", ["atmosphere"]),
        ("audio_tools", "spawn_ambient_sound", ["audio"]),
        ("niagara_tools", "add_niagara_component", ["vfx"]),
        ("niagara_tools", "set_niagara_user_parameter", ["vfx"]),
        ("niagara_tools", "set_niagara_color", ["vfx"]),
        ("pcg_tools", "create_pcg_graph", ["pcg"]),
        ("pcg_tools", "configure_pcg_surface_sampler", ["pcg"]),
        ("pcg_tools", "configure_pcg_static_mesh_spawner", ["pcg"]),
        ("pcg_tools", "add_pcg_component", ["pcg"]),
        ("pcg_tools", "execute_pcg_graph", ["pcg"]),
        ("mesh_editing_tools", "asset_mesh_editing_tool", ["mesh_editing"]),
        ("rendering_tools", "spawn_post_process_volume", ["post_process"]),
        ("rendering_tools", "set_post_process_volume", ["post_process"]),
        ("foliage_tools", "foliage_paint", ["foliage"]),
        ("foliage_tools", "create_procedural_foliage_spawner", ["foliage"]),
        ("foliage_tools", "create_foliage_type", ["foliage"]),
        ("landscape_tools", "create_landscape", ["landscape"]),
        ("landscape_tools", "landscape_flatten", ["landscape"]),
        ("landscape_tools", "landscape_sculpt", ["landscape"]),
        ("world_building_tools", "construct_house", ["architecture"]),
        ("world_building_tools", "construct_mansion", ["architecture"]),
        ("world_building_tools", "create_castle_fortress", ["architecture"]),
        ("world_building_tools", "create_tower", ["architecture"]),
        ("world_building_tools", "create_suspension_bridge", ["architecture"]),
        ("world_building_tools", "create_wall", ["architecture"]),
        ("world_building_tools", "create_pyramid", ["architecture"]),
        ("world_building_tools", "create_maze", ["architecture"]),
        ("world_building_tools", "create_town", ["architecture"]),
        ("world_building_tools", "create_aqueduct", ["architecture"]),
        ("gameplay_framework_tools", "create_gamemode_blueprint", ["gameplay"]),
        ("gameplay_framework_tools", "create_character", ["gameplay"]),
        ("gas_tools", "grant_ability", ["gameplay"]),
        ("gameplay_framework_tools", "save_game_to_slot", ["gameplay"]),
    ]
    
    # Register cave tools
    for module, func in cave_tools:
        tool = _try_get_tool(module, func)
        if tool:
            registry.register(func, tool, ["cave"])
    
    # Register procedural tools
    for module, func in proc_tools:
        tool = _try_get_tool(module, func)
        if tool:
            registry.register(func, tool, ["procedural"])
    
    # Register validation tools
    for module, func in val_tools:
        tool = _try_get_tool(module, func)
        if tool:
            registry.register(func, tool, ["validation"])
    
    # Register scene tools
    for module, func in scene_tools:
        tool = _try_get_tool(module, func)
        if tool:
            registry.register(func, tool, ["scene"])
    
    # Register domain tools
    for module, func, domains in domain_tools:
        tool = _try_get_tool(module, func)
        if tool:
            registry.register(func, tool, domains)
    
    logger.info(f"Registered {len(registry.list_all())} tools")


def create_all_domain_agents(tool_registry: Dict[str, Any]) -> List[Any]:
    """Create all domain agent instances.
    
    Returns:
        List of initialized domain agents
    """
    agents = [
        CaveDomainAgent(tool_registry),
        ArchitectureDomainAgent(tool_registry),
        LightingDomainAgent(tool_registry),
        MaterialDomainAgent(tool_registry),
        LandscapeDomainAgent(tool_registry),
        FoliageDomainAgent(tool_registry),
        NpcDomainAgent(tool_registry),
        CinematicDomainAgent(tool_registry),
        UiDomainAgent(tool_registry),
        PhysicsDomainAgent(tool_registry),
        AudioDomainAgent(tool_registry),
        VfxDomainAgent(tool_registry),
        AnimationDomainAgent(tool_registry),
        GameplayDomainAgent(tool_registry),
        NetworkingDomainAgent(tool_registry),
        ValidationDomainAgent(tool_registry),
        ImportExportDomainAgent(tool_registry),
        AssetManagementDomainAgent(tool_registry),
        LevelManagementDomainAgent(tool_registry),
        ProjectEditorDomainAgent(tool_registry),
        PostProcessDomainAgent(tool_registry),
    ]
    
    return agents


def initialize_agent_system() -> MasterOrchestrator:
    """Initialize the complete agent system.
    
    This is the main entry point for setting up the agent ecosystem.
    It:
    1. Creates the tool registry
    2. Registers all MCP tools
    3. Creates all domain agents
    4. Initializes the master orchestrator
    5. Registers all domain agents with the orchestrator
    
    Returns:
        Configured MasterOrchestrator instance
    """
    logger.info("Initializing agent system...")
    
    # Create tool registry
    registry = get_tool_registry()
    register_all_tools(registry)
    
    # Create tool dict for agents
    tool_dict = registry.create_dict()
    
    # Get master orchestrator
    orchestrator = get_master_orchestrator(tool_dict)
    
    # Create and register all domain agents
    domain_agents = create_all_domain_agents(tool_dict)
    orchestrator.register_all_domain_agents(domain_agents)
    
    logger.info(
        f"Agent system initialized with {len(domain_agents)} domain agents "
        f"and {len(tool_dict)} tools"
    )
    
    return orchestrator


async def execute_intent(
    intent: str,
    scene_id: str = "main",
    target: Optional[str] = None,
    style_profile: Optional[str] = None,
    constraints: Optional[Dict[str, Any]] = None,
) -> AgentResult:
    """Execute a user intent through the agent system.
    
    This is the main API for running intents through the agent ecosystem.
    
    Args:
        intent: Natural language user request
        scene_id: Scene ID to operate on
        target: Optional target selector
        style_profile: Optional style/mood profile
        constraints: Optional execution constraints
        
    Returns:
        AgentResult with operation results
    """
    orchestrator = get_master_orchestrator()
    
    # Initialize if not already done
    if not orchestrator.sub_agents:
        orchestrator = initialize_agent_system()
    
    context = AgentContext(
        scene_id=scene_id,
        user_intent=intent,
        target=target,
        style_profile=style_profile,
        constraints=constraints or {},
    )
    
    return await orchestrator.execute(intent, context)


def get_agent_system_status() -> Dict[str, Any]:
    """Get current status of the agent system.
    
    Returns:
        Dict with agent counts, tool counts, and domain coverage
    """
    registry = get_tool_registry()
    orchestrator = get_master_orchestrator()
    
    return {
        "initialized": bool(orchestrator.sub_agents),
        "tool_count": len(registry.list_all()),
        "domain_agent_count": len(orchestrator.sub_agents),
        "domains": list(orchestrator._domain_agent_map.keys()),
        "agent_names": list(orchestrator.sub_agents.keys()),
    }

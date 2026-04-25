"""
Unreal Engine Advanced MCP Server

A streamlined MCP server focused on advanced composition tools for Unreal Engine.
Contains only the advanced tools from the expanded MCP tool system to keep tool count manageable.
"""

import logging

# Core infrastructure (re-exported for tests and helpers)
from server.core import (
    mcp,
    configure_logging,
    server_lifespan,
    get_unreal_connection,
    reset_unreal_connection,
    UnrealConnection,
)

# Re-export tool functions for backwards-compatible direct imports and tests.
from server.actor_tools import (
    get_actors_in_level,
    find_actors_by_name,
    delete_actor,
    spawn_actor,
    set_actor_transform,
    batch_spawn_actors,
    find_actor_by_mcp_id,
    set_actor_transform_by_mcp_id,
    delete_actor_by_mcp_id,
)

from server.blueprint_tools import (
    create_blueprint,
    add_component_to_blueprint,
    set_static_mesh_properties,
    set_physics_properties,
    compile_blueprint,
    read_blueprint_content,
    analyze_blueprint_graph,
    get_blueprint_variable_details,
    get_blueprint_function_details,
)

from server.blueprint_graph_tools import (
    add_node,
    connect_nodes,
    create_variable,
    set_blueprint_variable_properties,
    add_event_node,
    delete_node,
    set_node_property,
    create_function,
    add_function_input,
    add_function_output,
    delete_function,
    rename_function,
)

from server.material_tools import (
    get_available_materials,
    apply_material_to_actor,
    apply_material_to_blueprint,
    get_actor_material_info,
    get_blueprint_material_info,
    set_mesh_material_color,
)

from server.world_building_tools import (
    create_pyramid,
    create_wall,
    create_tower,
    create_staircase,
    construct_house,
    construct_mansion,
    create_arch,
    spawn_physics_blueprint_actor,
    create_maze,
    create_town,
    create_castle_fortress,
    create_suspension_bridge,
    create_aqueduct,
)

from server.scene_tools import (
    scene_create,
    scene_upsert_actor,
    scene_upsert_actors,
    scene_delete_actor,
    scene_list_objects,
    scene_health,
    scene_plan_sync,
)


# Import tool modules to register their @mcp.tool() decorated functions.
# These side-effect imports attach tools to the shared `mcp` instance.
from server import actor_tools        # noqa: F401
from server import material_tools      # noqa: F401
from server import blueprint_tools     # noqa: F401
from server import blueprint_graph_tools  # noqa: F401
from server import world_building_tools  # noqa: F401

# Re-export the mcp instance for any external consumers
__all__ = [
    "mcp",
    "get_unreal_connection",
    "reset_unreal_connection",
    "UnrealConnection",
    "configure_logging",
    "server_lifespan",
    "get_actors_in_level",
    "find_actors_by_name",
    "delete_actor",
    "spawn_actor",
    "set_actor_transform",
    "batch_spawn_actors",
    "create_blueprint",
    "add_component_to_blueprint",
    "set_static_mesh_properties",
    "set_physics_properties",
    "compile_blueprint",
    "read_blueprint_content",
    "analyze_blueprint_graph",
    "get_blueprint_variable_details",
    "get_blueprint_function_details",
    "add_node",
    "connect_nodes",
    "create_variable",
    "set_blueprint_variable_properties",
    "add_event_node",
    "delete_node",
    "set_node_property",
    "create_function",
    "add_function_input",
    "add_function_output",
    "delete_function",
    "rename_function",
    "get_available_materials",
    "apply_material_to_actor",
    "apply_material_to_blueprint",
    "get_actor_material_info",
    "get_blueprint_material_info",
    "set_mesh_material_color",
    "create_pyramid",
    "create_wall",
    "create_tower",
    "create_staircase",
    "construct_house",
    "construct_mansion",
    "create_arch",
    "spawn_physics_blueprint_actor",
    "create_maze",
    "create_town",
    "create_castle_fortress",
    "create_suspension_bridge",
    "create_aqueduct",
]


if __name__ == "__main__":
    configure_logging()
    logger = logging.getLogger("UnrealMCP_Advanced")
    logger.info("Starting Advanced MCP server with stdio transport")
    mcp.run(transport='stdio')

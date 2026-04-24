"""
Unreal Engine Advanced MCP Server

A streamlined MCP server focused on advanced composition tools for Unreal Engine.
Contains only the advanced tools from the expanded MCP tool system to keep tool count manageable.
"""

import logging
import os

from server.core import mcp, configure_logging, server_lifespan

# Import tool modules to register their @mcp.tool() decorated tools
from server import actor_tools        # noqa: F401
from server import material_tools      # noqa: F401
from server import blueprint_tools    # noqa: F401
from server import blueprint_graph_tools  # noqa: F401
from server import world_building_tools  # noqa: F401

# Re-export the mcp instance for any external consumers
__all__ = ["mcp"]

if __name__ == "__main__":
    configure_logging()
    logger = logging.getLogger("UnrealMCP_Advanced")
    logger.info("Starting Advanced MCP server with stdio transport")
    mcp.run(transport='stdio')

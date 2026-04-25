"""
Actor utility functions for Unreal MCP Server.
Contains helper functions for spawning and managing actors.
"""
from typing import Dict, Any, List
import logging
from utils.responses import is_success_response, make_error_response

logger = logging.getLogger(__name__)

try:
    from .actor_name_manager import get_unique_actor_name, get_global_actor_name_manager
except ImportError:
    logger.warning("Could not import actor_name_manager, unique name generation disabled")
    def get_unique_actor_name(base_name: str, unreal_connection=None) -> str:
        return base_name
    def get_global_actor_name_manager():
        return None


def spawn_blueprint_actor(
    unreal_connection,
    blueprint_name: str,
    actor_name: str,
    location: List[float] = [0, 0, 0],
    rotation: List[float] = [0, 0, 0],
    auto_unique_name: bool = True
) -> Dict[str, Any]:
    try:
        if not unreal_connection:
            return make_error_response("No Unreal connection provided")
        
        original_name = actor_name
        
        if auto_unique_name:
            unique_name = get_unique_actor_name(actor_name, unreal_connection)
            if unique_name != actor_name:
                logger.debug(f"Blueprint actor name changed: '{actor_name}' -> '{unique_name}'")
                actor_name = unique_name
        
        params = {
            "blueprint_name": blueprint_name,
            "actor_name": actor_name,
            "location": location,
            "rotation": rotation
        }
        
        response = unreal_connection.send_command("spawn_blueprint_actor", params)
        
        if response and is_success_response(response):
            manager = get_global_actor_name_manager()
            if manager:
                manager.mark_actor_created(actor_name)
            
            if isinstance(response, dict):
                response["final_name"] = actor_name
                response["original_name"] = original_name
        
        return response or make_error_response("No response from Unreal")
        
    except Exception as e:
        logger.error(f"spawn_blueprint_actor helper error: {e}")
        return make_error_response(str(e))


def get_blueprint_material_info(
    unreal_connection,
    blueprint_name: str,
    component_name: str
) -> Dict[str, Any]:
    try:
        if not unreal_connection:
            return make_error_response("No Unreal connection provided")
        
        params = {
            "blueprint_name": blueprint_name,
            "component_name": component_name
        }
        
        response = unreal_connection.send_command("get_blueprint_material_info", params)
        return response or make_error_response("No response from Unreal")
        
    except Exception as e:
        logger.error(f"get_blueprint_material_info helper error: {e}")
        return make_error_response(str(e))
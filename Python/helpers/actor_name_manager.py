"""
Actor Name Management System

Centralized system for managing unique actor names across all MCP functions.
Prevents duplicate name errors by automatically generating unique names and tracking actors.
"""

import logging
import time
import uuid
from typing import Dict, Any, Set, Optional
from utils.responses import is_success_response, make_error_response

logger = logging.getLogger("ActorNameManager")


class ActorNameManager:
    """Centralized system for managing unique actor names across all MCP functions."""
    
    def __init__(self):
        self._known_actors: Set[str] = set()
        self._session_id = str(int(time.time()))[-6:]
        self._actor_counters: Dict[str, int] = {}
        logger.info(f"ActorNameManager initialized with session ID: {self._session_id}")
        
        self._known_actors.clear()
        
    
    def generate_unique_name(self, base_name: str, unreal_connection=None) -> str:
        """
        Generate a unique actor name based on the desired base name.
        
        Strategy:
        1. First try the base name as-is
        2. If that exists, try base_name with session suffix
        3. If that exists, try base_name with counter
        4. If that exists, try base_name with session + counter + unique_id
        """
        base_name = str(base_name).strip()
        if not base_name:
            base_name = f"Actor_{self._session_id}"
        
        if not self._actor_exists(base_name, unreal_connection):
            return base_name
        
        session_name = f"{base_name}_{self._session_id}"
        if not self._actor_exists(session_name, unreal_connection):
            return session_name
        
        counter_key = base_name
        if counter_key not in self._actor_counters:
            self._actor_counters[counter_key] = 0
        
        for attempt in range(1000):
            self._actor_counters[counter_key] += 1
            counter_name = f"{base_name}_{self._actor_counters[counter_key]}"
            
            if not self._actor_exists(counter_name, unreal_connection):
                return counter_name
        
        unique_suffix = str(uuid.uuid4())[:8]
        final_name = f"{base_name}_{self._session_id}_{self._actor_counters[counter_key]}_{unique_suffix}"
        
        logger.info(f"Generated unique name: {base_name} -> {final_name}")
        return final_name
    
    def _actor_exists(self, name: str, unreal_connection=None) -> bool:
        """Check if an actor with the given name exists."""
        if name in self._known_actors:
            return True
        
        if unreal_connection:
            try:
                response = unreal_connection.send_command("find_actors_by_name", {"pattern": name})
                actors = []
                if response and is_success_response(response):
                    if isinstance(response.get("actors"), list):
                        actors = response.get("actors", [])

                if actors:
                    if isinstance(actors, list):
                        for actor in actors:
                            if isinstance(actor, dict) and actor.get("name") == name:
                                self._known_actors.add(name)
                                return True
            except Exception as e:
                logger.debug(f"Error checking actor existence for '{name}': {e}")
        
        return False
    
    def mark_actor_created(self, name: str):
        """Mark an actor as created (add to known actors)."""
        self._known_actors.add(name)
    
    def remove_actor(self, name: str):
        """Remove an actor from known actors (when deleted)."""
        self._known_actors.discard(name)
    

_global_actor_name_manager = ActorNameManager()

def get_global_actor_name_manager() -> ActorNameManager:
    return _global_actor_name_manager

def clear_actor_cache():
    global _global_actor_name_manager
    _global_actor_name_manager._known_actors.clear()
    _global_actor_name_manager._actor_counters.clear()
    logger.info("Cleared global actor cache")

def get_unique_actor_name(base_name: str, unreal_connection=None) -> str:
    return _global_actor_name_manager.generate_unique_name(base_name, unreal_connection)

def safe_spawn_actor(unreal_connection, params: Dict[str, Any], auto_unique_name: bool = True) -> Dict[str, Any]:
    if not unreal_connection:
        return make_error_response("No Unreal connection available")
    
    original_name = params.get("name", "Actor")
    
    if auto_unique_name:
        unique_name = _global_actor_name_manager.generate_unique_name(original_name, unreal_connection)
        params["name"] = unique_name
        
        if unique_name != original_name:
            logger.debug(f"Actor name changed: '{original_name}' -> '{unique_name}'")
    
    try:
        response = unreal_connection.send_command("spawn_actor", params)
        
        if response and is_success_response(response):
            _global_actor_name_manager.mark_actor_created(params["name"])
            if isinstance(response, dict):
                response["final_name"] = params["name"]
                response["original_name"] = original_name
        elif response and not is_success_response(response) and "already exists" in response.get("error", ""):
            if auto_unique_name:
                retry_name = _global_actor_name_manager.generate_unique_name(original_name, unreal_connection)
                params["name"] = retry_name
                try:
                    retry_response = unreal_connection.send_command("spawn_actor", params)
                    if retry_response and is_success_response(retry_response):
                        _global_actor_name_manager.mark_actor_created(retry_name)
                        if isinstance(retry_response, dict):
                            retry_response["final_name"] = retry_name
                            retry_response["original_name"] = original_name
                    return retry_response or make_error_response("No response from Unreal")
                except Exception as e:
                    logger.error(f"Error in safe_spawn_actor retry: {e}")
                    return make_error_response(str(e))
            return response
        
        return response or make_error_response("No response from Unreal")
        
    except Exception as e:
        logger.error(f"Error in safe_spawn_actor: {e}")
        return make_error_response(str(e))

def safe_delete_actor(unreal_connection, actor_name: str) -> Dict[str, Any]:
    if not unreal_connection:
        return make_error_response("No Unreal connection available")
    
    try:
        response = unreal_connection.send_command("delete_actor", {"name": actor_name})
        
        if response and is_success_response(response):
            _global_actor_name_manager.remove_actor(actor_name)
        
        return response or make_error_response("No response from Unreal")
        
    except Exception as e:
        logger.error(f"Error in safe_delete_actor: {e}")
        return make_error_response(str(e))
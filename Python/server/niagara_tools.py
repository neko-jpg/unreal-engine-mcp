""" Niagara / VFX MCP tools (Sub-batch I, issue #49).

Each tool wraps a single C++ command in FEpicUnrealMCPNiagaraCommands. We make
the underlying send_command call inline (with a string literal) so the
3-layer audit (scripts/audit_route_contracts.py) sees the binding statically.
"""

from typing import Any, Dict, List, Optional

from server.core import mcp, get_unreal_connection
from server.validation import (
    validate_string,
    ValidationError,
    make_validation_error_response_from_exception,
)
from utils.responses import make_error_response


def _envelope(name: str, result: Any) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return make_error_response(f"Unexpected Unreal response for '{name}'")
    if not result.get("success", False):
        err = result.get("error", "unknown error")
        hint = result.get("hint")
        if hint:
            return make_error_response(f"{name}: {err} (hint: {hint})")
        return make_error_response(f"{name}: {err}")
    return result


# ---- Asset creation --------------------------------------------------------

@mcp.tool()
def create_niagara_system(asset_path: str = "/Game/Niagara", asset_name: str = "NS_New") -> Dict[str, Any]:
    """Create an empty UNiagaraSystem asset at asset_path/asset_name."""
    try:
        validate_string(asset_path, "asset_path")
        validate_string(asset_name, "asset_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("create_niagara_system", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_niagara_system': {e}")
    return _envelope("create_niagara_system", result)


@mcp.tool()
def create_niagara_emitter(asset_path: str = "/Game/Niagara", asset_name: str = "NE_New") -> Dict[str, Any]:
    """Create an empty UNiagaraEmitter asset."""
    try:
        validate_string(asset_path, "asset_path")
        validate_string(asset_name, "asset_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("create_niagara_emitter", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_niagara_emitter': {e}")
    return _envelope("create_niagara_emitter", result)


@mcp.tool()
def add_emitter_to_system(system_path: str, emitter_path: str) -> Dict[str, Any]:
    """Queue an emitter slot add inside a Niagara System asset (asset dirtied for manual save)."""
    try:
        validate_string(system_path, "system_path")
        validate_string(emitter_path, "emitter_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("add_emitter_to_system", {"system_path": system_path, "emitter_path": emitter_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_emitter_to_system': {e}")
    return _envelope("add_emitter_to_system", result)


@mcp.tool()
def add_niagara_module(emitter_path: str, module_name: str, stage: str = "ParticleUpdate") -> Dict[str, Any]:
    """Queue a module add at a stage on an emitter (asset dirtied)."""
    try:
        validate_string(emitter_path, "emitter_path")
        validate_string(module_name, "module_name")
        validate_string(stage, "stage")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("add_niagara_module", {"emitter_path": emitter_path, "module_name": module_name, "stage": stage})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_niagara_module': {e}")
    return _envelope("add_niagara_module", result)


@mcp.tool()
def remove_niagara_module(emitter_path: str, module_name: str) -> Dict[str, Any]:
    """Queue a module remove on an emitter (asset dirtied)."""
    try:
        validate_string(emitter_path, "emitter_path")
        validate_string(module_name, "module_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("remove_niagara_module", {"emitter_path": emitter_path, "module_name": module_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'remove_niagara_module': {e}")
    return _envelope("remove_niagara_module", result)


@mcp.tool()
def set_niagara_spawn_rate(actor_name: str, spawn_rate: float, component_name: str = "") -> Dict[str, Any]:
    """Set User.SpawnRate (float) on a NiagaraComponent."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("set_niagara_spawn_rate", {"actor_name": actor_name, "component_name": component_name, "spawn_rate": float(spawn_rate)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_niagara_spawn_rate': {e}")
    return _envelope("set_niagara_spawn_rate", result)


@mcp.tool()
def set_niagara_burst(actor_name: str, burst_count: int, component_name: str = "") -> Dict[str, Any]:
    """Set User.BurstCount (int) on a NiagaraComponent."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("set_niagara_burst", {"actor_name": actor_name, "component_name": component_name, "burst_count": int(burst_count)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_niagara_burst': {e}")
    return _envelope("set_niagara_burst", result)


@mcp.tool()
def set_niagara_lifetime(actor_name: str, lifetime: float, component_name: str = "") -> Dict[str, Any]:
    """Set User.Lifetime (float seconds) on a NiagaraComponent."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("set_niagara_lifetime", {"actor_name": actor_name, "component_name": component_name, "lifetime": float(lifetime)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_niagara_lifetime': {e}")
    return _envelope("set_niagara_lifetime", result)


@mcp.tool()
def set_niagara_velocity(actor_name: str, velocity: List[float], component_name: str = "") -> Dict[str, Any]:
    """Set User.Velocity (FVector) on a NiagaraComponent. velocity must be [x,y,z]."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    if not isinstance(velocity, list) or len(velocity) != 3:
        return make_error_response("velocity must be [x, y, z]")
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("set_niagara_velocity", {"actor_name": actor_name, "component_name": component_name, "velocity": [float(v) for v in velocity]})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_niagara_velocity': {e}")
    return _envelope("set_niagara_velocity", result)


@mcp.tool()
def set_niagara_gravity(actor_name: str, gravity_z: float = -980.0, component_name: str = "") -> Dict[str, Any]:
    """Set User.Gravity (FVector) on a NiagaraComponent."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("set_niagara_gravity", {"actor_name": actor_name, "component_name": component_name, "gravity_z": float(gravity_z)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_niagara_gravity': {e}")
    return _envelope("set_niagara_gravity", result)


@mcp.tool()
def set_niagara_color(actor_name: str, color: List[float], component_name: str = "") -> Dict[str, Any]:
    """Set User.Color (FLinearColor) on a NiagaraComponent. color is [r,g,b] or [r,g,b,a]."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    if not isinstance(color, list) or len(color) < 3 or len(color) > 4:
        return make_error_response("color must be [r,g,b] or [r,g,b,a]")
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("set_niagara_color", {"actor_name": actor_name, "component_name": component_name, "color": [float(v) for v in color]})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_niagara_color': {e}")
    return _envelope("set_niagara_color", result)


@mcp.tool()
def set_niagara_size(actor_name: str, size: float, component_name: str = "") -> Dict[str, Any]:
    """Set User.Size (float multiplier) on a NiagaraComponent."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("set_niagara_size", {"actor_name": actor_name, "component_name": component_name, "size": float(size)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_niagara_size': {e}")
    return _envelope("set_niagara_size", result)


@mcp.tool()
def set_niagara_ribbon_renderer(actor_name: str, material_path: str = "", component_name: str = "") -> Dict[str, Any]:
    """Set User.Ribbon.Material on a NiagaraComponent."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("set_niagara_ribbon_renderer", {"actor_name": actor_name, "component_name": component_name, "material_path": material_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_niagara_ribbon_renderer': {e}")
    return _envelope("set_niagara_ribbon_renderer", result)


@mcp.tool()
def set_niagara_sprite_renderer(actor_name: str, material_path: str = "", component_name: str = "") -> Dict[str, Any]:
    """Set User.Sprite.Material on a NiagaraComponent."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("set_niagara_sprite_renderer", {"actor_name": actor_name, "component_name": component_name, "material_path": material_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_niagara_sprite_renderer': {e}")
    return _envelope("set_niagara_sprite_renderer", result)


@mcp.tool()
def set_niagara_mesh_renderer(actor_name: str, mesh_path: str = "", component_name: str = "") -> Dict[str, Any]:
    """Set User.Mesh (UStaticMesh) on a NiagaraComponent."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("set_niagara_mesh_renderer", {"actor_name": actor_name, "component_name": component_name, "mesh_path": mesh_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_niagara_mesh_renderer': {e}")
    return _envelope("set_niagara_mesh_renderer", result)


@mcp.tool()
def set_niagara_gpu_simulation(emitter_path: str, use_gpu: bool = True) -> Dict[str, Any]:
    """Toggle GPU/CPU sim on a Niagara Emitter asset (asset dirtied for manual save)."""
    try:
        validate_string(emitter_path, "emitter_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("set_niagara_gpu_simulation", {"emitter_path": emitter_path, "use_gpu": bool(use_gpu)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_niagara_gpu_simulation': {e}")
    return _envelope("set_niagara_gpu_simulation", result)


@mcp.tool()
def set_niagara_collision(actor_name: str, enabled: bool = True, component_name: str = "") -> Dict[str, Any]:
    """Set User.CollisionEnabled (bool) on a NiagaraComponent."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("set_niagara_collision", {"actor_name": actor_name, "component_name": component_name, "enabled": bool(enabled)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_niagara_collision': {e}")
    return _envelope("set_niagara_collision", result)


@mcp.tool()
def add_niagara_user_parameter(system_path: str, parameter_name: str, parameter_type: str = "float") -> Dict[str, Any]:
    """Queue a User.* parameter declaration on a Niagara System."""
    try:
        validate_string(system_path, "system_path")
        validate_string(parameter_name, "parameter_name")
        validate_string(parameter_type, "parameter_type")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("add_niagara_user_parameter", {"system_path": system_path, "parameter_name": parameter_name, "parameter_type": parameter_type})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_niagara_user_parameter': {e}")
    return _envelope("add_niagara_user_parameter", result)


@mcp.tool()
def set_niagara_user_parameter(actor_name: str, parameter_name: str, parameter_type: str, value: Any, component_name: str = "") -> Dict[str, Any]:
    """Set a User.* parameter on a NiagaraComponent. parameter_type: float/int/bool/vector/color."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(parameter_name, "parameter_name")
        validate_string(parameter_type, "parameter_type")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    if parameter_type not in {"float", "int", "bool", "vector", "color"}:
        return make_error_response("parameter_type must be one of: float, int, bool, vector, color")
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("set_niagara_user_parameter", {"actor_name": actor_name, "component_name": component_name, "parameter_name": parameter_name, "parameter_type": parameter_type, "value": value})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_niagara_user_parameter': {e}")
    return _envelope("set_niagara_user_parameter", result)


@mcp.tool()
def add_niagara_component(actor_name: str, system_path: str = "", component_name: str = "NiagaraComponent") -> Dict[str, Any]:
    """Attach a new UNiagaraComponent to an actor (optionally bound to system_path)."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(component_name, "component_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("add_niagara_component", {"actor_name": actor_name, "system_path": system_path, "component_name": component_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_niagara_component': {e}")
    return _envelope("add_niagara_component", result)


@mcp.tool()
def attach_niagara_to_actor(actor_name: str, system_path: str, component_name: str = "") -> Dict[str, Any]:
    """Bind a Niagara System asset to an existing NiagaraComponent and activate it."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(system_path, "system_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("attach_niagara_to_actor", {"actor_name": actor_name, "component_name": component_name, "system_path": system_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'attach_niagara_to_actor': {e}")
    return _envelope("attach_niagara_to_actor", result)


@mcp.tool()
def bind_niagara_parameter(actor_name: str, parameter_name: str, source_object: str = "", component_name: str = "") -> Dict[str, Any]:
    """Bind a User.* object parameter on a NiagaraComponent (material / mesh / texture / etc)."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(parameter_name, "parameter_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("bind_niagara_parameter", {"actor_name": actor_name, "component_name": component_name, "parameter_name": parameter_name, "source_object": source_object})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'bind_niagara_parameter': {e}")
    return _envelope("bind_niagara_parameter", result)


@mcp.tool()
def create_niagara_data_channel(asset_path: str = "/Game/Niagara", asset_name: str = "NDC_New") -> Dict[str, Any]:
    """Queue a NiagaraDataChannel asset creation (gated by NiagaraDataChannelEditor)."""
    try:
        validate_string(asset_path, "asset_path")
        validate_string(asset_name, "asset_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("create_niagara_data_channel", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_niagara_data_channel': {e}")
    return _envelope("create_niagara_data_channel", result)


@mcp.tool()
def create_niagara_effect_type(asset_path: str = "/Game/Niagara", asset_name: str = "FX_NewEffectType") -> Dict[str, Any]:
    """Create a UNiagaraEffectType asset (used for scalability + significance)."""
    try:
        validate_string(asset_path, "asset_path")
        validate_string(asset_name, "asset_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("create_niagara_effect_type", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_niagara_effect_type': {e}")
    return _envelope("create_niagara_effect_type", result)


@mcp.tool()
def set_niagara_scalability(effect_type_path: str, quality_level: str = "High") -> Dict[str, Any]:
    """Queue a scalability rule update on a Niagara EffectType asset."""
    try:
        validate_string(effect_type_path, "effect_type_path")
        validate_string(quality_level, "quality_level")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("set_niagara_scalability", {"effect_type_path": effect_type_path, "quality_level": quality_level})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_niagara_scalability': {e}")
    return _envelope("set_niagara_scalability", result)


@mcp.tool()
def niagara_debug_console(command: str = "fx.Niagara.Debug.Hud 1") -> Dict[str, Any]:
    """Run a fx.Niagara.* console command on the editor world."""
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("niagara_debug_console", {"command": command})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'niagara_debug_console': {e}")
    return _envelope("niagara_debug_console", result)


@mcp.tool()
def niagara_sim_cache(action: str = "create", asset_path: str = "/Game/Niagara", asset_name: str = "NSC_New") -> Dict[str, Any]:
    """Queue a NiagaraSimCache record/playback action; runtime cache requires PIE."""
    try:
        validate_string(action, "action")
        validate_string(asset_path, "asset_path")
        validate_string(asset_name, "asset_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if unreal is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        result = unreal.send_command("niagara_sim_cache", {"action": action, "asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'niagara_sim_cache': {e}")
    return _envelope("niagara_sim_cache", result)
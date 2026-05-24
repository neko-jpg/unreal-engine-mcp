"""PCG Framework (Sub-batch O, issue #45) MCP tools (auto-generated scaffold).

Each tool wraps a single C++ handler. The C++ side returns a queued
envelope when the underlying plugin is missing; the wrappers surface that
to the caller via an actionable error envelope.
"""

from typing import Any, Dict

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
        return make_error_response(f"{name}: {err}" + (f" (hint: {hint})" if hint else ""))
    return result


@mcp.tool()
def create_pcg_graph(asset_path: str = "/Game/PCG", asset_name: str = "PCGG_New") -> Dict[str, Any]:
    """create_pcg_graph -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_pcg_graph", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_pcg_graph': {e}")
    return _envelope("create_pcg_graph", r)


@mcp.tool()
def add_pcg_component(actor_name: str, graph_path: str) -> Dict[str, Any]:
    """add_pcg_component -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(graph_path, "graph_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_pcg_component", {"actor_name": actor_name, "graph_path": graph_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_pcg_component': {e}")
    return _envelope("add_pcg_component", r)


@mcp.tool()
def create_pcg_volume(actor_name: str = "PCGVolume", extent_xyz: list = [2000.0, 2000.0, 500.0]) -> Dict[str, Any]:
    """create_pcg_volume -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_pcg_volume", {"actor_name": actor_name, "extent_xyz": extent_xyz})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_pcg_volume': {e}")
    return _envelope("create_pcg_volume", r)


@mcp.tool()
def add_pcg_node(graph_path: str, node_type: str) -> Dict[str, Any]:
    """add_pcg_node -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(graph_path, "graph_path")
        validate_string(node_type, "node_type")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_pcg_node", {"graph_path": graph_path, "node_type": node_type})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_pcg_node': {e}")
    return _envelope("add_pcg_node", r)


@mcp.tool()
def connect_pcg_nodes(graph_path: str, from_node: str, to_node: str) -> Dict[str, Any]:
    """connect_pcg_nodes -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(graph_path, "graph_path")
        validate_string(from_node, "from_node")
        validate_string(to_node, "to_node")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("connect_pcg_nodes", {"graph_path": graph_path, "from_node": from_node, "to_node": to_node})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'connect_pcg_nodes': {e}")
    return _envelope("connect_pcg_nodes", r)


@mcp.tool()
def set_pcg_graph_parameter(graph_path: str, parameter: str, value: str = "") -> Dict[str, Any]:
    """set_pcg_graph_parameter -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(graph_path, "graph_path")
        validate_string(parameter, "parameter")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_pcg_graph_parameter", {"graph_path": graph_path, "parameter": parameter, "value": value})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_pcg_graph_parameter': {e}")
    return _envelope("set_pcg_graph_parameter", r)


@mcp.tool()
def configure_pcg_spline_sampler(graph_path: str, spline_actor: str) -> Dict[str, Any]:
    """configure_pcg_spline_sampler -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(graph_path, "graph_path")
        validate_string(spline_actor, "spline_actor")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_pcg_spline_sampler", {"graph_path": graph_path, "spline_actor": spline_actor})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_pcg_spline_sampler': {e}")
    return _envelope("configure_pcg_spline_sampler", r)


@mcp.tool()
def configure_pcg_surface_sampler(graph_path: str, surface_actor: str, density: float = 1.0) -> Dict[str, Any]:
    """configure_pcg_surface_sampler -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(graph_path, "graph_path")
        validate_string(surface_actor, "surface_actor")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_pcg_surface_sampler", {"graph_path": graph_path, "surface_actor": surface_actor, "density": float(density)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_pcg_surface_sampler': {e}")
    return _envelope("configure_pcg_surface_sampler", r)


@mcp.tool()
def configure_pcg_static_mesh_spawner(graph_path: str, mesh_path: str) -> Dict[str, Any]:
    """configure_pcg_static_mesh_spawner -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(graph_path, "graph_path")
        validate_string(mesh_path, "mesh_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_pcg_static_mesh_spawner", {"graph_path": graph_path, "mesh_path": mesh_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_pcg_static_mesh_spawner': {e}")
    return _envelope("configure_pcg_static_mesh_spawner", r)


@mcp.tool()
def configure_pcg_rule(graph_path: str, rule_name: str) -> Dict[str, Any]:
    """configure_pcg_rule -- Add a filter/rule node to a PCG graph."""
    try:
        validate_string(graph_path, "graph_path")
        validate_string(rule_name, "rule_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_pcg_rule", {"graph_path": graph_path, "rule_name": rule_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_pcg_rule': {e}")
    return _envelope("configure_pcg_rule", r)


@mcp.tool()
def create_pcg_biome_graph(asset_path: str = "/Game/PCG", asset_name: str = "PCGB_New") -> Dict[str, Any]:
    """create_pcg_biome_graph -- Create a new PCG biome graph asset."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_pcg_biome_graph", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_pcg_biome_graph': {e}")
    return _envelope("create_pcg_biome_graph", r)


@mcp.tool()
def operate_pcg_point_data(graph_path: str, operation: str = "Project") -> Dict[str, Any]:
    """operate_pcg_point_data -- Configure point data operations on a PCG graph."""
    try:
        validate_string(graph_path, "graph_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("operate_pcg_point_data", {"graph_path": graph_path, "operation": operation})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'operate_pcg_point_data': {e}")
    return _envelope("operate_pcg_point_data", r)


@mcp.tool()
def operate_pcg_attribute(graph_path: str, attribute_name: str) -> Dict[str, Any]:
    """operate_pcg_attribute -- Configure attribute operations on a PCG graph."""
    try:
        validate_string(graph_path, "graph_path")
        validate_string(attribute_name, "attribute_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("operate_pcg_attribute", {"graph_path": graph_path, "attribute_name": attribute_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'operate_pcg_attribute': {e}")
    return _envelope("operate_pcg_attribute", r)


@mcp.tool()
def execute_pcg_graph(actor_name: str) -> Dict[str, Any]:
    """execute_pcg_graph -- Trigger PCG graph generation on an actor."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("execute_pcg_graph", {"actor_name": actor_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'execute_pcg_graph': {e}")
    return _envelope("execute_pcg_graph", r)


@mcp.tool()
def regenerate_pcg_graph(actor_name: str) -> Dict[str, Any]:
    """regenerate_pcg_graph -- Cleanup and regenerate a PCG graph on an actor."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("regenerate_pcg_graph", {"actor_name": actor_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'regenerate_pcg_graph': {e}")
    return _envelope("regenerate_pcg_graph", r)


@mcp.tool()
def set_pcg_runtime_generation(actor_name: str, enable: bool = True) -> Dict[str, Any]:
    """set_pcg_runtime_generation -- Enable/disable runtime generation on a PCG component."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_pcg_runtime_generation", {"actor_name": actor_name, "enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_pcg_runtime_generation': {e}")
    return _envelope("set_pcg_runtime_generation", r)


@mcp.tool()
def use_pcg_editor_mode(mode: str = "Sculpt") -> Dict[str, Any]:
    """use_pcg_editor_mode -- Set the PCG editor mode preference."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("use_pcg_editor_mode", {"mode": mode})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'use_pcg_editor_mode': {e}")
    return _envelope("use_pcg_editor_mode", r)


@mcp.tool()
def create_pcg_tool(asset_path: str = "/Game/PCG", asset_name: str = "PCGTool_New") -> Dict[str, Any]:
    """create_pcg_tool -- Create a new PCG tool graph asset."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_pcg_tool", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_pcg_tool': {e}")
    return _envelope("create_pcg_tool", r)


@mcp.tool()
def set_pcg_debug_display(enable: bool = True) -> Dict[str, Any]:
    """set_pcg_debug_display -- Enable/disable PCG debug display in the editor."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_pcg_debug_display", {"enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_pcg_debug_display': {e}")
    return _envelope("set_pcg_debug_display", r)


@mcp.tool()
def configure_pcg_self_pruning(graph_path: str, radius: float = 100.0) -> Dict[str, Any]:
    """configure_pcg_self_pruning -- Configure self-pruning radius on a PCG graph."""
    try:
        validate_string(graph_path, "graph_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_pcg_self_pruning", {"graph_path": graph_path, "radius": float(radius)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_pcg_self_pruning': {e}")
    return _envelope("configure_pcg_self_pruning", r)

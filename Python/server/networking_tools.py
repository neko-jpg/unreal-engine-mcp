"""Networking / Multiplayer (Sub-batch P, issue #41) MCP tools (auto-generated scaffold).

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
def create_rpc_server_function(blueprint_path: str, function_name: str, with_validation: bool = False) -> Dict[str, Any]:
    """create_rpc_server_function -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(blueprint_path, "blueprint_path")
        validate_string(function_name, "function_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_rpc_server_function", {"blueprint_path": blueprint_path, "function_name": function_name, "with_validation": bool(with_validation)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_rpc_server_function': {e}")
    return _envelope("create_rpc_server_function", r)


@mcp.tool()
def create_rpc_client_function(blueprint_path: str, function_name: str) -> Dict[str, Any]:
    """create_rpc_client_function -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(blueprint_path, "blueprint_path")
        validate_string(function_name, "function_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_rpc_client_function", {"blueprint_path": blueprint_path, "function_name": function_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_rpc_client_function': {e}")
    return _envelope("create_rpc_client_function", r)


@mcp.tool()
def create_rpc_multicast_function(blueprint_path: str, function_name: str) -> Dict[str, Any]:
    """create_rpc_multicast_function -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(blueprint_path, "blueprint_path")
        validate_string(function_name, "function_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_rpc_multicast_function", {"blueprint_path": blueprint_path, "function_name": function_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_rpc_multicast_function': {e}")
    return _envelope("create_rpc_multicast_function", r)


@mcp.tool()
def set_rpc_reliability(blueprint_path: str, function_name: str, reliable: bool = True) -> Dict[str, Any]:
    """set_rpc_reliability -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(blueprint_path, "blueprint_path")
        validate_string(function_name, "function_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_rpc_reliability", {"blueprint_path": blueprint_path, "function_name": function_name, "reliable": bool(reliable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_rpc_reliability': {e}")
    return _envelope("set_rpc_reliability", r)


@mcp.tool()
def set_rep_notify(blueprint_path: str, variable_name: str, repnotify_function: str = "") -> Dict[str, Any]:
    """set_rep_notify -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(blueprint_path, "blueprint_path")
        validate_string(variable_name, "variable_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_rep_notify", {"blueprint_path": blueprint_path, "variable_name": variable_name, "repnotify_function": repnotify_function})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_rep_notify': {e}")
    return _envelope("set_rep_notify", r)


@mcp.tool()
def list_replicated_variables(blueprint_path: str) -> Dict[str, Any]:
    """list_replicated_variables -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(blueprint_path, "blueprint_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("list_replicated_variables", {"blueprint_path": blueprint_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'list_replicated_variables': {e}")
    return _envelope("list_replicated_variables", r)


@mcp.tool()
def set_network_prediction(actor_name: str, enable: bool = True) -> Dict[str, Any]:
    """set_network_prediction -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_network_prediction", {"actor_name": actor_name, "enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_network_prediction': {e}")
    return _envelope("set_network_prediction", r)


@mcp.tool()
def configure_dedicated_server(map_name: str = "/Game/Maps/StartUp", port: int = 7777) -> Dict[str, Any]:
    """configure_dedicated_server -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_dedicated_server", {"map_name": map_name, "port": int(port)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_dedicated_server': {e}")
    return _envelope("configure_dedicated_server", r)


@mcp.tool()
def start_listen_server(map_name: str = "/Game/Maps/StartUp", port: int = 7777) -> Dict[str, Any]:
    """start_listen_server -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("start_listen_server", {"map_name": map_name, "port": int(port)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'start_listen_server': {e}")
    return _envelope("start_listen_server", r)


@mcp.tool()
def start_client(host: str = "127.0.0.1", port: int = 7777) -> Dict[str, Any]:
    """start_client -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("start_client", {"host": host, "port": int(port)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'start_client': {e}")
    return _envelope("start_client", r)


@mcp.tool()
def configure_multi_pie(client_count: int = 2) -> Dict[str, Any]:
    """configure_multi_pie -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_multi_pie", {"client_count": int(client_count)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_multi_pie': {e}")
    return _envelope("configure_multi_pie", r)


@mcp.tool()
def set_online_subsystem(subsystem: str = "NULL") -> Dict[str, Any]:
    """set_online_subsystem -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_online_subsystem", {"subsystem": subsystem})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_online_subsystem': {e}")
    return _envelope("set_online_subsystem", r)


@mcp.tool()
def create_session(session_name: str = "Default", max_players: int = 8) -> Dict[str, Any]:
    """create_session -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_session", {"session_name": session_name, "max_players": int(max_players)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_session': {e}")
    return _envelope("create_session", r)


@mcp.tool()
def find_sessions(timeout_seconds: float = 10.0) -> Dict[str, Any]:
    """find_sessions -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("find_sessions", {"timeout_seconds": float(timeout_seconds)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'find_sessions': {e}")
    return _envelope("find_sessions", r)


@mcp.tool()
def join_session(session_name: str = "Default") -> Dict[str, Any]:
    """join_session -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("join_session", {"session_name": session_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'join_session': {e}")
    return _envelope("join_session", r)


@mcp.tool()
def set_iris_replication(enable: bool = True) -> Dict[str, Any]:
    """set_iris_replication -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_iris_replication", {"enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_iris_replication': {e}")
    return _envelope("set_iris_replication", r)


@mcp.tool()
def set_replication_graph(replication_graph_class: str = "ReplicationGraph") -> Dict[str, Any]:
    """set_replication_graph -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_replication_graph", {"replication_graph_class": replication_graph_class})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_replication_graph': {e}")
    return _envelope("set_replication_graph", r)


@mcp.tool()
def start_bandwidth_profiling(seconds: float = 30.0) -> Dict[str, Any]:
    """start_bandwidth_profiling -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("start_bandwidth_profiling", {"seconds": float(seconds)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'start_bandwidth_profiling': {e}")
    return _envelope("start_bandwidth_profiling", r)


@mcp.tool()
def attach_network_profiler(enable: bool = True) -> Dict[str, Any]:
    """attach_network_profiler -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("attach_network_profiler", {"enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'attach_network_profiler': {e}")
    return _envelope("attach_network_profiler", r)


@mcp.tool()
def create_network_component(actor_name: str, component_class: str = "NetworkComponent") -> Dict[str, Any]:
    """create_network_component -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_network_component", {"actor_name": actor_name, "component_class": component_class})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_network_component': {e}")
    return _envelope("create_network_component", r)


@mcp.tool()
def set_blueprint_variable_replication(blueprint_path: str, variable_name: str, condition: str = "None") -> Dict[str, Any]:
    """set_blueprint_variable_replication -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(blueprint_path, "blueprint_path")
        validate_string(variable_name, "variable_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_blueprint_variable_replication", {"blueprint_path": blueprint_path, "variable_name": variable_name, "condition": condition})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_blueprint_variable_replication': {e}")
    return _envelope("set_blueprint_variable_replication", r)

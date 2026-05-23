"""Gameplay Ability System (Sub-batch R, issue #55) MCP tools (auto-generated scaffold).

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
def enable_gas_plugin() -> Dict[str, Any]:
    """enable_gas_plugin -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("enable_gas_plugin", {})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'enable_gas_plugin': {e}")
    return _envelope("enable_gas_plugin", r)


@mcp.tool()
def add_ability_system_component(actor_name: str) -> Dict[str, Any]:
    """add_ability_system_component -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_ability_system_component", {"actor_name": actor_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_ability_system_component': {e}")
    return _envelope("add_ability_system_component", r)


@mcp.tool()
def create_attribute_set(asset_path: str = "/Game/GAS", asset_name: str = "AS_New") -> Dict[str, Any]:
    """create_attribute_set -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_attribute_set", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_attribute_set': {e}")
    return _envelope("create_attribute_set", r)


@mcp.tool()
def create_gameplay_ability(asset_path: str = "/Game/GAS", asset_name: str = "GA_New") -> Dict[str, Any]:
    """create_gameplay_ability -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_gameplay_ability", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_gameplay_ability': {e}")
    return _envelope("create_gameplay_ability", r)


@mcp.tool()
def create_gameplay_effect(asset_path: str = "/Game/GAS", asset_name: str = "GE_New", duration_type: str = "Instant") -> Dict[str, Any]:
    """create_gameplay_effect -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_gameplay_effect", {"asset_path": asset_path, "asset_name": asset_name, "duration_type": duration_type})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_gameplay_effect': {e}")
    return _envelope("create_gameplay_effect", r)


@mcp.tool()
def create_gameplay_cue(asset_path: str = "/Game/GAS", asset_name: str = "GC_New") -> Dict[str, Any]:
    """create_gameplay_cue -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_gameplay_cue", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_gameplay_cue': {e}")
    return _envelope("create_gameplay_cue", r)


@mcp.tool()
def bind_ability_input(actor_name: str, ability_path: str, input_action: str) -> Dict[str, Any]:
    """bind_ability_input -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(ability_path, "ability_path")
        validate_string(input_action, "input_action")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("bind_ability_input", {"actor_name": actor_name, "ability_path": ability_path, "input_action": input_action})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'bind_ability_input': {e}")
    return _envelope("bind_ability_input", r)


@mcp.tool()
def grant_ability(actor_name: str, ability_path: str) -> Dict[str, Any]:
    """grant_ability -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(ability_path, "ability_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("grant_ability", {"actor_name": actor_name, "ability_path": ability_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'grant_ability': {e}")
    return _envelope("grant_ability", r)


@mcp.tool()
def configure_ability_activation(ability_path: str, activation_policy: str = "OnInputTriggered") -> Dict[str, Any]:
    """configure_ability_activation -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(ability_path, "ability_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_ability_activation", {"ability_path": ability_path, "activation_policy": activation_policy})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_ability_activation': {e}")
    return _envelope("configure_ability_activation", r)


@mcp.tool()
def configure_ability_cooldown(ability_path: str, cooldown_seconds: float = 1.0) -> Dict[str, Any]:
    """configure_ability_cooldown -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(ability_path, "ability_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_ability_cooldown", {"ability_path": ability_path, "cooldown_seconds": float(cooldown_seconds)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_ability_cooldown': {e}")
    return _envelope("configure_ability_cooldown", r)


@mcp.tool()
def configure_ability_cost(ability_path: str, cost_attribute: str = "Mana", amount: float = 10.0) -> Dict[str, Any]:
    """configure_ability_cost -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(ability_path, "ability_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_ability_cost", {"ability_path": ability_path, "cost_attribute": cost_attribute, "amount": float(amount)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_ability_cost': {e}")
    return _envelope("configure_ability_cost", r)


@mcp.tool()
def initialize_attribute(attribute_set_path: str, attribute: str, value: float = 100.0) -> Dict[str, Any]:
    """initialize_attribute -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(attribute_set_path, "attribute_set_path")
        validate_string(attribute, "attribute")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("initialize_attribute", {"attribute_set_path": attribute_set_path, "attribute": attribute, "value": float(value)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'initialize_attribute': {e}")
    return _envelope("initialize_attribute", r)


@mcp.tool()
def bind_attribute_change_event(attribute_set_path: str, attribute: str, handler: str = "OnAttributeChanged") -> Dict[str, Any]:
    """bind_attribute_change_event -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(attribute_set_path, "attribute_set_path")
        validate_string(attribute, "attribute")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("bind_attribute_change_event", {"attribute_set_path": attribute_set_path, "attribute": attribute, "handler": handler})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'bind_attribute_change_event': {e}")
    return _envelope("bind_attribute_change_event", r)


@mcp.tool()
def link_gameplay_tag(target: str, tag: str) -> Dict[str, Any]:
    """link_gameplay_tag -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(target, "target")
        validate_string(tag, "tag")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("link_gameplay_tag", {"target": target, "tag": tag})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'link_gameplay_tag': {e}")
    return _envelope("link_gameplay_tag", r)


@mcp.tool()
def configure_gas_replication(actor_name: str, replication_mode: str = "Mixed") -> Dict[str, Any]:
    """configure_gas_replication -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_gas_replication", {"actor_name": actor_name, "replication_mode": replication_mode})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_gas_replication': {e}")
    return _envelope("configure_gas_replication", r)


@mcp.tool()
def configure_gas_prediction(actor_name: str, enable: bool = True) -> Dict[str, Any]:
    """configure_gas_prediction -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_gas_prediction", {"actor_name": actor_name, "enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_gas_prediction': {e}")
    return _envelope("configure_gas_prediction", r)

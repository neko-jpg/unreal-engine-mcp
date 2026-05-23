"""Data Tables / Data Assets extensions (Sub-batch X, issue #54) MCP tools (auto-generated scaffold).

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
def create_row_struct(asset_path: str = "/Game/Data", asset_name: str = "FRow_New", fields: list = []) -> Dict[str, Any]:
    """create_row_struct -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_row_struct", {"asset_path": asset_path, "asset_name": asset_name, "fields": fields})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_row_struct': {e}")
    return _envelope("create_row_struct", r)


@mcp.tool()
def edit_row_struct(struct_path: str, fields: list) -> Dict[str, Any]:
    """edit_row_struct -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(struct_path, "struct_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("edit_row_struct", {"struct_path": struct_path, "fields": fields})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'edit_row_struct': {e}")
    return _envelope("edit_row_struct", r)


@mcp.tool()
def edit_data_asset_properties(data_asset_path: str, properties: list) -> Dict[str, Any]:
    """edit_data_asset_properties -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(data_asset_path, "data_asset_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("edit_data_asset_properties", {"data_asset_path": data_asset_path, "properties": properties})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'edit_data_asset_properties': {e}")
    return _envelope("edit_data_asset_properties", r)


@mcp.tool()
def import_gameplay_tag_table(csv_path: str) -> Dict[str, Any]:
    """import_gameplay_tag_table -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(csv_path, "csv_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("import_gameplay_tag_table", {"csv_path": csv_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'import_gameplay_tag_table': {e}")
    return _envelope("import_gameplay_tag_table", r)


@mcp.tool()
def generate_item_db_template(asset_path: str = "/Game/Data", asset_name: str = "DT_Items") -> Dict[str, Any]:
    """generate_item_db_template -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("generate_item_db_template", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'generate_item_db_template': {e}")
    return _envelope("generate_item_db_template", r)


@mcp.tool()
def generate_enemy_db_template(asset_path: str = "/Game/Data", asset_name: str = "DT_Enemies") -> Dict[str, Any]:
    """generate_enemy_db_template -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("generate_enemy_db_template", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'generate_enemy_db_template': {e}")
    return _envelope("generate_enemy_db_template", r)


@mcp.tool()
def generate_quest_db_template(asset_path: str = "/Game/Data", asset_name: str = "DT_Quests") -> Dict[str, Any]:
    """generate_quest_db_template -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("generate_quest_db_template", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'generate_quest_db_template': {e}")
    return _envelope("generate_quest_db_template", r)


@mcp.tool()
def generate_dialogue_db_template(asset_path: str = "/Game/Data", asset_name: str = "DT_Dialogue") -> Dict[str, Any]:
    """generate_dialogue_db_template -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("generate_dialogue_db_template", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'generate_dialogue_db_template': {e}")
    return _envelope("generate_dialogue_db_template", r)


@mcp.tool()
def create_blueprint_datatable_reference_node(blueprint_path: str, datatable_path: str, graph_name: str = "EventGraph") -> Dict[str, Any]:
    """create_blueprint_datatable_reference_node -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(blueprint_path, "blueprint_path")
        validate_string(datatable_path, "datatable_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_blueprint_datatable_reference_node", {"blueprint_path": blueprint_path, "datatable_path": datatable_path, "graph_name": graph_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_blueprint_datatable_reference_node': {e}")
    return _envelope("create_blueprint_datatable_reference_node", r)

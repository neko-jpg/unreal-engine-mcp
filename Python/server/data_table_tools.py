"""Data Table tools for the Unreal MCP server."""

import logging
from typing import Dict, Any, Optional

from server.core import mcp, get_unreal_connection
from server.validation import validate_string, ValidationError, make_validation_error_response_from_exception
from utils.responses import make_error_response

logger = logging.getLogger("UnrealMCP_Advanced")


@mcp.tool()
def create_data_table(table_path: str, row_struct_path: str) -> Dict[str, Any]:
    """Create a new DataTable asset with the specified row struct.

    table_path: Asset path (e.g., /Game/Data/MyTable)
    row_struct_path: Path to the UScriptStruct to use as row type (e.g., /Game/Structs/MyRowStruct)
    """
    try:
        validate_string(table_path, "table_path")
        validate_string(row_struct_path, "row_struct_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command(
            "create_data_table", {"table_path": table_path, "row_struct_path": row_struct_path}
        )
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"create_data_table error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def import_csv_to_data_table(table_path: str, csv_content: str) -> Dict[str, Any]:
    """Import CSV content into an existing DataTable.

    table_path: Asset path to the DataTable
    csv_content: Raw CSV string (first row = headers matching struct properties, first column = RowName)
    """
    try:
        validate_string(table_path, "table_path")
        validate_string(csv_content, "csv_content")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command(
            "import_csv_to_data_table", {"table_path": table_path, "csv_content": csv_content}
        )
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"import_csv_to_data_table error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def add_data_table_row(table_path: str, row_name: str, row_data: Dict[str, Any]) -> Dict[str, Any]:
    """Add a single row to an existing DataTable.

    table_path: Asset path to the DataTable
    row_name: Unique name for the row
    row_data: JSON object where keys are struct property names and values are the data
    """
    try:
        validate_string(table_path, "table_path")
        validate_string(row_name, "row_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command(
            "add_data_table_row",
            {"table_path": table_path, "row_name": row_name, "row_data": row_data},
        )
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"add_data_table_row error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def delete_data_table_row(table_path: str, row_name: str) -> Dict[str, Any]:
    """Delete a row from an existing DataTable.

    table_path: Asset path to the DataTable
    row_name: Name of the row to delete
    """
    try:
        validate_string(table_path, "table_path")
        validate_string(row_name, "row_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command(
            "delete_data_table_row",
            {"table_path": table_path, "row_name": row_name},
        )
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"delete_data_table_row error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def update_data_table_row(table_path: str, row_name: str, row_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing row in a DataTable (replaces the row data).

    table_path: Asset path to the DataTable
    row_name: Name of the row to update
    row_data: JSON object where keys are struct property names and values are the data
    """
    try:
        validate_string(table_path, "table_path")
        validate_string(row_name, "row_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command(
            "update_data_table_row",
            {"table_path": table_path, "row_name": row_name, "row_data": row_data},
        )
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"update_data_table_row error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def export_data_table_csv(table_path: str) -> Dict[str, Any]:
    """Export a DataTable to CSV string.

    table_path: Asset path to the DataTable
    """
    try:
        validate_string(table_path, "table_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command(
            "export_data_table_csv",
            {"table_path": table_path},
        )
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"export_data_table_csv error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def export_data_table_json(table_path: str) -> Dict[str, Any]:
    """Export a DataTable to JSON string.

    table_path: Asset path to the DataTable
    """
    try:
        validate_string(table_path, "table_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command(
            "export_data_table_json",
            {"table_path": table_path},
        )
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"export_data_table_json error: {e}")
        return make_error_response(str(e))

# W1-B Data Tables residue (UE 5.7)


@mcp.tool()
def create_data_table_from_json(
    table_path: str,
    row_struct_path: str,
    json_content: str,
) -> Dict[str, Any]:
    """Create or replace a DataTable from a JSON string (UDataTable::CreateTableFromJSONString).

    table_path: /Game path for the DataTable asset (created if it does not exist)
    row_struct_path: /Game or /Script path to the row UScriptStruct
    json_content: JSON array string mapping row names to struct field values
    """
    try:
        validate_string(table_path, "table_path")
        validate_string(row_struct_path, "row_struct_path")
        validate_string(json_content, "json_content")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command(
            "create_data_table_from_json",
            {
                "table_path": table_path,
                "row_struct_path": row_struct_path,
                "json_content": json_content,
            },
        )
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"create_data_table_from_json error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def create_curve_table(
    table_path: str,
    csv_content: Optional[str] = None,
    interp_mode: str = "Linear",
) -> Dict[str, Any]:
    """Create or update a CurveTable asset, optionally seeded from CSV.

    table_path: /Game path for the CurveTable asset (created if it does not exist)
    csv_content: Optional CSV content (each row is a curve: Name, Key0, Key1, ...)
    interp_mode: "Linear" | "Cubic" | "Constant"
    """
    try:
        validate_string(table_path, "table_path")
        validate_string(interp_mode, "interp_mode")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    if interp_mode not in {"Linear", "Cubic", "Constant"}:
        return make_error_response("interp_mode must be one of: Linear, Cubic, Constant")
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    payload: Dict[str, Any] = {"table_path": table_path, "interp_mode": interp_mode}
    if csv_content:
        payload["csv_content"] = csv_content
    try:
        response = unreal.send_command("create_curve_table", payload)
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"create_curve_table error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def create_string_table(
    table_path: str,
    namespace: Optional[str] = None,
    entries: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Create or update a UStringTable asset with optional initial entries.

    table_path: /Game path for the StringTable asset
    namespace: Optional namespace (defaults to table_path)
    entries: Optional dict of {key: localized_source_text}
    """
    try:
        validate_string(table_path, "table_path")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    if entries is not None and not isinstance(entries, dict):
        return make_error_response("entries must be a dict[str, str]")
    if entries:
        for k, v in entries.items():
            if not isinstance(k, str) or not isinstance(v, str):
                return make_error_response("entries keys and values must be strings")
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    payload: Dict[str, Any] = {"table_path": table_path}
    if namespace:
        payload["namespace"] = namespace
    if entries:
        payload["entries"] = entries
    try:
        response = unreal.send_command("create_string_table", payload)
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"create_string_table error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def set_string_table_entry(table_path: str, key: str, value: str) -> Dict[str, Any]:
    """Insert or update a single (key, value) entry in a UStringTable.

    table_path: /Game path to an existing StringTable
    key: String key
    value: Source-language localized text
    """
    try:
        validate_string(table_path, "table_path")
        validate_string(key, "key")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    if not isinstance(value, str):
        return make_error_response("value must be a string")
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command(
            "set_string_table_entry",
            {"table_path": table_path, "key": key, "value": value},
        )
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"set_string_table_entry error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def create_data_asset(asset_path: str, class_path: str) -> Dict[str, Any]:
    """Create a UDataAsset or UPrimaryDataAsset instance at the given path.

    asset_path: /Game path for the new DataAsset
    class_path: /Script or /Game path to a UDataAsset-derived UClass
    """
    try:
        validate_string(asset_path, "asset_path")
        validate_string(class_path, "class_path")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command(
            "create_data_asset",
            {"asset_path": asset_path, "class_path": class_path},
        )
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"create_data_asset error: {exc}")
        return make_error_response(str(exc))

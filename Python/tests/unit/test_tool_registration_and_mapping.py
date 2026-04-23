"""
tests/unit/test_tool_registration_and_mapping.py

L1 Python unit tests - @mcp.tool() API surface, command mapping, and parameter mapping

Covers:
- All @mcp.tool() functions register without import-time exceptions
- Public tool count matches source definitions
- Each tool calls the correct Unreal command name
- Each tool passes required parameters with correct keys
- Consistent error dictionary on connection failure
- Mutable default arguments are not shared across calls
"""

import inspect
import json
import re
from unittest.mock import patch

import pytest

import unreal_mcp_server_advanced as srv
from unreal_mcp_server_advanced import mcp, get_unreal_connection


def _collect_source_tools():
    """Detect functions wrapped by FastMCP tool decorators in the source module."""
    import pathlib
    src = pathlib.Path(srv.__file__).read_text(encoding="utf-8")
    # Allow comments and blank lines between @mcp.tool() and the next def.
    return [m.group(1) for m in re.finditer(r'@mcp\.tool\(.*?\)[\s]*?def\s+(\w+)', src, re.DOTALL)]


TOOL_FUNCS = _collect_source_tools()


class TestToolRegistration:
    def test_all_tools_registered_without_exception(self):
        """Tools should be registered correctly in FastMCP."""
        tools = mcp._tool_manager._tools
        assert len(tools) > 0, "No tools registered in FastMCP"

    def test_tool_count_matches_source_definitions(self):
        """
        Number of @mcp.tool() in source should match the number of actually registered tools.
        """
        source_tools = TOOL_FUNCS
        registered_tools = mcp._tool_manager._tools
        src_count = len(source_tools)
        reg_count = len(registered_tools)
        assert src_count == reg_count, (
            f"Mismatch: source has {src_count} tools, FastMCP registered {reg_count}"
        )


@pytest.fixture
def fake_conn(fake_conn_factory):
    """Fake connection where all commands succeed."""
    return fake_conn_factory()


class TestToolCommandMapping:
    """
    Validate that each tool passes the correct command string and parameter keys to send_command.
    """

    @pytest.mark.parametrize("tool_name, expected_cmd", [
        ("get_actors_in_level", "get_actors_in_level"),
        ("find_actors_by_name", "find_actors_by_name"),
        ("delete_actor", "delete_actor"),
        ("set_actor_transform", "set_actor_transform"),
        ("create_blueprint", "create_blueprint"),
        ("add_component_to_blueprint", "add_component_to_blueprint"),
        ("set_static_mesh_properties", "set_static_mesh_properties"),
        ("set_physics_properties", "set_physics_properties"),
        ("compile_blueprint", "compile_blueprint"),
        ("read_blueprint_content", "read_blueprint_content"),
        ("analyze_blueprint_graph", "analyze_blueprint_graph"),
        ("get_blueprint_variable_details", "get_blueprint_variable_details"),
        ("get_blueprint_function_details", "get_blueprint_function_details"),
        ("get_available_materials", "get_available_materials"),
        ("apply_material_to_actor", "apply_material_to_actor"),
        ("apply_material_to_blueprint", "apply_material_to_blueprint"),
        ("get_actor_material_info", "get_actor_material_info"),
        ("set_mesh_material_color", "set_mesh_material_color"),
    ])
    def test_tool_calls_expected_command(self, tool_name, expected_cmd, fake_conn):
        fn = getattr(srv, tool_name)
        sig = inspect.signature(fn)
        kwargs = {}
        # Fill only required arguments.
        for name, param in sig.parameters.items():
            if name == "random_string":
                kwargs[name] = ""
            elif name == "color":
                kwargs[name] = [1.0, 0.0, 0.0, 1.0]
            elif param.default is not inspect.Parameter.empty:
                kwargs[name] = param.default
            elif param.annotation == list:
                kwargs[name] = [0.0, 0.0, 0.0]
            elif param.annotation == str:
                kwargs[name] = "TestName"
            elif param.annotation == float:
                kwargs[name] = 0.0
            elif param.annotation == int:
                kwargs[name] = 0
            elif param.annotation == bool:
                kwargs[name] = True
            elif param.annotation == dict:
                kwargs[name] = {}
            else:
                kwargs[name] = "default"

        with patch.object(srv, "get_unreal_connection", return_value=fake_conn):
            fn(**kwargs)

        # Read the last command sent.
        last = fake_conn.history[-1]
        assert last["command"] == expected_cmd, (
            f"{tool_name} expected command '{expected_cmd}' but got '{last['command']}'"
        )

    def test_create_blueprint_required_params(self, fake_conn):
        with patch.object(srv, "get_unreal_connection", return_value=fake_conn):
            srv.create_blueprint(name="MyBP", parent_class="Actor")
        last = fake_conn.history[-1]
        assert last["params"]["name"] == "MyBP"
        assert last["params"]["parent_class"] == "Actor"

    def test_add_component_required_params(self, fake_conn):
        with patch.object(srv, "get_unreal_connection", return_value=fake_conn):
            srv.add_component_to_blueprint(
                blueprint_name="MyBP",
                component_type="StaticMeshComponent",
                component_name="MeshComp"
            )
        last = fake_conn.history[-1]
        assert last["params"]["blueprint_name"] == "MyBP"
        assert last["params"]["component_type"] == "StaticMeshComponent"
        assert last["params"]["component_name"] == "MeshComp"

    def test_set_physics_properties_params(self, fake_conn):
        with patch.object(srv, "get_unreal_connection", return_value=fake_conn):
            srv.set_physics_properties(
                blueprint_name="MyBP",
                component_name="MeshComp",
                simulate_physics=False,
                gravity_enabled=False,
                mass=5.0,
                linear_damping=0.1,
                angular_damping=0.2
            )
        last = fake_conn.history[-1]
        p = last["params"]
        assert p["simulate_physics"] is False
        assert p["gravity_enabled"] is False
        assert p["mass"] == 5.0
        assert p["linear_damping"] == 0.1
        assert p["angular_damping"] == 0.2


class TestConnectionFailureConsistentError:
    def test_tools_return_consistent_error_on_connection_failure(self):
        """
        Return a consistent error shape on connection failure.
        (get_unreal_connection normally returns UnrealConnection,
         so failure is simulated by patching send_command.)
        """
        from tests.conftest import FakeUnrealConnection
        real_conn = srv.get_unreal_connection()
        
        # Simulating connect failure through helper internals is heavier; patch send_command instead.
        with patch.object(real_conn, "send_command", return_value={"status": "error", "error": "conn failed"}):
            result = srv.create_blueprint("BP", "Actor")

        # Current implementation returns send_command output as-is.
        assert result.get("status") == "error" or result.get("success") is False


class TestMutableDefaultArguments:
    """
    Detect functions with mutable defaults (list/dict)
    and test that state is not shared across calls.
    Requirement note: add_component_to_blueprint(location=[], rotation=[], scale=[], component_properties={})
    """

    def add_component_to_blueprint_mutable_defaults_not_shared(self):
        from tests.conftest import FakeUnrealConnection
        fake_conn = FakeUnrealConnection()
        with patch.object(srv, "get_unreal_connection", return_value=fake_conn):
            # First call.
            r1 = srv.add_component_to_blueprint(
                blueprint_name="BP", component_type="A", component_name="C1",
                location=[1, 2, 3], rotation=[4, 5, 6]
            )
            # Second call uses default arguments.
            r2 = srv.add_component_to_blueprint(
                blueprint_name="BP", component_type="B", component_name="C2"
            )
        # r2 location/rotation should be empty lists.
        last = fake_conn.history[-1]
        assert last["params"]["location"] == []
        assert last["params"]["rotation"] == []
        assert last["params"]["scale"] == []

    def test_all_tools_no_mutable_default_pollution(self):
        """
        Scan all tool function signatures and list mutable defaults.
        If this fails, those functions should be fixed.
        """
        bad = []
        for tool_name in TOOL_FUNCS:
            obj = getattr(srv, tool_name, None)
            if obj is None:
                continue
            sig = inspect.signature(obj)
            for param_name, param in sig.parameters.items():
                default = param.default
                if default is not inspect.Parameter.empty and isinstance(default, (list, dict)):
                    # list/dict defaults are risky.
                    bad.append((tool_name, param_name, default))
        if bad:
            msg = "The following tools have mutable defaults and may cause state pollution:\n"
            for fn, pn, d in bad:
                msg += f"  {fn}(... {pn}={d!r} ...)\n"
            pytest.fail(msg)

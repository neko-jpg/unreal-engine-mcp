"""
tests/unit/test_blueprint_graph_helpers.py

L1 Python helper unit tests - Blueprint Graph helper modules

Covers:
- node_manager: add_node, add_print_node, add_event_node, add_variable_get_node, ...
- connector_manager: connect_nodes, connect_execution_pins, connect_data_pins
- event_manager: add_event_node
- variable_manager: create_variable, set_blueprint_variable_properties
- node_deleter: delete_node
- node_properties: set_node_property, add_pin, remove_pin, set_enum_type, ...
- function_manager: create_function_handler, delete_function_handler, rename_function_handler
- function_io: add_function_input_handler, add_function_output_handler

Requirements:
- Each helper uses the correct command name
- Blueprint name, node ID, pin name, and function name are sent with correct keys
- No unnecessary keys are sent when optional parameters are omitted
- Unreal-side errors are returned to callers without being swallowed
- On exceptions, at minimum return {success: False, error: ...}
"""

import json
import pytest
from unittest.mock import patch

from tests.conftest import FakeUnrealConnection

import helpers.blueprint_graph.node_manager as nm
import helpers.blueprint_graph.connector_manager as cm
import helpers.blueprint_graph.event_manager as em
import helpers.blueprint_graph.variable_manager as vm
import helpers.blueprint_graph.node_deleter as nd
import helpers.blueprint_graph.node_properties as np
import helpers.blueprint_graph.function_manager as fm
import helpers.blueprint_graph.function_io as fio


# ---------------------------------------------------------------------------
# node_manager
# ---------------------------------------------------------------------------

class TestNodeManager:
    def test_add_node_uses_correct_command(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["add_blueprint_node"] = {"success": True, "node_id": "N1"}
        nm.add_node(conn, "MyBP", "Print", {"message": "hello"})
        assert conn.history[-1]["command"] == "add_blueprint_node"
        assert conn.history[-1]["params"]["blueprint_name"] == "MyBP"
        assert conn.history[-1]["params"]["node_type"] == "Print"
        assert conn.history[-1]["params"]["node_params"]["message"] == "hello"

    def test_add_print_node_maps_params(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["add_blueprint_node"] = {"success": True, "node_id": "N2"}
        nm.add_print_node(conn, "MyBP", "Hello", 10, 20)
        p = conn.history[-1]["params"]["node_params"]
        assert p["message"] == "Hello"
        assert p["pos_x"] == 10
        assert p["pos_y"] == 20

    def test_add_event_node_maps_event_type(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["add_blueprint_node"] = {"success": True, "node_id": "N3"}
        nm.add_event_node(conn, "MyBP", "BeginPlay", 0, 0)
        p = conn.history[-1]["params"]["node_params"]
        assert p["event_type"] == "BeginPlay"

    def test_add_call_function_node_includes_optional_target_blueprint(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["add_blueprint_node"] = {"success": True, "node_id": "N4"}
        nm.add_call_function_node(conn, "MyBP", "MyFunc", 100, 200, target_blueprint="OtherBP")
        p = conn.history[-1]["params"]["node_params"]
        assert p["target_function"] == "MyFunc"
        assert p["target_blueprint"] == "OtherBP"

    def test_add_call_function_node_omits_target_blueprint_when_none(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["add_blueprint_node"] = {"success": True, "node_id": "N5"}
        nm.add_call_function_node(conn, "MyBP", "MyFunc", 0, 0, target_blueprint=None)
        p = conn.history[-1]["params"]["node_params"]
        assert "target_blueprint" not in p

    def test_add_node_returns_error_from_unreal(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["add_blueprint_node"] = {"success": False, "error": "unknown type"}
        result = nm.add_node(conn, "MyBP", "UnknownNode", {})
        assert result["success"] is False
        assert result["error"] == "unknown type"

    def test_add_node_exception_returns_safe_error(self):
        class BrokenConn:
            def send_command(self, command, params):
                raise RuntimeError("kaboom")
        result = nm.add_node(BrokenConn(), "MyBP", "Print", {})
        assert result["success"] is False
        assert "kaboom" in result["error"]


# ---------------------------------------------------------------------------
# connector_manager
# ---------------------------------------------------------------------------

class TestConnectorManager:
    def test_connect_nodes_execution_pins(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["connect_nodes"] = {"success": True, "connection": {"type": "exec"}}
        cm.connect_nodes(conn, "MyBP", "N1", "execute", "N2", "execute")
        p = conn.history[-1]["params"]
        assert p["blueprint_name"] == "MyBP"
        assert p["source_node_id"] == "N1"
        assert p["source_pin_name"] == "execute"
        assert p["target_node_id"] == "N2"
        assert p["target_pin_name"] == "execute"

    def test_connect_nodes_data_pins(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["connect_nodes"] = {"success": True}
        cm.connect_nodes(conn, "MyBP", "N1", "Value", "N2", "InString")
        p = conn.history[-1]["params"]
        assert p["source_pin_name"] == "Value"
        assert p["target_pin_name"] == "InString"

    def test_connect_nodes_optional_function_name(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["connect_nodes"] = {"success": True}
        cm.connect_nodes(conn, "MyBP", "A", "out", "B", "in", function_name="MyFunc")
        p = conn.history[-1]["params"]
        assert p["function_name"] == "MyFunc"

    def test_connect_nodes_omits_function_name_when_none(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["connect_nodes"] = {"success": True}
        cm.connect_nodes(conn, "MyBP", "A", "out", "B", "in")
        p = conn.history[-1]["params"]
        assert "function_name" not in p

    def test_connect_execution_pins_convenience(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["connect_nodes"] = {"success": True}
        cm.connect_execution_pins(conn, "MyBP", "A", "B")
        p = conn.history[-1]["params"]
        assert p["source_pin_name"] == "execute"
        assert p["target_pin_name"] == "execute"

    def test_connect_data_pins_convenience(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["connect_nodes"] = {"success": True}
        cm.connect_data_pins(conn, "MyBP", "A", "FloatVal", "B", "Input")
        p = conn.history[-1]["params"]
        assert p["source_pin_name"] == "FloatVal"
        assert p["target_pin_name"] == "Input"

    def test_connect_nodes_returns_error(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["connect_nodes"] = {"success": False, "error": "pin mismatch"}
        result = cm.connect_nodes(conn, "MyBP", "A", "out", "B", "in")
        assert result["success"] is False
        assert result["error"] == "pin mismatch"


# ---------------------------------------------------------------------------
# event_manager
# ---------------------------------------------------------------------------

class TestEventManager:
    def test_add_event_node_params(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["add_event_node"] = {"success": True, "node_id": "E1"}
        em.add_event_node(conn, "MyBP", "ReceiveTick", 50, 100)
        p = conn.history[-1]["params"]
        assert p["blueprint_name"] == "MyBP"
        assert p["event_name"] == "ReceiveTick"
        assert p["pos_x"] == 50
        assert p["pos_y"] == 100

    def test_add_event_node_returns_error(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["add_event_node"] = {"success": False, "error": "bad event"}
        result = em.add_event_node(conn, "MyBP", "NoEvent")
        assert result["success"] is False
        assert result["error"] == "bad event"


# ---------------------------------------------------------------------------
# variable_manager
# ---------------------------------------------------------------------------

class TestVariableManager:
    def test_create_variable_required_params(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["create_variable"] = {"success": True, "variable": {"name": "Health"}}
        vm.create_variable(conn, "MyBP", "Health", "float")
        p = conn.history[-1]["params"]
        assert p["blueprint_name"] == "MyBP"
        assert p["variable_name"] == "Health"
        assert p["variable_type"] == "float"

    def test_create_variable_optional_params_omitted_when_default(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["create_variable"] = {"success": True}
        vm.create_variable(conn, "MyBP", "Score", "int")
        p = conn.history[-1]["params"]
        assert "default_value" not in p
        assert "is_public" not in p
        assert "category" not in p

    def test_create_variable_includes_optional_when_provided(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["create_variable"] = {"success": True}
        vm.create_variable(conn, "MyBP", "Speed", "float", default_value=10.5, is_public=True, tooltip="Fast", category="Movement")
        p = conn.history[-1]["params"]
        assert p["default_value"] == 10.5
        assert p["is_public"] is True
        assert p["tooltip"] == "Fast"
        assert p["category"] == "Movement"

    def test_set_blueprint_variable_properties_includes_only_specified(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["set_blueprint_variable_properties"] = {"success": True}
        vm.set_blueprint_variable_properties(
            conn, "MyBP", "Health",
            is_public=True,
            default_value=100.0,
        )
        p = conn.history[-1]["params"]
        assert p["is_public"] is True
        assert p["default_value"] == 100.0
        assert "var_name" not in p
        assert "tooltip" not in p
        assert "replication_enabled" not in p

    def test_set_blueprint_variable_properties_all_options(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["set_blueprint_variable_properties"] = {"success": True}
        vm.set_blueprint_variable_properties(
            conn, "MyBP", "Health",
            var_name="NewHealth",
            var_type="int",
            is_blueprint_readable=True,
            is_blueprint_writable=True,
            is_public=True,
            is_editable_in_instance=True,
            tooltip="HP",
            category="Stats",
            default_value=100,
            expose_on_spawn=True,
            expose_to_cinematics=True,
            slider_range_min="0",
            slider_range_max="100",
            value_range_min="0",
            value_range_max="200",
            units="hp",
            bitmask=True,
            bitmask_enum="EMyEnum",
            replication_enabled=True,
            replication_condition=1,
            is_private=False,
        )
        p = conn.history[-1]["params"]
        assert p["var_name"] == "NewHealth"
        assert p["var_type"] == "int"
        assert p["is_blueprint_readable"] is True
        assert p["is_private"] is False

    def test_create_float_variable_passes_correct_type(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["create_variable"] = {"success": True}
        vm.create_float_variable(conn, "MyBP", "Speed", 10.5, True, "Move", "Movement")
        p = conn.history[-1]["params"]
        assert p["variable_type"] == "float"
        assert p["default_value"] == 10.5

    def test_create_vector_variable_null_default(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["create_variable"] = {"success": True}
        vm.create_vector_variable(conn, "MyBP", "Pos")
        p = conn.history[-1]["params"]
        assert p["variable_type"] == "vector"
        assert p["default_value"] == [0.0, 0.0, 0.0]


# ---------------------------------------------------------------------------
# node_deleter
# ---------------------------------------------------------------------------

class TestNodeDeleter:
    def test_delete_node_params(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["delete_node"] = {"success": True, "deleted_node_id": "N1"}
        nd.delete_node(conn, "MyBP", "N1")
        p = conn.history[-1]["params"]
        assert p["blueprint_name"] == "MyBP"
        assert p["node_id"] == "N1"
        assert "function_name" not in p

    def test_delete_node_with_function_name(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["delete_node"] = {"success": True}
        nd.delete_node(conn, "MyBP", "N1", function_name="MyFunc")
        p = conn.history[-1]["params"]
        assert p["function_name"] == "MyFunc"

    def test_delete_node_returns_error(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["delete_node"] = {"success": False, "error": "not found"}
        result = nd.delete_node(conn, "MyBP", "N99")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# node_properties
# ---------------------------------------------------------------------------

class TestNodeProperties:
    def test_set_node_property_legacy_params(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["set_node_property"] = {"success": True}
        np.set_node_property(conn, "MyBP", "N1", "message", "Hello")
        p = conn.history[-1]["params"]
        assert p["blueprint_name"] == "MyBP"
        assert p["node_id"] == "N1"
        assert p["property_name"] == "message"
        assert p["property_value"] == "Hello"
        assert "action" not in p

    def test_set_node_property_semantic_action(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["set_node_property"] = {"success": True}
        np.set_node_property(conn, "MyBP", "N1", "x", "y", action="add_pin", pin_type="exec")
        p = conn.history[-1]["params"]
        assert p["action"] == "add_pin"
        assert p["pin_type"] == "exec"
        assert "property_name" not in p
        assert "property_value" not in p

    def test_set_node_property_with_function_name(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["set_node_property"] = {"success": True}
        np.set_node_property(conn, "MyBP", "N1", "msg", "hi", function_name="MyFunc")
        p = conn.history[-1]["params"]
        assert p["function_name"] == "MyFunc"

    def test_add_pin_convenience(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["set_node_property"] = {"success": True}
        np.add_pin(conn, "MyBP", "N1", "ExecutionOutput", pin_name="Then_1", function_name="MyFunc")
        p = conn.history[-1]["params"]
        assert p["action"] == "add_pin"
        assert p["pin_type"] == "ExecutionOutput"
        assert p["pin_name"] == "Then_1"
        assert p["function_name"] == "MyFunc"

    def test_add_pin_omits_pin_name_when_none(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["set_node_property"] = {"success": True}
        np.add_pin(conn, "MyBP", "N1", "ArrayElement")
        p = conn.history[-1]["params"]
        assert "pin_name" not in p

    def test_remove_pin_convenience(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["set_node_property"] = {"success": True}
        np.remove_pin(conn, "MyBP", "N1", "Then_1")
        p = conn.history[-1]["params"]
        assert p["action"] == "remove_pin"
        assert p["pin_name"] == "Then_1"

    def test_set_enum_type_convenience(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["set_node_property"] = {"success": True}
        np.set_enum_type(conn, "MyBP", "N1", "EMyEnum")
        p = conn.history[-1]["params"]
        assert p["action"] == "set_enum_type"
        assert p["enum_type"] == "EMyEnum"

    def test_set_pin_type_convenience(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["set_node_property"] = {"success": True}
        np.set_pin_type(conn, "MyBP", "N1", "A", "float")
        p = conn.history[-1]["params"]
        assert p["action"] == "set_pin_type"
        assert p["pin_name"] == "A"
        assert p["new_type"] == "float"

    def test_set_function_call_with_target_class(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["set_node_property"] = {"success": True}
        np.set_function_call(conn, "MyBP", "N1", "DoThing", target_class="MyClass")
        p = conn.history[-1]["params"]
        assert p["action"] == "set_function_call"
        assert p["target_function"] == "DoThing"
        assert p["target_class"] == "MyClass"

    def test_set_function_call_without_target_class(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["set_node_property"] = {"success": True}
        np.set_function_call(conn, "MyBP", "N1", "DoThing")
        p = conn.history[-1]["params"]
        assert "target_class" not in p

    def test_set_event_type_convenience(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["set_node_property"] = {"success": True}
        np.set_event_type(conn, "MyBP", "N1", "Tick")
        p = conn.history[-1]["params"]
        assert p["action"] == "set_event_type"
        assert p["event_type"] == "Tick"

    def test_node_properties_exception_safe(self):
        class Broken:
            def send_command(self, c, p):
                raise RuntimeError("oops")
        result = np.set_node_property(Broken(), "MyBP", "N1", "x", "y")
        assert result["success"] is False
        assert "oops" in result["error"]


# ---------------------------------------------------------------------------
# function_manager
# ---------------------------------------------------------------------------

class TestFunctionManager:
    def test_create_function_handler_command(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["create_function"] = {"success": True, "function_name": "MyFunc"}
        fm.create_function_handler(conn, "MyBP", "MyFunc", "int")
        p = conn.history[-1]["params"]
        assert conn.history[-1]["command"] == "create_function"
        assert p["blueprint_name"] == "MyBP"
        assert p["function_name"] == "MyFunc"
        assert p["return_type"] == "int"

    def test_delete_function_handler_command(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["delete_function"] = {"success": True}
        fm.delete_function_handler(conn, "MyBP", "OldFunc")
        p = conn.history[-1]["params"]
        assert conn.history[-1]["command"] == "delete_function"
        assert p["blueprint_name"] == "MyBP"
        assert p["function_name"] == "OldFunc"

    def test_rename_function_handler_command(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["rename_function"] = {"success": True}
        fm.rename_function_handler(conn, "MyBP", "OldFunc", "NewFunc")
        p = conn.history[-1]["params"]
        assert conn.history[-1]["command"] == "rename_function"
        assert p["blueprint_name"] == "MyBP"
        assert p["old_function_name"] == "OldFunc"
        assert p["new_function_name"] == "NewFunc"

    def test_function_manager_exception_safe(self):
        class Broken:
            def send_command(self, c, p):
                raise Exception("fail")
        result = fm.create_function_handler(Broken(), "BP", "F")
        assert result["success"] is False
        assert "fail" in result["error"]


# ---------------------------------------------------------------------------
# function_io
# ---------------------------------------------------------------------------

class TestFunctionIO:
    def test_add_function_input_handler_params(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["add_function_input"] = {"success": True}
        fio.add_function_input_handler(conn, "MyBP", "MyFunc", "Health", "float", is_array=True)
        p = conn.history[-1]["params"]
        assert conn.history[-1]["command"] == "add_function_input"
        assert p["blueprint_name"] == "MyBP"
        assert p["function_name"] == "MyFunc"
        assert p["param_name"] == "Health"
        assert p["param_type"] == "float"
        assert p["is_array"] is True

    def test_add_function_output_handler_params(self, fake_conn_factory):
        conn = fake_conn_factory()
        conn.responses["add_function_output"] = {"success": True}
        fio.add_function_output_handler(conn, "MyBP", "MyFunc", "Result", "bool")
        p = conn.history[-1]["params"]
        assert conn.history[-1]["command"] == "add_function_output"
        assert p["param_name"] == "Result"
        assert p["param_type"] == "bool"
        assert p["is_array"] is False

    def test_function_io_exception_safe(self):
        class Broken:
            def send_command(self, c, p):
                raise ValueError("bad")
        result = fio.add_function_input_handler(Broken(), "BP", "F", "P", "int")
        assert result["success"] is False
        assert "bad" in result["error"]

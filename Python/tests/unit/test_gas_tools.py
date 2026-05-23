"""L1 unit tests for gas_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.gas_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_enable_gas_plugin_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.enable_gas_plugin()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "enable_gas_plugin"


def test_add_ability_system_component_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.add_ability_system_component("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "add_ability_system_component"


def test_create_attribute_set_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_attribute_set()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_attribute_set"


def test_create_gameplay_ability_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_gameplay_ability()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_gameplay_ability"


def test_create_gameplay_effect_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_gameplay_effect()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_gameplay_effect"


def test_create_gameplay_cue_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_gameplay_cue()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_gameplay_cue"


def test_bind_ability_input_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.bind_ability_input("actor_name_v", "ability_path_v", "input_action_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "bind_ability_input"


def test_grant_ability_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.grant_ability("actor_name_v", "ability_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "grant_ability"


def test_configure_ability_activation_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_ability_activation("ability_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_ability_activation"


def test_configure_ability_cooldown_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_ability_cooldown("ability_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_ability_cooldown"


def test_configure_ability_cost_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_ability_cost("ability_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_ability_cost"


def test_initialize_attribute_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.initialize_attribute("attribute_set_path_v", "attribute_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "initialize_attribute"


def test_bind_attribute_change_event_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.bind_attribute_change_event("attribute_set_path_v", "attribute_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "bind_attribute_change_event"


def test_link_gameplay_tag_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.link_gameplay_tag("target_v", "tag_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "link_gameplay_tag"


def test_configure_gas_replication_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_gas_replication("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_gas_replication"


def test_configure_gas_prediction_payload():
    with patch("server.gas_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_gas_prediction("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_gas_prediction"

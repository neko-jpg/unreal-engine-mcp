"""L1 unit tests for Niagara tools (Sub-batch I, issue #49).

Verifies payload serialization, command-name mapping and validation handling
for each Niagara MCP tool. No live Unreal connection required.
"""

from unittest.mock import patch, MagicMock

import pytest

import server.niagara_tools as niagara_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True, "data": {}}
    return m


class TestAssetCreation:
    def test_create_system_defaults(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            r = niagara_tools.create_niagara_system()
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "create_niagara_system"
        assert args[0][1] == {"asset_path": "/Game/Niagara", "asset_name": "NS_New"}
        assert r["success"] is True

    def test_create_emitter_overrides(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.create_niagara_emitter("/Game/Fx", "NE_Smoke")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "create_niagara_emitter"
        assert args[0][1] == {"asset_path": "/Game/Fx", "asset_name": "NE_Smoke"}

    def test_add_emitter_to_system_requires_both(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()):
            r = niagara_tools.add_emitter_to_system("", "/Game/NE_X")
        assert r.get("success") is False

    def test_add_module_default_stage(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.add_niagara_module("/Game/NE_X", "ApplyGravity")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["stage"] == "ParticleUpdate"

    def test_remove_module_payload(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.remove_niagara_module("/Game/NE_X", "ApplyGravity")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "remove_niagara_module"


class TestComponentSetters:
    def test_set_spawn_rate(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.set_niagara_spawn_rate("FX_Actor", 32.5, component_name="MyNiagara")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "set_niagara_spawn_rate"
        assert args[0][1]["spawn_rate"] == 32.5
        assert args[0][1]["component_name"] == "MyNiagara"

    def test_set_burst_int_cast(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.set_niagara_burst("FX", 12)
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["burst_count"] == 12

    def test_set_velocity_requires_three(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()):
            r = niagara_tools.set_niagara_velocity("FX", [1.0, 2.0])
        assert r.get("success") is False

    def test_set_velocity_passthrough(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.set_niagara_velocity("FX", [10.0, 0.0, 50.0])
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["velocity"] == [10.0, 0.0, 50.0]

    def test_set_color_validates(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()):
            r = niagara_tools.set_niagara_color("FX", [1.0, 0.5])
        assert r.get("success") is False

    def test_set_color_accepts_rgb(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.set_niagara_color("FX", [1.0, 0.5, 0.0])
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["color"] == [1.0, 0.5, 0.0]

    def test_set_size_payload(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.set_niagara_size("FX", 2.5)
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["size"] == 2.5

    def test_set_lifetime_payload(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.set_niagara_lifetime("FX", 3.0)
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["lifetime"] == 3.0

    def test_set_gravity_default(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.set_niagara_gravity("FX")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["gravity_z"] == -980.0


class TestRenderers:
    def test_ribbon_renderer(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.set_niagara_ribbon_renderer("FX", material_path="/Game/M_Ribbon")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "set_niagara_ribbon_renderer"
        assert args[0][1]["material_path"] == "/Game/M_Ribbon"

    def test_sprite_renderer(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.set_niagara_sprite_renderer("FX", material_path="/Game/M_Sprite")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["material_path"] == "/Game/M_Sprite"

    def test_mesh_renderer(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.set_niagara_mesh_renderer("FX", mesh_path="/Engine/Meshes/SM_Cube")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["mesh_path"] == "/Engine/Meshes/SM_Cube"


class TestSimulation:
    def test_set_gpu(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.set_niagara_gpu_simulation("/Game/NE_X", use_gpu=False)
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["use_gpu"] is False

    def test_set_collision(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.set_niagara_collision("FX", enabled=True)
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["enabled"] is True


class TestParameters:
    def test_add_user_parameter(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.add_niagara_user_parameter("/Game/NS_X", "SpeedScale", "float")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["parameter_type"] == "float"

    def test_set_user_parameter_rejects_unknown_type(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()):
            r = niagara_tools.set_niagara_user_parameter("FX", "X", "matrix", value=0)
        assert r.get("success") is False

    def test_set_user_parameter_int(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.set_niagara_user_parameter("FX", "Count", "int", value=7)
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1] == {
            "actor_name": "FX", "component_name": "",
            "parameter_name": "Count", "parameter_type": "int", "value": 7,
        }


class TestPlacement:
    def test_add_component(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.add_niagara_component("Actor", system_path="/Game/NS_Y", component_name="Fx")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "add_niagara_component"
        assert args[0][1]["system_path"] == "/Game/NS_Y"

    def test_attach(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.attach_niagara_to_actor("FX", "/Game/NS_Y")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "attach_niagara_to_actor"

    def test_bind_parameter(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.bind_niagara_parameter("FX", "User.MyMat", source_object="/Game/M_Foo")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["parameter_name"] == "User.MyMat"


class TestEffectScalability:
    def test_create_data_channel(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.create_niagara_data_channel()
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "create_niagara_data_channel"

    def test_create_effect_type(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.create_niagara_effect_type()
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "create_niagara_effect_type"

    def test_scalability(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.set_niagara_scalability("/Game/FX_EffectType", quality_level="Medium")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["quality_level"] == "Medium"

    def test_debug_console_default(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.niagara_debug_console()
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["command"] == "fx.Niagara.Debug.Hud 1"

    def test_sim_cache(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            niagara_tools.niagara_sim_cache(action="record")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][1]["action"] == "record"


class TestConnectionFailure:
    def test_no_connection_returns_error(self):
        with patch("server.niagara_tools.get_unreal_connection", return_value=None):
            r = niagara_tools.create_niagara_system()
        assert r.get("success") is False
        assert "connect" in r.get("error", "").lower()
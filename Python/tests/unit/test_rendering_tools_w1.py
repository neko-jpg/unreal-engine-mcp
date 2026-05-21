"""L1 unit tests for rendering_tools W1-7 Camera/PostProcess residue."""

from unittest.mock import patch, MagicMock

import server.rendering_tools as rendering_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True}
    return m


class TestSpawnCameraShakeSource:
    def test_minimal(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            rendering_tools.spawn_camera_shake_source("Shake01")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "spawn_camera_shake_source"
        payload = args[0][1]
        assert payload["name"] == "Shake01"
        assert payload["attenuation_inner_radius"] == 100.0
        assert payload["attenuation_outer_radius"] == 1000.0
        assert "location" not in payload
        assert "shake_class_path" not in payload

    def test_with_optional(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            rendering_tools.spawn_camera_shake_source(
                "Shake01",
                location=[10.0, 20.0, 30.0],
                shake_class_path="/Script/Engine.MatineeCameraShake",
                attenuation_inner_radius=50.0,
                attenuation_outer_radius=500.0,
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["location"] == [10.0, 20.0, 30.0]
        assert payload["shake_class_path"] == "/Script/Engine.MatineeCameraShake"
        assert payload["attenuation_inner_radius"] == 50.0

    def test_rejects_empty_name(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()):
            r = rendering_tools.spawn_camera_shake_source("")
        assert r.get("success") is False


class TestSpawnCameraRigRail:
    def test_minimal(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            rendering_tools.spawn_camera_rig_rail("Rail01")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["name"] == "Rail01"
        assert payload["current_position"] == 0.0
        assert payload["lock_orientation_to_rail"] is False

    def test_lock_orientation(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            rendering_tools.spawn_camera_rig_rail("Rail01", current_position=0.5, lock_orientation_to_rail=True)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["current_position"] == 0.5
        assert payload["lock_orientation_to_rail"] is True

    def test_rejects_out_of_range(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()):
            r = rendering_tools.spawn_camera_rig_rail("R", current_position=1.5)
        assert r.get("success") is False


class TestSpawnCameraRigCrane:
    def test_defaults(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            rendering_tools.spawn_camera_rig_crane("Crane01")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["name"] == "Crane01"
        assert payload["crane_pitch"] == 0.0
        assert payload["crane_yaw"] == 0.0
        assert payload["crane_arm_length"] == 250.0

    def test_explicit_params(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            rendering_tools.spawn_camera_rig_crane(
                "Crane01",
                crane_pitch=10.0,
                crane_yaw=45.0,
                crane_arm_length=300.0,
                lock_mount_pitch=True,
                lock_mount_yaw=True,
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["crane_pitch"] == 10.0
        assert payload["crane_arm_length"] == 300.0
        assert payload["lock_mount_pitch"] is True
        assert payload["lock_mount_yaw"] is True

    def test_rejects_negative_arm(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()):
            r = rendering_tools.spawn_camera_rig_crane("Crane01", crane_arm_length=-5.0)
        assert r.get("success") is False


class TestSetPostProcessOverride:
    def test_gi_only(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            rendering_tools.set_post_process_override("PP1", gi_method="Lumen")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"volume_name": "PP1", "gi_method": "Lumen"}

    def test_reflection_only(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            rendering_tools.set_post_process_override("PP1", reflection_method="ScreenSpace")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"volume_name": "PP1", "reflection_method": "ScreenSpace"}

    def test_both(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            rendering_tools.set_post_process_override("PP1", gi_method="Lumen", reflection_method="Lumen")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["gi_method"] == "Lumen"
        assert payload["reflection_method"] == "Lumen"

    def test_rejects_when_nothing_provided(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()):
            r = rendering_tools.set_post_process_override("PP1")
        assert r.get("success") is False

    def test_rejects_unknown_gi(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()):
            r = rendering_tools.set_post_process_override("PP1", gi_method="RayTraced")
        assert r.get("success") is False

    def test_rejects_unknown_reflection(self):
        with patch("server.rendering_tools.get_unreal_connection", return_value=_mock_conn()):
            r = rendering_tools.set_post_process_override("PP1", reflection_method="Plugin")
        assert r.get("success") is False

"""L1 unit tests for Landscape tools (Sub-batch J, issue #43)."""

from unittest.mock import patch, MagicMock

import server.landscape_tools as landscape_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True, "data": {}}
    return m


class TestCreate:
    def test_create_landscape_defaults(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            r = landscape_tools.create_landscape()
        args = ue.return_value.send_command.call_args
        assert args[0][0] == "create_landscape"
        assert args[0][1]["actor_name"] == "Landscape"
        assert args[0][1]["sections_per_component"] == 1
        assert args[0][1]["quads_per_section"] == 63
        assert r["success"] is True

    def test_create_landscape_rejects_empty(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()):
            r = landscape_tools.create_landscape(actor_name="")
        assert r.get("success") is False


class TestHeightmap:
    def test_import_heightmap_payload(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.import_landscape_heightmap("Landscape", "C:/heights.png")
        args = ue.return_value.send_command.call_args
        assert args[0][0] == "import_landscape_heightmap"
        assert args[0][1]["heightmap_path"] == "C:/heights.png"

    def test_export_heightmap_payload(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.export_landscape_heightmap("L", "/out.png")
        args = ue.return_value.send_command.call_args
        assert args[0][0] == "export_landscape_heightmap"


class TestSculptBrushes:
    def test_sculpt_default_location(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.landscape_sculpt("L")
        args = ue.return_value.send_command.call_args
        assert args[0][1]["location_xy"] == [0.0, 0.0]
        assert args[0][1]["brush_radius"] == 100.0

    def test_smooth_iterations(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.landscape_smooth("L", iterations=4)
        args = ue.return_value.send_command.call_args
        assert args[0][1]["iterations"] == 4

    def test_flatten_height(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.landscape_flatten("L", target_height=250.0)
        args = ue.return_value.send_command.call_args
        assert args[0][1]["target_height"] == 250.0

    def test_ramp_payload(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.landscape_ramp("L", [0,0], [100,0], ramp_height=64.0)
        args = ue.return_value.send_command.call_args
        assert args[0][1]["start_xy"] == [0,0]

    def test_erosion(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.landscape_erosion("L", iterations=5, strength=0.25)
        args = ue.return_value.send_command.call_args
        assert args[0][1]["strength"] == 0.25

    def test_noise(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.landscape_noise("L")
        args = ue.return_value.send_command.call_args
        assert args[0][1]["amplitude"] == 100.0


class TestPaint:
    def test_create_paint_layer(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.create_landscape_paint_layer("L", "Grass")
        args = ue.return_value.send_command.call_args
        assert args[0][0] == "create_landscape_paint_layer"
        assert args[0][1]["layer_name"] == "Grass"

    def test_set_layer_blend(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.set_landscape_layer_blend("L", "Grass", weight=0.75)
        args = ue.return_value.send_command.call_args
        assert args[0][1]["weight"] == 0.75

    def test_apply_material(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.apply_landscape_material("L", "/Game/Materials/M_Land")
        args = ue.return_value.send_command.call_args
        assert args[0][0] == "apply_landscape_material"


class TestAux:
    def test_grass_output(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.set_landscape_grass_output("L", grass_type_path="/Game/Grass")
        args = ue.return_value.send_command.call_args
        assert args[0][1]["grass_type_path"] == "/Game/Grass"

    def test_collision_toggle(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.set_landscape_collision("L", enable=False)
        args = ue.return_value.send_command.call_args
        assert args[0][1]["enable"] is False

    def test_hole(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.add_landscape_hole("L", [100,200], radius=50.0)
        args = ue.return_value.send_command.call_args
        assert args[0][1]["radius"] == 50.0

    def test_spline(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.add_landscape_spline("L", [[0,0],[1,1]])
        args = ue.return_value.send_command.call_args
        assert args[0][0] == "add_landscape_spline"

    def test_road_spline(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.add_road_spline("L", [[0,0],[1,1]], road_mesh_path="/Game/Road")
        args = ue.return_value.send_command.call_args
        assert args[0][1]["road_mesh_path"] == "/Game/Road"

    def test_carve_river(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.carve_river_terrain("L")
        args = ue.return_value.send_command.call_args
        assert args[0][0] == "carve_river_terrain"

    def test_rvt(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.attach_landscape_rvt("L", "/Game/RVT_Albedo")
        args = ue.return_value.send_command.call_args
        assert args[0][1]["rvt_asset_path"] == "/Game/RVT_Albedo"

    def test_nanite(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.set_landscape_nanite("L")
        args = ue.return_value.send_command.call_args
        assert args[0][1]["enable"] is True

    def test_world_partition(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.set_landscape_world_partition("L", grid_size=8)
        args = ue.return_value.send_command.call_args
        assert args[0][1]["grid_size"] == 8

    def test_size(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.set_landscape_size("L", 1024, 1024)
        args = ue.return_value.send_command.call_args
        assert args[0][1]["width_quads"] == 1024

    def test_section_component(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            landscape_tools.set_landscape_section_component("L", sections_per_component=2, quads_per_section=31)
        args = ue.return_value.send_command.call_args
        assert args[0][1]["quads_per_section"] == 31


class TestFailures:
    def test_no_connection(self):
        with patch("server.landscape_tools.get_unreal_connection", return_value=None):
            r = landscape_tools.create_landscape()
        assert r.get("success") is False
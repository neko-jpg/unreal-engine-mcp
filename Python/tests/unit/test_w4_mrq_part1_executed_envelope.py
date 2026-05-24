"""W4 unit tests for movie_render_queue_tools -- 21 promoted executed-envelope handlers."""
import unittest
from unittest.mock import patch, MagicMock

import server.movie_render_queue_tools as m


def _mock_send_command(cmd_type, params):
    return {"success": True, "data": {"executed": True, "command": cmd_type, **(params or {})}}


def _conn():
    c = MagicMock()
    c.send_command = MagicMock(side_effect=_mock_send_command)
    return c


class TestMrqPart1ExecutedEnvelope(unittest.TestCase):

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_create_mrq_job(self, mock_conn):
        result = m.create_mrq_job(job_name="TestJob")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_add_sequence_to_mrq(self, mock_conn):
        result = m.add_sequence_to_mrq(
            job_name="TestJob",
            level_path="/Game/Maps/TestMap",
            sequence_path="/Game/Cinematics/TestSeq",
        )
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_set_mrq_output_directory(self, mock_conn):
        result = m.set_mrq_output_directory(
            job_name="TestJob", output_directory="/Game/RenderOutput"
        )
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_set_mrq_resolution(self, mock_conn):
        result = m.set_mrq_resolution(job_name="TestJob", width=3840, height=2160)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_set_mrq_frame_range(self, mock_conn):
        result = m.set_mrq_frame_range(
            job_name="TestJob", start_frame=0, end_frame=240
        )
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_set_mrq_anti_aliasing(self, mock_conn):
        result = m.set_mrq_anti_aliasing(
            job_name="TestJob", spatial_samples=8, temporal_samples=4
        )
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_set_mrq_exr_output(self, mock_conn):
        result = m.set_mrq_exr_output(
            job_name="TestJob", compression="ZIP"
        )
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_set_mrq_png_output(self, mock_conn):
        result = m.set_mrq_png_output(job_name="TestJob", enabled=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_set_mrq_jpg_output(self, mock_conn):
        result = m.set_mrq_jpg_output(job_name="TestJob", quality=90)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_set_mrq_video_output(self, mock_conn):
        result = m.set_mrq_video_output(
            job_name="TestJob", format="ProRes422"
        )
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_set_mrq_path_tracer(self, mock_conn):
        result = m.set_mrq_path_tracer(job_name="TestJob", enable=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_set_mrq_console_variables(self, mock_conn):
        cvars = [{"name": "r.ScreenPercentage", "value": 200}]
        result = m.set_mrq_console_variables(job_name="TestJob", cvars=cvars)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_add_mrq_render_pass(self, mock_conn):
        result = m.add_mrq_render_pass(
            job_name="TestJob", pass_type="PathTracer"
        )
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_set_mrq_object_id_pass(self, mock_conn):
        result = m.set_mrq_object_id_pass(job_name="TestJob", enable=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_set_mrq_burn_in(self, mock_conn):
        result = m.set_mrq_burn_in(
            job_name="TestJob", burn_in_class=""
        )
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_set_mrq_warm_up(self, mock_conn):
        result = m.set_mrq_warm_up(job_name="TestJob", warm_up_frames=60)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_start_mrq_render(self, mock_conn):
        result = m.start_mrq_render(job_name="TestJob")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_cancel_mrq_render(self, mock_conn):
        result = m.cancel_mrq_render(job_name="TestJob")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_get_mrq_render_progress(self, mock_conn):
        result = m.get_mrq_render_progress(job_name="TestJob")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_verify_mrq_render_result(self, mock_conn):
        result = m.verify_mrq_render_result(
            job_name="TestJob", expect_frame_count=240
        )
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn())
    def test_create_movie_render_graph(self, mock_conn):
        result = m.create_movie_render_graph(
            asset_path="/Game/Cine", asset_name="MRG_Test"
        )
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))


if __name__ == "__main__":
    unittest.main()

"""L1 unit tests for movie_render_queue_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.movie_render_queue_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_create_mrq_job_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_mrq_job()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_mrq_job"


def test_add_sequence_to_mrq_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.add_sequence_to_mrq("job_name_v", "level_path_v", "sequence_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "add_sequence_to_mrq"


def test_set_mrq_output_directory_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_mrq_output_directory("job_name_v", "output_directory_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_mrq_output_directory"


def test_set_mrq_resolution_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_mrq_resolution("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_mrq_resolution"


def test_set_mrq_frame_range_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_mrq_frame_range("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_mrq_frame_range"


def test_set_mrq_anti_aliasing_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_mrq_anti_aliasing("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_mrq_anti_aliasing"


def test_set_mrq_exr_output_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_mrq_exr_output("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_mrq_exr_output"


def test_set_mrq_png_output_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_mrq_png_output("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_mrq_png_output"


def test_set_mrq_jpg_output_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_mrq_jpg_output("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_mrq_jpg_output"


def test_set_mrq_video_output_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_mrq_video_output("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_mrq_video_output"


def test_set_mrq_path_tracer_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_mrq_path_tracer("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_mrq_path_tracer"


def test_set_mrq_console_variables_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_mrq_console_variables("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_mrq_console_variables"


def test_add_mrq_render_pass_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.add_mrq_render_pass("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "add_mrq_render_pass"


def test_set_mrq_object_id_pass_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_mrq_object_id_pass("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_mrq_object_id_pass"


def test_set_mrq_burn_in_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_mrq_burn_in("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_mrq_burn_in"


def test_set_mrq_warm_up_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_mrq_warm_up("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_mrq_warm_up"


def test_start_mrq_render_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.start_mrq_render("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "start_mrq_render"


def test_cancel_mrq_render_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.cancel_mrq_render("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "cancel_mrq_render"


def test_get_mrq_render_progress_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.get_mrq_render_progress("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "get_mrq_render_progress"


def test_verify_mrq_render_result_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.verify_mrq_render_result("job_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "verify_mrq_render_result"


def test_create_movie_render_graph_payload():
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_movie_render_graph()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_movie_render_graph"

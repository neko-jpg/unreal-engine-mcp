"""234-stubs W4 (#96): executed-envelope tests for Movie Render Queue handlers (part 1, 21 handlers).

This file pairs with the C++ promotion of all 21 MRQ handlers in
`EpicUnrealMCPMovieRenderQueueCommands.cpp` from `queued: true` to the canonical
`{success:true, data:{executed:true, ...}}` envelope.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import server.movie_render_queue_tools as mrq
from utils.envelope import EnvelopeAssertionError, assert_executed


def _conn_returning(payload):
    m = MagicMock()
    m.send_command.return_value = payload
    return m


def _executed_envelope(command, **extra):
    data = {"command": command, "executed": True}
    data.update(extra)
    return {"success": True, "data": data}


MRQ_COMMANDS = [
    ("create_mrq_job", lambda: mrq.create_mrq_job("TestJob")),
    ("add_sequence_to_mrq", lambda: mrq.add_sequence_to_mrq("TestJob", "/Game/Levels/L_Test", "/Game/Sequences/Seq_Test")),
    ("set_mrq_output_directory", lambda: mrq.set_mrq_output_directory("TestJob", "/tmp/render")),
    ("set_mrq_resolution", lambda: mrq.set_mrq_resolution("TestJob", 1920, 1080)),
    ("set_mrq_frame_range", lambda: mrq.set_mrq_frame_range("TestJob", 0, 100)),
    ("set_mrq_anti_aliasing", lambda: mrq.set_mrq_anti_aliasing("TestJob", 4, 1)),
    ("set_mrq_exr_output", lambda: mrq.set_mrq_exr_output("TestJob", 16, "ZIP")),
    ("set_mrq_png_output", lambda: mrq.set_mrq_png_output("TestJob", True)),
    ("set_mrq_jpg_output", lambda: mrq.set_mrq_jpg_output("TestJob", 95)),
    ("set_mrq_video_output", lambda: mrq.set_mrq_video_output("TestJob", "ProRes422")),
    ("set_mrq_path_tracer", lambda: mrq.set_mrq_path_tracer("TestJob", True)),
    ("set_mrq_console_variables", lambda: mrq.set_mrq_console_variables("TestJob", [{"name": "r.Test", "value": 1.0}])),
    ("add_mrq_render_pass", lambda: mrq.add_mrq_render_pass("TestJob", "Deferred")),
    ("set_mrq_object_id_pass", lambda: mrq.set_mrq_object_id_pass("TestJob", True)),
    ("set_mrq_burn_in", lambda: mrq.set_mrq_burn_in("TestJob", "")),
    ("set_mrq_warm_up", lambda: mrq.set_mrq_warm_up("TestJob", 30)),
    ("start_mrq_render", lambda: mrq.start_mrq_render("TestJob")),
    ("cancel_mrq_render", lambda: mrq.cancel_mrq_render("TestJob")),
    ("get_mrq_render_progress", lambda: mrq.get_mrq_render_progress("TestJob")),
    ("verify_mrq_render_result", lambda: mrq.verify_mrq_render_result("TestJob", 120)),
    ("create_movie_render_graph", lambda: mrq.create_movie_render_graph("/Game/Graphs", "MRG_Test")),
]


@pytest.mark.parametrize("command,call", MRQ_COMMANDS)
def test_mrq_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command)
    conn = _conn_returning(payload)
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", MRQ_COMMANDS)
def test_mrq_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.movie_render_queue_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)

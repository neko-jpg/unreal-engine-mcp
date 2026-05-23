"""L1 unit tests for packaging_extension_tools (Sub-batch AA, issue #56).

Each test (a) confirms the right C++ command name is dispatched, (b) checks
that ``None`` fields are dropped from the payload so the C++ side can detect
"unspecified" vs "set to false / empty list", and (c) verifies the wrapper
returns the success envelope unchanged.
"""
from unittest.mock import MagicMock, patch

import server.packaging_extension_tools as m


def _conn(payload=None):
    c = MagicMock()
    c.send_command.return_value = {
        "success": True,
        "data": payload or {"available": True},
    }
    return c


# ---------------------------------------------------------------------------
# set_live_coding_mode
# ---------------------------------------------------------------------------

def test_set_live_coding_mode_default_compile_now_false():
    with patch("server.packaging_extension_tools.get_unreal_connection",
               return_value=_conn({"available": True, "enabled": True})) as ue:
        out = m.set_live_coding_mode(enable=True)
    call = ue.return_value.send_command.call_args
    assert call[0][0] == "set_live_coding_mode"
    assert call[0][1] == {"enable": True, "compile_now": False}
    assert out["success"] is True
    assert out["data"]["available"] is True


def test_set_live_coding_mode_compile_now_true():
    with patch("server.packaging_extension_tools.get_unreal_connection",
               return_value=_conn({"available": True, "compile_triggered": True})) as ue:
        m.set_live_coding_mode(enable=False, compile_now=True)
    call = ue.return_value.send_command.call_args
    assert call[0][1] == {"enable": False, "compile_now": True}


def test_set_live_coding_mode_surfaces_available_false_envelope():
    """Live Coding unavailable on non-Windows / non-Editor must NOT be an error."""
    with patch("server.packaging_extension_tools.get_unreal_connection",
               return_value=_conn({"available": False, "hint": "no LC"})):
        out = m.set_live_coding_mode(enable=True)
    assert out["success"] is True
    assert out["data"]["available"] is False


# ---------------------------------------------------------------------------
# set_pak_iostore_settings
# ---------------------------------------------------------------------------

def test_set_pak_iostore_settings_drops_none_fields():
    with patch("server.packaging_extension_tools.get_unreal_connection",
               return_value=_conn({"any_changed": True})) as ue:
        m.set_pak_iostore_settings(use_pak=True, compressed=False)
    call = ue.return_value.send_command.call_args
    assert call[0][0] == "set_pak_iostore_settings"
    payload = call[0][1]
    assert payload == {"use_pak": True, "compressed": False}
    # The two unset fields must NOT be present (so C++ can detect "unspecified")
    assert "use_iostore" not in payload
    assert "generate_no_chunks" not in payload


def test_set_pak_iostore_settings_all_unset_is_empty_payload():
    with patch("server.packaging_extension_tools.get_unreal_connection",
               return_value=_conn({"any_changed": False})) as ue:
        m.set_pak_iostore_settings()
    payload = ue.return_value.send_command.call_args[0][1]
    assert payload == {}


# ---------------------------------------------------------------------------
# set_chunk_settings
# ---------------------------------------------------------------------------

def test_set_chunk_settings_all_provided():
    with patch("server.packaging_extension_tools.get_unreal_connection",
               return_value=_conn({"any_changed": True})) as ue:
        m.set_chunk_settings(
            generate_chunks=True,
            chunk_hard_references_only=False,
            has_chunk_assignment_rules=True,
        )
    call = ue.return_value.send_command.call_args
    assert call[0][0] == "set_chunk_settings"
    assert call[0][1] == {
        "generate_chunks": True,
        "chunk_hard_references_only": False,
        "has_chunk_assignment_rules": True,
    }


def test_set_chunk_settings_partial_payload():
    with patch("server.packaging_extension_tools.get_unreal_connection",
               return_value=_conn({"any_changed": True})) as ue:
        m.set_chunk_settings(generate_chunks=True)
    assert ue.return_value.send_command.call_args[0][1] == {"generate_chunks": True}


# ---------------------------------------------------------------------------
# set_localization_cook_settings
# ---------------------------------------------------------------------------

def test_set_localization_cook_settings_full_payload():
    with patch("server.packaging_extension_tools.get_unreal_connection",
               return_value=_conn({"any_changed": True})) as ue:
        m.set_localization_cook_settings(
            cultures_to_stage=["en", "ja", "fr"],
            cook_all=False,
            localization_targets_to_chunk=["Game"],
        )
    call = ue.return_value.send_command.call_args
    assert call[0][0] == "set_localization_cook_settings"
    assert call[0][1] == {
        "cultures_to_stage": ["en", "ja", "fr"],
        "cook_all": False,
        "localization_targets_to_chunk": ["Game"],
    }


def test_set_localization_cook_settings_empty_list_is_passed_through():
    """Empty list != None; the C++ side treats empty as 'clear the list'."""
    with patch("server.packaging_extension_tools.get_unreal_connection",
               return_value=_conn({"any_changed": True})) as ue:
        m.set_localization_cook_settings(cultures_to_stage=[])
    payload = ue.return_value.send_command.call_args[0][1]
    assert payload == {"cultures_to_stage": []}


# ---------------------------------------------------------------------------
# set_crash_reporter_settings
# ---------------------------------------------------------------------------

def test_set_crash_reporter_settings_email_only():
    with patch("server.packaging_extension_tools.get_unreal_connection",
               return_value=_conn({"any_changed": True})) as ue:
        m.set_crash_reporter_settings(crash_report_client_email="qa@example.com")
    call = ue.return_value.send_command.call_args
    assert call[0][0] == "set_crash_reporter_settings"
    assert call[0][1] == {"crash_report_client_email": "qa@example.com"}


def test_set_crash_reporter_settings_full_payload():
    with patch("server.packaging_extension_tools.get_unreal_connection",
               return_value=_conn({"any_changed": True})) as ue:
        m.set_crash_reporter_settings(
            crash_report_client_email="qa@example.com",
            send_unattended_bug_reports=True,
            send_usage_data=False,
        )
    call = ue.return_value.send_command.call_args
    assert call[0][1] == {
        "crash_report_client_email": "qa@example.com",
        "send_unattended_bug_reports": True,
        "send_usage_data": False,
    }


def test_set_crash_reporter_settings_all_unset_is_empty_payload():
    with patch("server.packaging_extension_tools.get_unreal_connection",
               return_value=_conn({"any_changed": False})) as ue:
        m.set_crash_reporter_settings()
    assert ue.return_value.send_command.call_args[0][1] == {}


# ---------------------------------------------------------------------------
# Error path: connection failure surfaces an error envelope rather than raising
# ---------------------------------------------------------------------------

def test_connection_failure_returns_error_envelope():
    with patch("server.packaging_extension_tools.get_unreal_connection", return_value=None):
        out = m.set_pak_iostore_settings(use_pak=True)
    assert out["success"] is False
    assert "Failed to connect" in out.get("error", "")


def test_send_exception_returns_error_envelope():
    bad = MagicMock()
    bad.send_command.side_effect = RuntimeError("kaboom")
    with patch("server.packaging_extension_tools.get_unreal_connection", return_value=bad):
        out = m.set_crash_reporter_settings(send_usage_data=True)
    assert out["success"] is False
    assert "kaboom" in out.get("error", "")


def test_unreal_failure_envelope_is_propagated():
    """When C++ returns success=False, the wrapper must convert it to an
    error envelope (mirrors every other sub-batch wrapper)."""
    failing = MagicMock()
    failing.send_command.return_value = {"success": False, "error": "settings missing"}
    with patch("server.packaging_extension_tools.get_unreal_connection", return_value=failing):
        out = m.set_chunk_settings(generate_chunks=True)
    assert out["success"] is False
    assert "settings missing" in out.get("error", "")
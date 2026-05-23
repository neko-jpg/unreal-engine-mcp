"""234-stubs Wave 1 (#81, #82) regression tests: executed-envelope path.

These tests assert that the Python wrappers for the 9 Wave-1 handlers that
were `queued`-only at Wave 0 now propagate the new
`{success:true, data:{executed:true, ...}}` envelope verbatim, and that
`utils.envelope.assert_executed` accepts them.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from utils.envelope import EnvelopeAssertionError, assert_executed

# Niagara handlers (#82)
import server.niagara_tools as niagara_tools
# Material handlers (#81)
import server.material_graph_tools as material_graph_tools


def _executed_envelope(extra=None):
    data = {"executed": True}
    if extra:
        data.update(extra)
    return {"success": True, "data": data}


def _patch(target_module, attr_path="get_unreal_connection"):
    """Patch get_unreal_connection on the given server module to return an MC mock."""
    conn = MagicMock()
    conn.send_command.return_value = _executed_envelope()
    return patch(f"{target_module.__name__}.{attr_path}", return_value=conn), conn


# ---------------------------------------------------------------- #81 Material

class TestMaterialExecutedEnvelope:
    def test_create_substrate_material_returns_executed(self):
        with _patch(material_graph_tools)[0] as mock_ue:
            mock_ue.return_value.send_command.return_value = _executed_envelope(
                {"asset_path": "/Game/M_NewSubstrate.M_NewSubstrate",
                 "asset_name": "M_NewSubstrate",
                 "front_material_wired": True,
                 "needs_substrate": True})
            r = material_graph_tools.create_substrate_material("M_NewSubstrate")
        assert_executed(r, "create_substrate_material")

    def test_create_layered_material_returns_executed(self):
        with _patch(material_graph_tools)[0] as mock_ue:
            mock_ue.return_value.send_command.return_value = _executed_envelope(
                {"asset_path": "/Game/M_NewLayered.M_NewLayered",
                 "asset_name": "M_NewLayered",
                 "material_attributes_wired": True,
                 "layer_count": 0,
                 "blend_count": 0,
                 "layer_paths": [],
                 "blend_paths": []})
            r = material_graph_tools.create_layered_material("M_NewLayered")
        assert_executed(r, "create_layered_material")

    def test_legacy_queued_envelope_is_rejected(self):
        """If a regression sneaks a queued-only envelope back in, this fails loudly."""
        with _patch(material_graph_tools)[0] as mock_ue:
            mock_ue.return_value.send_command.return_value = {
                "success": True, "data": {"queued": True, "asset_path": "/Game/M_X.M_X"}
            }
            r = material_graph_tools.create_substrate_material("M_X")
        with pytest.raises(EnvelopeAssertionError):
            assert_executed(r, "create_substrate_material")


# ---------------------------------------------------------------- #82 Niagara

class TestNiagaraExecutedEnvelope:
    @pytest.mark.parametrize("tool_name,callable_factory", [
        ("add_emitter_to_system",
         lambda: niagara_tools.add_emitter_to_system("/Game/Niagara/NS_A.NS_A",
                                                    "/Game/Niagara/NE_A.NE_A")),
        ("add_niagara_module",
         lambda: niagara_tools.add_niagara_module("/Game/Niagara/NE_A.NE_A",
                                                  "ApplyGravity",
                                                  stage="ParticleUpdate")),
        ("remove_niagara_module",
         lambda: niagara_tools.remove_niagara_module("/Game/Niagara/NE_A.NE_A",
                                                    "ApplyGravity")),
        ("add_niagara_user_parameter",
         lambda: niagara_tools.add_niagara_user_parameter(
             "/Game/Niagara/NS_A.NS_A", "User.SpawnRate", "float")),
        ("create_niagara_data_channel",
         lambda: niagara_tools.create_niagara_data_channel("/Game/Niagara", "NDC_X")),
        ("set_niagara_scalability",
         lambda: niagara_tools.set_niagara_scalability(
             "/Game/Niagara/FX_T.FX_T", "Cinematic")),
        ("niagara_sim_cache",
         lambda: niagara_tools.niagara_sim_cache(action="create",
                                                 asset_path="/Game/Niagara",
                                                 asset_name="NSC_X")),
    ])
    def test_handler_returns_executed_envelope(self, tool_name, callable_factory):
        conn = MagicMock()
        conn.send_command.return_value = _executed_envelope({"echo": tool_name})
        with patch("server.niagara_tools.get_unreal_connection", return_value=conn):
            r = callable_factory()
        # The Python wrappers route through _envelope() which surfaces success
        # transparently; the `executed: true` flag must reach the caller.
        assert_executed(r, tool_name)

"""Guard tests for procedural scene tool validation."""

from server.scene_procedural_tools import scene_wfc_to_semantic_layout


def test_wfc_semantic_layout_rejects_empty_tile_asset_map():
    res = scene_wfc_to_semantic_layout(
        scene_id="test",
        width=1,
        height=1,
        tiles=[{"id": "rock", "weight": 1.0}],
        constraints=[],
        tile_asset_map=None,
    )
    assert res["success"] is False
    assert "tile_asset_map cannot be empty" in res["error"]

"""E2E test for the WFC → Semantic Layout → HISM proxy pipeline (issue #27).

Pipeline under test:
    scene_create_wfc_grid (Rust)
        →  scene_wfc_to_semantic_layout (scene-syncd upserts tagged entities)
        →  scene_show_wfc_proxy (Unreal native HISM proxies)

The whole pipeline requires scene-syncd + SurrealDB + a running Unreal
Editor. The test skips gracefully when any of those is missing.
"""

from __future__ import annotations

import os
import sys
import time

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "..", "Python"))


@pytest.mark.requires_unreal
class TestWfcSemanticHismPipeline:
    """3x3 WFC grid → semantic layout entities → HISM proxy in Unreal."""

    def test_full_pipeline(self, scene_syncd_available, unreal_available, isolated_scene):
        if not scene_syncd_available:
            pytest.skip("scene-syncd not available")
        if not unreal_available:
            pytest.skip("Unreal MCP bridge not available")

        # Import here so a missing Python dep cannot crash collection.
        from server import scene_procedural_tools as spt

        scene_id = isolated_scene
        tiles = [{"id": "T_A", "weight": 1.0}, {"id": "T_B", "weight": 1.0}]
        constraints = [
            {"left": "T_A", "right": "T_A", "direction": "east"},
            {"left": "T_A", "right": "T_B", "direction": "east"},
            {"left": "T_B", "right": "T_A", "direction": "east"},
            {"left": "T_B", "right": "T_B", "direction": "east"},
            {"left": "T_A", "right": "T_A", "direction": "south"},
            {"left": "T_A", "right": "T_B", "direction": "south"},
            {"left": "T_B", "right": "T_A", "direction": "south"},
            {"left": "T_B", "right": "T_B", "direction": "south"},
        ]
        tile_asset_map = {
            "T_A": "/Engine/BasicShapes/Cube.Cube",
            "T_B": "/Engine/BasicShapes/Cube.Cube",
        }
        cell_size = {"x": 200.0, "y": 200.0}
        origin = {"x": 0.0, "y": 0.0, "z": 0.0}

        # Step 1: WFC -> Semantic Layout upserts into the test scene database.
        semantic = spt.scene_wfc_to_semantic_layout(
            scene_id=scene_id,
            width=3,
            height=3,
            tiles=tiles,
            constraints=constraints,
            tile_asset_map=tile_asset_map,
            seed=42,
            cell_size=cell_size,
            origin=origin,
            group_id_prefix="e2e_wfc",
            desired_name_prefix="E2EWfcTile",
        )
        assert semantic.get("success") is True, semantic
        data = semantic.get("data") or semantic
        assert data.get("upserted_count", 0) >= 9, data

        # Allow scene-syncd to persist.
        time.sleep(0.3)

        # Step 2: Show WFC proxy spawns HISM proxies in Unreal.
        proxy = spt.scene_show_wfc_proxy(scene_id=scene_id, proxy_name_prefix="e2e_wfc")
        assert proxy.get("success") is True, proxy
        proxy_data = proxy.get("data") or proxy
        proxies = proxy_data.get("proxies", [])
        assert len(proxies) > 0, proxy_data

        # Step 3: Verify the per-tile world position contract.
        per_tile = proxy_data.get("tile_id_actors") or {}
        for tile_id, actors in per_tile.items():
            for actor in actors:
                location = actor.get("location") or {}
                grid_x = int(actor.get("grid_x", 0))
                grid_y = int(actor.get("grid_y", 0))
                expected_x = origin["x"] + grid_x * cell_size["x"]
                expected_y = origin["y"] + grid_y * cell_size["y"]
                if "x" in location and "y" in location:
                    assert abs(location["x"] - expected_x) < 1e-3, (tile_id, location, expected_x)
                    assert abs(location["y"] - expected_y) < 1e-3, (tile_id, location, expected_y)
"""Unit tests for vision/visual_metrics and vision_analyzer (simplified)."""

from __future__ import annotations

import pytest

from server.vision.visual_metrics import VisualMetrics, compute_metrics_for_path
from server.vision.vision_analyzer import NullProvider, VlmRubric


@pytest.fixture
def synth_image(tmp_path):
    PIL = pytest.importorskip("PIL.Image")
    import numpy as np
    arr = np.zeros((64, 96, 3), dtype="uint8")
    # half left = warm, half right = blue
    arr[:, :48, 0] = 200; arr[:, :48, 1] = 130; arr[:, :48, 2] = 60
    arr[:, 48:, 0] = 40;  arr[:, 48:, 1] = 80;  arr[:, 48:, 2] = 200
    p = tmp_path / "synth.png"
    PIL.fromarray(arr).save(p)
    return str(p)


def test_visual_metrics_decisive_for_warm_vs_cool(synth_image):
    metrics = compute_metrics_for_path(synth_image)
    assert metrics.width == 96
    assert metrics.height == 64
    # warm side has higher r, cool side has higher b, mean blue_cyan_bias > 0
    assert metrics.warm_bias != 0
    assert metrics.luminance_mean > 0


def test_visual_metrics_are_deterministic(synth_image):
    m1 = compute_metrics_for_path(synth_image).to_dict()
    m2 = compute_metrics_for_path(synth_image).to_dict()
    assert m1 == m2


def test_visual_metrics_missing_image_returns_note(tmp_path):
    metrics = compute_metrics_for_path(str(tmp_path / "nope.png"))
    assert metrics.note == "missing"


def test_null_provider_returns_disabled_note():
    provider = NullProvider()
    rubric = VlmRubric(rubric_id="test", goal="dummy", criteria=["x"])
    result = provider.analyze("nonexistent.png", rubric)
    assert result.provider == "null"
    assert "disabled" in result.notes


def test_scene_preview_returns_mcp_image_content(monkeypatch, synth_image):
    """scene_preview should return images as MCP ImageContent (base64 PNG)."""
    import server.dialog_tools as dt
    import server.vision.screenshot as screenshot_mod

    class _FakeClient:
        def call_scene_syncd(self, path, payload):
            mapping = {
                "/objects/list": {"objects": []},
                "/entities/list": {"entities": []},
                "/components/list": {"components": []},
                "/assets/list": {"assets": []},
                "/snapshots/list": {"snapshots": []},
                "/operations/recent": {"operations": []},
            }
            return {"success": True, "data": mapping.get(path, {})}

    class _Shot:
        success = True
        path = synth_image
        elapsed_ms = 0.1
        warnings = []

    monkeypatch.setattr(dt, "_summarizer_client", lambda: _FakeClient())
    monkeypatch.setattr(screenshot_mod, "take_via_focus", lambda request: _Shot())

    res = dt.scene_preview(scene_id="preview_test")
    assert res["success"] is True
    assert res["vlm_status"] == "delegated_to_agent"
    # MCP ImageContent format
    assert len(res["images"]) == 1
    img = res["images"][0]
    assert img["type"] == "image"
    assert img["mime_type"] == "image/png"
    assert img["label"] == "single"
    assert len(img["data"]) > 100  # base64 PNG should be substantial
    # Deterministic metrics
    assert res["per_image_metrics"][0]["sha1"]


def test_scene_preview_single_sets_camera_from_scene_bounds(monkeypatch, synth_image):
    import server.dialog_tools as dt
    import server.vision.screenshot as screenshot_mod

    class _FakeClient:
        def call_scene_syncd(self, path, payload):
            mapping = {
                "/objects/list": {
                    "objects": [
                        {
                            "mcp_id": "cave_floor",
                            "desired_name": "Cave_Floor",
                            "metadata": {"kind": "floor"},
                            "tags": ["cave"],
                            "transform": {
                                "location": {"x": 0, "y": 0, "z": 0},
                                "scale": {"x": 20, "y": 20, "z": 0.3},
                            },
                            "bounds": {"min": [-1000, -1000, 0], "max": [1000, 1000, 400]},
                        }
                    ]
                },
                "/entities/list": {"entities": []},
                "/components/list": {"components": []},
                "/assets/list": {"assets": []},
                "/snapshots/list": {"snapshots": []},
                "/operations/recent": {"operations": []},
            }
            return {"success": True, "data": mapping.get(path, {})}

    class _Shot:
        success = True
        path = synth_image
        elapsed_ms = 0.1
        warnings = []

    requests = []
    monkeypatch.setattr(dt, "_summarizer_client", lambda: _FakeClient())

    def _take(request):
        requests.append(request)
        return _Shot()

    monkeypatch.setattr(screenshot_mod, "take_via_focus", _take)

    res = dt.scene_preview(scene_id="preview_test", target="cave", batch="single")
    assert res["success"] is True
    assert res["cave_metrics"]["is_box_cave"] is False
    assert res["cave_metrics"]["entrance_count"] >= 1
    assert len(requests) == 1
    assert requests[0].camera_location is not None
    assert requests[0].camera_location == pytest.approx((0.0, -257.09, 210.0), abs=0.01)
    assert requests[0].camera_look_at == pytest.approx((0.0, 799.84, 190.0), abs=0.01)


def test_scene_preview_surround_returns_six_images(monkeypatch, synth_image):
    """batch='surround' should return 6 images."""
    import server.dialog_tools as dt
    import server.vision.screenshot as screenshot_mod

    class _FakeClient:
        def call_scene_syncd(self, path, payload):
            return {"success": True, "data": {k: [] for k in ["objects", "entities", "components", "assets", "snapshots", "operations"]}}

    class _Shot:
        success = True
        path = synth_image
        elapsed_ms = 0.1
        warnings = []

    monkeypatch.setattr(dt, "_summarizer_client", lambda: _FakeClient())
    monkeypatch.setattr(screenshot_mod, "take_via_focus", lambda request: _Shot())

    res = dt.scene_preview(scene_id="surround_test", batch="surround")
    assert res["success"] is True
    assert len(res["images"]) == 6
    assert len(res["camera_views"]) == 6
    assert all("camera_location" in view for view in res["camera_views"])
    labels = [img["label"] for img in res["images"]]
    assert "front" in labels
    assert "bird_eye" in labels


def test_scene_preview_orbit_returns_eight_camera_views(monkeypatch, synth_image):
    """batch='orbit' should compute eight target-relative camera views."""
    import server.dialog_tools as dt
    import server.vision.screenshot as screenshot_mod

    class _FakeClient:
        def call_scene_syncd(self, path, payload):
            mapping = {
                "/objects/list": {
                    "objects": [
                        {
                            "mcp_id": "hero",
                            "name": "hero",
                            "kind": "character",
                            "tags": ["target"],
                            "transform": {"location": [100, 200, 50]},
                        }
                    ]
                },
                "/entities/list": {"entities": []},
                "/components/list": {"components": []},
                "/assets/list": {"assets": []},
                "/snapshots/list": {"snapshots": []},
                "/operations/recent": {"operations": []},
            }
            return {"success": True, "data": mapping.get(path, {})}

    class _Shot:
        success = True
        path = synth_image
        elapsed_ms = 0.1
        warnings = []

    requests = []
    monkeypatch.setattr(dt, "_summarizer_client", lambda: _FakeClient())

    def _take(request):
        requests.append(request)
        return _Shot()

    monkeypatch.setattr(screenshot_mod, "take_via_focus", _take)

    res = dt.scene_preview(scene_id="orbit_test", target="hero", batch="orbit")
    assert res["success"] is True
    assert len(res["images"]) == 8
    assert [img["label"] for img in res["images"]] == [f"orbit_{i}" for i in range(8)]
    assert len(requests) == 8
    assert all(req.camera_location for req in requests)
    assert all(req.camera_look_at == (100.0, 200.0, 50.0) for req in requests)


def test_take_via_focus_sets_camera_before_screenshot(tmp_path):
    """Explicit camera views should use set_camera_position before capture."""
    from server.vision.screenshot import ScreenshotRequest, take_via_focus

    out = tmp_path / "shot.png"

    class _FakeUE:
        def __init__(self):
            self.calls = []

        def send_command(self, command, params):
            self.calls.append((command, params))
            if command == "take_screenshot":
                out.write_bytes(b"not-a-real-png")
                return {"success": True, "path": str(out)}
            return {"success": True}

    fake = _FakeUE()
    result = take_via_focus(
        ScreenshotRequest(
            scene_id="camera_test",
            camera_location=[1, 2, 3],
            camera_rotation=[4, 5, 6],
            camera_look_at=[7, 8, 9],
        ),
        unreal_connection=fake,
    )
    assert result.success is True
    assert fake.calls[0] == (
        "set_camera_position",
        {"location": [1, 2, 3], "rotation": [4, 5, 6], "look_at": [7, 8, 9]},
    )
    assert fake.calls[1][0] == "take_screenshot"


def test_scene_preview_no_vlm_api_calls(monkeypatch, synth_image):
    """scene_preview must NOT import or call any VLM API provider."""
    import server.dialog_tools as dt
    import server.vision.screenshot as screenshot_mod

    class _FakeClient:
        def call_scene_syncd(self, path, payload):
            return {"success": True, "data": {k: [] for k in ["objects", "entities", "components", "assets", "snapshots", "operations"]}}

    class _Shot:
        success = True
        path = synth_image
        elapsed_ms = 0.1
        warnings = []

    monkeypatch.setattr(dt, "_summarizer_client", lambda: _FakeClient())
    monkeypatch.setattr(screenshot_mod, "take_via_focus", lambda request: _Shot())

    res = dt.scene_preview(scene_id="no_vlm_test")
    assert res["success"] is True
    assert res["vlm_status"] == "delegated_to_agent"
    # No VLM result in response
    assert "vlm" not in res or "result" not in res.get("vlm", {})

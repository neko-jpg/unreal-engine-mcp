"""Screenshot helper.

Uses `viewport_action` mode=focus_actor when a target is provided, then runs
the existing `take_screenshot` command. Returns the absolute screenshot path
plus diagnostic info.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger("UnrealMCP_Advanced")

DEFAULT_SCREENSHOT_DIR = os.environ.get(
    "MCP_SCREENSHOT_DIR",
    str(Path.cwd() / "artifacts" / "screenshots"),
)


@dataclass
class ScreenshotRequest:
    scene_id: str = "main"
    target_actor: Optional[str] = None
    width: int = 1280
    height: int = 720
    camera_location: Optional[Sequence[float]] = None
    camera_rotation: Optional[Sequence[float]] = None
    camera_look_at: Optional[Sequence[float]] = None
    label: Optional[str] = None


@dataclass
class ScreenshotResult:
    success: bool
    path: Optional[str] = None
    elapsed_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


def _ensure_dir(path: str) -> str:
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def take_via_focus(
    request: ScreenshotRequest,
    *,
    unreal_connection: Any = None,
) -> ScreenshotResult:
    """Focus on optional target, then capture a screenshot."""
    start = time.perf_counter()
    out_dir = _ensure_dir(DEFAULT_SCREENSHOT_DIR)
    out_name = f"scene_{request.scene_id}_{int(time.time() * 1000)}.png"
    out_path = str(Path(out_dir) / out_name)

    if unreal_connection is None:
        from server.core import get_unreal_connection
        unreal_connection = get_unreal_connection()

    result = ScreenshotResult(success=False)
    if request.camera_location:
        camera_params: Dict[str, Any] = {
            "location": list(request.camera_location),
        }
        if request.camera_rotation:
            camera_params["rotation"] = list(request.camera_rotation)
        if request.camera_look_at:
            camera_params["look_at"] = list(request.camera_look_at)
        camera_resp = unreal_connection.send_command("set_camera_position", camera_params)
        if isinstance(camera_resp, dict) and not camera_resp.get("success", True):
            result.warnings.append(f"set_camera_position failed: {camera_resp.get('error')}")
        time.sleep(0.15)
    elif request.target_actor:
        focus_resp = unreal_connection.send_command(
            "viewport_action",
            {"action": "focus_actor", "actor_name": request.target_actor},
        )
        if isinstance(focus_resp, dict) and not focus_resp.get("success", True):
            result.warnings.append(f"focus_actor failed: {focus_resp.get('error')}")
        time.sleep(0.15)

    shot_resp = unreal_connection.send_command(
        "take_screenshot",
        {"output_path": out_path, "width": request.width, "height": request.height},
    )
    result.raw = shot_resp if isinstance(shot_resp, dict) else {}
    if isinstance(shot_resp, dict) and shot_resp.get("success", True):
        # Some UE handlers respect output_path, others write to a default
        # Saved/Screenshots dir. Honour an absolute path in the response.
        returned = shot_resp.get("path") or shot_resp.get("file") or out_path
        result.success = True
        result.path = str(returned)
    else:
        result.warnings.append(
            f"take_screenshot failed: {(shot_resp or {}).get('error', 'unknown')}"
        )
    result.elapsed_ms = (time.perf_counter() - start) * 1000.0
    return result

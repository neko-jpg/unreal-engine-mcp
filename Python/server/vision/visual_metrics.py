"""Decisive visual metrics for React-for-UE v3.0.

These are deterministic numerical proxies for mood evaluation, computed
without any LLM call. Pillow + NumPy provide the heavy lifting; if Pillow
is not available the helpers degrade to a pure-Python stub that returns
zeros.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger("UnrealMCP_Advanced")


@dataclass
class VisualMetrics:
    image_path: str
    width: int = 0
    height: int = 0
    luminance_mean: float = 0.0
    luminance_stddev: float = 0.0
    contrast: float = 0.0
    blue_cyan_bias: float = 0.0
    warm_bias: float = 0.0
    bright_pixel_ratio: float = 0.0
    dominant_color: Optional[List[int]] = None
    sha1: Optional[str] = None
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _hash_file(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _import_pillow():
    try:
        from PIL import Image  # type: ignore
        import numpy as np  # type: ignore
        return Image, np
    except Exception:  # pragma: no cover
        return None, None


def compute_metrics_for_path(path: str) -> VisualMetrics:
    """Compute decisive visual metrics for a single image."""
    if not path or not Path(path).exists():
        return VisualMetrics(image_path=path or "", note="missing")

    metrics = VisualMetrics(image_path=path)
    metrics.sha1 = _hash_file(path)

    Image, np = _import_pillow()
    if Image is None or np is None:
        metrics.note = "pillow_or_numpy_missing"
        return metrics

    with Image.open(path) as im:
        im = im.convert("RGB")
        metrics.width, metrics.height = im.size
        arr = np.asarray(im, dtype=np.float32) / 255.0

    r = arr[..., 0]
    g = arr[..., 1]
    b = arr[..., 2]

    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    metrics.luminance_mean = float(luminance.mean())
    metrics.luminance_stddev = float(luminance.std())
    metrics.contrast = float(luminance.max() - luminance.min())

    metrics.blue_cyan_bias = float(((b + g) * 0.5 - r).mean())
    metrics.warm_bias = float((r - b).mean())
    metrics.bright_pixel_ratio = float((luminance > 0.85).mean())

    # Coarse dominant colour: 4x4 mean tile then majority bucket
    h = max(1, metrics.height // 4)
    w = max(1, metrics.width // 4)
    arr_small = (arr[:h * 4, :w * 4].reshape(4, h, 4, w, 3).mean(axis=(1, 3)) * 255).astype("uint8")
    flat = arr_small.reshape(-1, 3)
    counts: Dict[tuple, int] = {}
    for row in flat:
        key = tuple(int(x // 32) for x in row)
        counts[key] = counts.get(key, 0) + 1
    if counts:
        best = max(counts.items(), key=lambda kv: kv[1])[0]
        metrics.dominant_color = [int(c * 32) for c in best]
    return metrics

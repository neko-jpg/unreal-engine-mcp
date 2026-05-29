"""Pure-Python SDF evaluation and coarse mesh extraction."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from server.generation.geometry import Aabb3, Vector3, vec3
from server.generation.mesh_payload import ProceduralMeshPayload


# --- 3D Value Noise (hash-based, no external dependencies) ---

def _hash3(ix: int, iy: int, iz: int) -> float:
    """Deterministic pseudo-random float in [-1, 1] from integer coordinates."""
    n = ix * 73856093 ^ iy * 19349663 ^ iz * 83492791
    n = (n ^ (n >> 13)) * 1274126177
    n = n ^ (n >> 16)
    return ((n & 0x7FFFFFFF) / 0x7FFFFFFF) * 2.0 - 1.0


def _lerp(a: float, b: float, t: float) -> float:
    return a + t * (b - a)


def _smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def value_noise_3d(x: float, y: float, z: float) -> float:
    """3D value noise with trilinear interpolation."""
    ix = math.floor(x)
    iy = math.floor(y)
    iz = math.floor(z)
    fx = _smoothstep(x - ix)
    fy = _smoothstep(y - iy)
    fz = _smoothstep(z - iz)

    c000 = _hash3(ix, iy, iz)
    c100 = _hash3(ix + 1, iy, iz)
    c010 = _hash3(ix, iy + 1, iz)
    c110 = _hash3(ix + 1, iy + 1, iz)
    c001 = _hash3(ix, iy, iz + 1)
    c101 = _hash3(ix + 1, iy, iz + 1)
    c011 = _hash3(ix, iy + 1, iz + 1)
    c111 = _hash3(ix + 1, iy + 1, iz + 1)

    return _lerp(
        _lerp(_lerp(c000, c100, fx), _lerp(c010, c110, fx), fy),
        _lerp(_lerp(c001, c101, fx), _lerp(c011, c111, fx), fy),
        fz,
    )


def fbm_3d(x: float, y: float, z: float, octaves: int = 6, lacunarity: float = 2.0, gain: float = 0.5) -> float:
    """Fractal Brownian motion using 3D value noise."""
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    norm = 0.0
    for _ in range(max(1, min(octaves, 10))):
        value += amplitude * value_noise_3d(x * frequency, y * frequency, z * frequency)
        norm += amplitude
        amplitude *= gain
        frequency *= lacunarity
    return value / max(norm, 1e-6)


def _sub(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a: Vector3, s: float) -> Vector3:
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a: Vector3, b: Vector3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _length(a: Vector3) -> float:
    return math.sqrt(max(_dot(a, a), 0.0))


def _normalize(a: Vector3, fallback: Vector3 = (0.0, 0.0, 1.0)) -> Vector3:
    length = _length(a)
    if length <= 1.0e-9:
        return fallback
    return (a[0] / length, a[1] / length, a[2] / length)


def smooth_min(a: float, b: float, k: float) -> float:
    if k <= 0.0:
        return min(a, b)
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * k * 0.25


def evaluate_sdf(node: Mapping[str, Any], point: Sequence[float]) -> float:
    """Evaluate Rust-compatible SDF JSON at ``point``."""
    p = vec3(point)
    node_type = str(node.get("type", "sphere")).lower()
    if node_type in {"primitive"} and isinstance(node.get("primitive"), Mapping):
        return evaluate_sdf(node["primitive"], p)
    if node_type == "sphere":
        center = vec3(node.get("center", (0.0, 0.0, 0.0)))
        return _length(_sub(p, center)) - float(node.get("radius", 100.0))
    if node_type == "box":
        bmin = vec3(node.get("min", (-100.0, -100.0, -100.0)))
        bmax = vec3(node.get("max", (100.0, 100.0, 100.0)))
        center = _mul(_add(bmin, bmax), 0.5)
        half = _mul(_sub(bmax, bmin), 0.5)
        d = (abs(p[0] - center[0]) - half[0], abs(p[1] - center[1]) - half[1], abs(p[2] - center[2]) - half[2])
        outside = _length((max(d[0], 0.0), max(d[1], 0.0), max(d[2], 0.0)))
        inside = min(max(d[0], max(d[1], d[2])), 0.0)
        return outside + inside
    if node_type == "capsule":
        start = vec3(node.get("start", (0.0, 0.0, 0.0)))
        end = vec3(node.get("end", (100.0, 0.0, 0.0)))
        radius = float(node.get("radius", 30.0))
        pa = _sub(p, start)
        ba = _sub(end, start)
        denom = _dot(ba, ba)
        h = min(max(_dot(pa, ba) / denom, 0.0), 1.0) if denom > 0.0 else 0.0
        return _length(_sub(pa, _mul(ba, h))) - radius
    if node_type == "torus":
        center = vec3(node.get("center", (0.0, 0.0, 0.0)))
        q = _sub(p, center)
        major = float(node.get("major_radius", 100.0))
        minor = float(node.get("minor_radius", 30.0))
        return math.hypot(math.hypot(q[0], q[1]) - major, q[2]) - minor
    if node_type == "gyroid":
        f = float(node.get("frequency", 1.0))
        thickness = float(node.get("thickness", 0.1))
        g = (
            math.sin(p[0] * f) * math.sin(p[1] * f) * math.cos(p[2] * f)
            + math.sin(p[2] * f) * math.sin(p[0] * f) * math.cos(p[1] * f)
            + math.sin(p[1] * f) * math.sin(p[2] * f) * math.cos(p[0] * f)
        )
        return abs(g) - thickness
    if node_type == "scherk":
        f = float(node.get("frequency", 1.0))
        return abs(math.sinh(p[0] * f) * math.sinh(p[1] * f) - math.sin(p[2] * f)) - 0.1
    if node_type == "union":
        children = [child for child in node.get("children", []) if isinstance(child, Mapping)]
        if not children:
            return 1.0e9
        k = float(node.get("smoothness", 0.0))
        value = evaluate_sdf(children[0], p)
        for child in children[1:]:
            value = smooth_min(value, evaluate_sdf(child, p), k)
        return value
    if node_type == "difference":
        a = node.get("a") or node.get("left") or node.get("child")
        b = node.get("b") or node.get("right") or node.get("subtract")
        if isinstance(a, Mapping) and isinstance(b, Mapping):
            return max(evaluate_sdf(a, p), -evaluate_sdf(b, p))
        return 1.0e9
    if node_type == "intersection":
        children = [child for child in node.get("children", []) if isinstance(child, Mapping)]
        if not children:
            return 1.0e9
        return max(evaluate_sdf(child, p) for child in children)
    if node_type == "domain_warp":
        child = node.get("child")
        if not isinstance(child, Mapping):
            return 1.0e9
        amplitude = float(node.get("amplitude", 0.0))
        frequency = float(node.get("frequency", 0.01))
        warp = (
            math.sin(p[1] * frequency + 11.17) * math.cos(p[2] * frequency + 3.31) * amplitude,
            math.sin(p[2] * frequency + 17.71) * math.cos(p[0] * frequency + 5.37) * amplitude,
            math.sin(p[0] * frequency + 23.13) * math.cos(p[1] * frequency + 7.91) * amplitude,
        )
        return evaluate_sdf(child, _add(p, warp))
    if node_type == "displace":
        child = node.get("child")
        if not isinstance(child, Mapping):
            return 1.0e9
        amp = float(node.get("amplitude", 10.0))
        freq = float(node.get("frequency", 0.01))
        octaves = int(node.get("octaves", 4))
        decay = float(node.get("amplitude_decay", 0.5))
        noise = fbm_3d(p[0] * freq, p[1] * freq, p[2] * freq, octaves=octaves, gain=decay)
        return evaluate_sdf(child, p) + amp * noise
    return 1.0e9


def estimate_sdf_bounds(node: Mapping[str, Any], default: Optional[Aabb3] = None) -> Aabb3:
    node_type = str(node.get("type", "")).lower()
    if node_type == "sphere":
        center = vec3(node.get("center", (0.0, 0.0, 0.0)))
        radius = float(node.get("radius", 100.0))
        return Aabb3((center[0] - radius, center[1] - radius, center[2] - radius), (center[0] + radius, center[1] + radius, center[2] + radius))
    if node_type == "box":
        return Aabb3(vec3(node.get("min", (-100.0, -100.0, -100.0))), vec3(node.get("max", (100.0, 100.0, 100.0))))
    if node_type == "capsule":
        start = vec3(node.get("start", (0.0, 0.0, 0.0)))
        end = vec3(node.get("end", (100.0, 0.0, 0.0)))
        radius = float(node.get("radius", 30.0))
        return Aabb3(
            (min(start[0], end[0]) - radius, min(start[1], end[1]) - radius, min(start[2], end[2]) - radius),
            (max(start[0], end[0]) + radius, max(start[1], end[1]) + radius, max(start[2], end[2]) + radius),
        )
    children = []
    if isinstance(node.get("child"), Mapping):
        children.append(node["child"])
    children.extend(child for child in node.get("children", []) if isinstance(child, Mapping))
    bounds = [estimate_sdf_bounds(child, default) for child in children]
    if bounds:
        merged = bounds[0]
        for item in bounds[1:]:
            merged = merged.merge(item)
        if node_type == "domain_warp":
            return merged.expand(float(node.get("amplitude", 0.0)))
        if node_type == "displace":
            return merged.expand(abs(float(node.get("amplitude", 0.0))))
        return merged
    return default or Aabb3((-500.0, -500.0, -500.0), (500.0, 500.0, 500.0))


def sdf_normal(node: Mapping[str, Any], point: Sequence[float], epsilon: float) -> Vector3:
    p = vec3(point)
    ex = evaluate_sdf(node, (p[0] + epsilon, p[1], p[2])) - evaluate_sdf(node, (p[0] - epsilon, p[1], p[2]))
    ey = evaluate_sdf(node, (p[0], p[1] + epsilon, p[2])) - evaluate_sdf(node, (p[0], p[1] - epsilon, p[2]))
    ez = evaluate_sdf(node, (p[0], p[1], p[2] + epsilon)) - evaluate_sdf(node, (p[0], p[1], p[2] - epsilon))
    return _normalize((ex, ey, ez))


def sdf_to_voxel_surface_mesh(
    sdf_tree: Mapping[str, Any],
    bounds: Optional[Aabb3] = None,
    resolution: int = 32,
    mcp_id: str = "sdf_mesh",
    request_id: int = 1,
) -> ProceduralMeshPayload:
    """Extract a coarse manifold-ish voxel surface mesh from an SDF.

    This is intentionally pure Python and deterministic. For production smooth
    meshes, use the UE/scene-syncd marching-cubes path; this path gives Python
    a local generator implementation for validation and migration work.
    """
    res = max(4, min(int(resolution), 96))
    if bounds is None:
        estimated = estimate_sdf_bounds(sdf_tree)
        max_extent = max(estimated.size())
        b = estimated.expand(max(max_extent * 0.08, 0.01))
    else:
        b = bounds
    size = b.size()
    step = (size[0] / res, size[1] / res, size[2] / res)
    inside = set()
    for ix in range(res):
        x = b.min[0] + (ix + 0.5) * step[0]
        for iy in range(res):
            y = b.min[1] + (iy + 0.5) * step[1]
            for iz in range(res):
                z = b.min[2] + (iz + 0.5) * step[2]
                if evaluate_sdf(sdf_tree, (x, y, z)) < 0.0:
                    inside.add((ix, iy, iz))

    positions: List[List[float]] = []
    normals: List[List[float]] = []
    indices: List[int] = []
    faces = [
        ((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]),
        ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
        ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]),
        ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
        ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
        ((0, 0, -1), [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)]),
    ]
    for cell in inside:
        ix, iy, iz = cell
        base_origin = (b.min[0] + ix * step[0], b.min[1] + iy * step[1], b.min[2] + iz * step[2])
        for direction, corners in faces:
            neighbor = (ix + direction[0], iy + direction[1], iz + direction[2])
            if neighbor in inside:
                continue
            base = len(positions)
            for corner in corners:
                point = [
                    base_origin[0] + corner[0] * step[0],
                    base_origin[1] + corner[1] * step[1],
                    base_origin[2] + corner[2] * step[2],
                ]
                positions.append(point)
                normals.append(list(sdf_normal(sdf_tree, point, min(step) * 0.35)))
            indices.extend([base, base + 1, base + 2, base, base + 2, base + 3])
    return ProceduralMeshPayload(mcp_id=mcp_id, request_id=request_id, positions=positions, normals=normals, indices=indices)

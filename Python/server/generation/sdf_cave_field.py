"""SDF cave field construction.

The Unreal bridge consumes a JSON-like SDF tree; these helpers build that tree
from the cave graph and parameter updates used by the refinement loop.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from server.generation.sdf import evaluate_sdf, estimate_sdf_bounds, sdf_normal, vec3


def _vec(value: Iterable[float]) -> list[float]:
    vals = list(value)
    return [float(vals[0]), float(vals[1]), float(vals[2])]


def build_cave_sdf_from_graph(graph: Mapping[str, Any], params: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Build a smooth union of chamber spheres and tunnel capsules."""
    params = params or {}
    nodes = {node["node_id"]: node for node in graph.get("nodes", []) if isinstance(node, Mapping)}
    children: list[Dict[str, Any]] = []
    chamber_scale = float(params.get("chamber_radius_scale", 1.0))
    tunnel_scale = float(params.get("tunnel_radius_scale", 1.0))

    for node in nodes.values():
        radius = float(node.get("radius", 260.0)) * chamber_scale
        children.append(
            {
                "type": "sphere",
                "center": _vec(node.get("position", (0.0, 0.0, 0.0))),
                "radius": radius,
                "metadata": {"node_id": node.get("node_id"), "kind": node.get("kind")},
            }
        )

    for edge in graph.get("edges", []):
        if not isinstance(edge, Mapping):
            continue
        start = nodes.get(str(edge.get("start")))
        end = nodes.get(str(edge.get("end")))
        if not start or not end:
            continue
        children.append(
            {
                "type": "capsule",
                "start": _vec(start.get("position", (0.0, 0.0, 0.0))),
                "end": _vec(end.get("position", (0.0, 0.0, 0.0))),
                "radius": float(edge.get("radius", 160.0)) * tunnel_scale,
                "metadata": {"kind": edge.get("kind")},
            }
        )

    return {
        "type": "union",
        "smoothness": float(params.get("smoothness", 110.0)),
        "children": children,
    }


def apply_domain_warp(phi: Mapping[str, Any], params: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Wrap an SDF tree in domain warp to destroy box-like regularity."""
    params = params or {}
    strength = float(params.get("sdf_warp_strength", params.get("domain_warp", 0.55)))
    if strength <= 0.0:
        return dict(phi)
    return {
        "type": "domain_warp",
        "child": dict(phi),
        "amplitude": float(params.get("warp_amplitude", 40.0 + strength * 150.0)),
        "frequency": float(params.get("noise_frequency", 0.004 + strength * 0.003)),
        "octaves": int(params.get("warp_octaves", 3)),
    }


def apply_fractal_roughness(phi: Mapping[str, Any], params: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Add fBM roughness as a displacement layer."""
    params = params or {}
    octaves = int(params.get("noise_octaves", params.get("ceiling_noise_octaves", 6)))
    return {
        "type": "displace",
        "child": dict(phi),
        "noise": "fbm",
        "amplitude": float(params.get("roughness_amplitude", 35.0 + float(params.get("roughness", 0.72)) * 75.0)),
        "frequency": float(params.get("noise_frequency", 0.012)),
        "octaves": max(1, min(octaves, 10)),
        "amplitude_decay": float(params.get("amplitude_decay", 0.52)),
    }


def extract_mesh_marching_cubes(
    phi: Mapping[str, Any],
    resolution: int = 48,
    bounds: "Aabb3 | None" = None,
) -> Dict[str, Any]:
    """Extract a triangle mesh from an SDF tree via Marching Cubes.

    Returns a dict with ``vertices``, ``normals``, ``triangles`` (index list),
    and metadata.  The algorithm evaluates the SDF on a regular grid, classifies
    each cell, and produces interpolated triangles using the standard 256-case
    lookup tables.
    """
    from server.generation.geometry import Aabb3

    resolution = max(8, min(int(resolution), 128))

    if bounds is None:
        estimated = estimate_sdf_bounds(phi)
        max_extent = max(estimated.size())
        b = estimated.expand(max(max_extent * 0.08, 0.01))
    else:
        b = bounds

    size = b.size()
    step = (size[0] / resolution, size[1] / resolution, size[2] / resolution)
    origin = b.min

    # Sample SDF on the grid (one extra row/col for marching cubes edges)
    nx = resolution + 1
    ny = resolution + 1
    nz = resolution + 1
    grid: list[list[list[float]]] = []
    for iz in range(nz):
        plane: list[list[float]] = []
        for iy in range(ny):
            row: list[float] = []
            for ix in range(nx):
                x = origin[0] + ix * step[0]
                y = origin[1] + iy * step[1]
                z = origin[2] + iz * step[2]
                row.append(evaluate_sdf(phi, (x, y, z)))
            plane.append(row)
        grid.append(plane)

    # March through each cell
    vertices: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    triangles: list[tuple[int, int, int]] = []

    for iz in range(resolution):
        for iy in range(resolution):
            for ix in range(resolution):
                # Corner positions
                corners = [
                    (origin[0] + ix * step[0], origin[1] + iy * step[1], origin[2] + iz * step[2]),
                    (origin[0] + (ix + 1) * step[0], origin[1] + iy * step[1], origin[2] + iz * step[2]),
                    (origin[0] + (ix + 1) * step[0], origin[1] + (iy + 1) * step[1], origin[2] + iz * step[2]),
                    (origin[0] + ix * step[0], origin[1] + (iy + 1) * step[1], origin[2] + iz * step[2]),
                    (origin[0] + ix * step[0], origin[1] + iy * step[1], origin[2] + (iz + 1) * step[2]),
                    (origin[0] + (ix + 1) * step[0], origin[1] + iy * step[1], origin[2] + (iz + 1) * step[2]),
                    (origin[0] + (ix + 1) * step[0], origin[1] + (iy + 1) * step[1], origin[2] + (iz + 1) * step[2]),
                    (origin[0] + ix * step[0], origin[1] + (iy + 1) * step[1], origin[2] + (iz + 1) * step[2]),
                ]
                values = [
                    grid[iz][iy][ix],
                    grid[iz][iy][ix + 1],
                    grid[iz][iy + 1][ix + 1],
                    grid[iz][iy + 1][ix],
                    grid[iz + 1][iy][ix],
                    grid[iz + 1][iy][ix + 1],
                    grid[iz + 1][iy + 1][ix + 1],
                    grid[iz + 1][iy + 1][ix],
                ]

                # Classify corners
                cube_index = 0
                for i in range(8):
                    if values[i] < 0.0:
                        cube_index |= 1 << i

                if cube_index == 0 or cube_index == 255:
                    continue

                # Edge table: which edges are intersected
                edge_bits = _MC_EDGE_TABLE[cube_index]
                edge_verts: list[tuple[float, float, float] | None] = [None] * 12

                # Edge vertex indices pairs
                edge_pairs = [
                    (0, 1), (1, 2), (2, 3), (3, 0),
                    (4, 5), (5, 6), (6, 7), (7, 4),
                    (0, 4), (1, 5), (2, 6), (3, 7),
                ]

                for edge_idx in range(12):
                    if edge_bits & (1 << edge_idx):
                        a, b_idx = edge_pairs[edge_idx]
                        va, vb = values[a], values[b_idx]
                        t = va / (va - vb) if abs(va - vb) > 1e-12 else 0.5
                        t = max(0.0, min(1.0, t))
                        pa, pb = corners[a], corners[b_idx]
                        edge_verts[edge_idx] = (
                            pa[0] + t * (pb[0] - pa[0]),
                            pa[1] + t * (pb[1] - pa[1]),
                            pa[2] + t * (pb[2] - pa[2]),
                        )

                # Triangle table
                tri_data = _MC_TRI_TABLE[cube_index]
                for i in range(0, len(tri_data), 3):
                    e0, e1, e2 = tri_data[i], tri_data[i + 1], tri_data[i + 2]
                    if e0 < 0:
                        break
                    v0 = edge_verts[e0]
                    v1 = edge_verts[e1]
                    v2 = edge_verts[e2]
                    if v0 is None or v1 is None or v2 is None:
                        continue
                    base = len(vertices)
                    vertices.append(v0)
                    vertices.append(v1)
                    vertices.append(v2)
                    # Compute normals via SDF gradient
                    normals.append(sdf_normal(phi, v0, max(step[0], 1.0)))
                    normals.append(sdf_normal(phi, v1, max(step[0], 1.0)))
                    normals.append(sdf_normal(phi, v2, max(step[0], 1.0)))
                    triangles.append((base, base + 1, base + 2))

    complexity = _count_primitives(phi)
    return {
        "sdf_tree": dict(phi),
        "resolution": resolution,
        "vertex_count": len(vertices),
        "triangle_count": len(triangles),
        "estimated": False,
        "extractor": "marching_cubes",
        "vertices": vertices,
        "normals": normals,
        "triangles": triangles,
    }


# Standard Marching Cubes edge table (256 entries).
# Each bit indicates which of the 12 edges are intersected.
_MC_EDGE_TABLE = [
    0x000, 0x109, 0x203, 0x30a, 0x406, 0x50f, 0x605, 0x70c,
    0x80c, 0x905, 0xa0f, 0xb06, 0xc0a, 0xd03, 0xe09, 0xf00,
    0x190, 0x099, 0x393, 0x29a, 0x596, 0x49f, 0x795, 0x69c,
    0x99c, 0x895, 0xb9f, 0xa96, 0xd9a, 0xc93, 0xf99, 0xe90,
    0x230, 0x339, 0x033, 0x13a, 0x636, 0x73f, 0x435, 0x53c,
    0xa3c, 0xb35, 0x83f, 0x936, 0xe3a, 0xf33, 0xc39, 0xd30,
    0x3a0, 0x2a9, 0x1a3, 0x0aa, 0x7a6, 0x6af, 0x5a5, 0x4ac,
    0xbac, 0xaa5, 0x9af, 0x8a6, 0xfaa, 0xea3, 0xda9, 0xca0,
    0x460, 0x569, 0x663, 0x76a, 0x066, 0x16f, 0x265, 0x36c,
    0xc6c, 0xd65, 0xe6f, 0xf66, 0x86a, 0x963, 0xa69, 0xb60,
    0x5f0, 0x4f9, 0x7f3, 0x6fa, 0x1f6, 0x0ff, 0x3f5, 0x2fc,
    0xdfc, 0xcf5, 0xfff, 0xef6, 0x9fa, 0x8f3, 0xbf9, 0xaf0,
    0x650, 0x759, 0x453, 0x55a, 0x256, 0x35f, 0x055, 0x15c,
    0xe5c, 0xf55, 0xc5f, 0xd56, 0xa5a, 0xb53, 0x859, 0x950,
    0x7c0, 0x6c9, 0x5c3, 0x4ca, 0x3c6, 0x2cf, 0x1c5, 0x0cc,
    0xfcc, 0xec5, 0xdcf, 0xcc6, 0xbca, 0xac3, 0x9c9, 0x8c0,
    0x8c0, 0x9c9, 0xac3, 0xbca, 0xcc6, 0xdcf, 0xec5, 0xfcc,
    0x0cc, 0x1c5, 0x2cf, 0x3c6, 0x4ca, 0x5c3, 0x6c9, 0x7c0,
    0x950, 0x859, 0xb53, 0xa5a, 0xd56, 0xc5f, 0xf55, 0xe5c,
    0x15c, 0x055, 0x35f, 0x256, 0x55a, 0x453, 0x759, 0x650,
    0xaf0, 0xbf9, 0x8f3, 0x9fa, 0xef6, 0xfff, 0xcf5, 0xdfc,
    0x2fc, 0x3f5, 0x0ff, 0x1f6, 0x6fa, 0x7f3, 0x4f9, 0x5f0,
    0xb60, 0xa69, 0x963, 0x86a, 0xf66, 0xe6f, 0xd65, 0xc6c,
    0x36c, 0x265, 0x16f, 0x066, 0x76a, 0x663, 0x569, 0x460,
    0xca0, 0xda9, 0xea3, 0xfaa, 0x8a6, 0x9af, 0xaa5, 0xbac,
    0x4ac, 0x5a5, 0x6af, 0x7a6, 0x0aa, 0x1a3, 0x2a9, 0x3a0,
    0xd30, 0xc39, 0xf33, 0xe3a, 0x936, 0x83f, 0xb35, 0xa3c,
    0x53c, 0x435, 0x73f, 0x636, 0x13a, 0x033, 0x339, 0x230,
    0xe90, 0xf99, 0xc93, 0xd9a, 0xa96, 0xb9f, 0x895, 0x99c,
    0x69c, 0x795, 0x49f, 0x596, 0x29a, 0x393, 0x099, 0x190,
    0xf00, 0xe09, 0xd03, 0xc0a, 0xb06, 0xa0f, 0x905, 0x80c,
    0x70c, 0x605, 0x50f, 0x406, 0x30a, 0x203, 0x109, 0x000,
]

# Standard Marching Cubes triangle table (256 entries).
# Each entry lists up to 15 edge indices forming triangles (-1 = unused).
_MC_TRI_TABLE_RAW: list[list[int]] = [
    [-1], [0, 8, 3, -1], [0, 1, 9, -1], [1, 8, 3, 9, 8, 1, -1],
    [1, 2, 10, -1], [0, 8, 3, 1, 2, 10, -1], [9, 2, 10, 0, 2, 9, -1],
    [2, 8, 3, 2, 10, 8, 10, 9, 8, -1], [3, 11, 2, -1], [0, 11, 2, 8, 11, 0, -1],
    [1, 9, 0, 2, 3, 11, -1], [1, 11, 2, 1, 9, 11, 9, 8, 11, -1],
    [3, 10, 1, 11, 10, 3, -1], [0, 10, 1, 0, 8, 10, 8, 11, 10, -1],
    [3, 9, 0, 3, 11, 9, 11, 10, 9, -1], [9, 8, 10, 10, 8, 11, -1],
    [4, 7, 8, -1], [4, 3, 0, 7, 3, 4, -1], [0, 1, 9, 8, 4, 7, -1],
    [4, 1, 9, 4, 7, 1, 7, 3, 1, -1], [1, 2, 10, 8, 4, 7, -1],
    [3, 4, 7, 3, 0, 4, 1, 2, 10, -1], [9, 2, 10, 9, 0, 2, 8, 4, 7, -1],
    [2, 10, 9, 2, 9, 7, 2, 7, 3, 7, 9, 4, -1], [8, 4, 7, 3, 11, 2, -1],
    [11, 4, 7, 11, 2, 4, 2, 0, 4, -1], [9, 0, 1, 8, 4, 7, 2, 3, 11, -1],
    [4, 7, 11, 9, 4, 11, 9, 11, 2, 9, 2, 1, -1], [3, 10, 1, 3, 11, 10, 7, 8, 4, -1],
    [1, 11, 10, 1, 4, 11, 1, 0, 4, 7, 11, 4, -1], [4, 7, 8, 9, 0, 11, 9, 11, 10, 11, 0, 3, -1],
    [4, 7, 11, 4, 11, 9, 9, 11, 10, -1], [9, 5, 4, -1], [9, 5, 4, 0, 8, 3, -1],
    [0, 5, 4, 1, 5, 0, -1], [8, 5, 4, 8, 3, 5, 3, 1, 5, -1],
    [1, 2, 10, 9, 5, 4, -1], [3, 0, 8, 1, 2, 10, 4, 9, 5, -1],
    [5, 2, 10, 5, 4, 2, 4, 0, 2, -1], [2, 10, 5, 3, 2, 5, 3, 5, 4, 3, 4, 8, -1],
    [9, 5, 4, 2, 3, 11, -1], [0, 11, 2, 0, 8, 11, 4, 9, 5, -1],
    [0, 5, 4, 0, 1, 5, 2, 3, 11, -1], [2, 1, 5, 2, 5, 8, 2, 8, 11, 4, 8, 5, -1],
    [10, 3, 11, 10, 1, 3, 9, 5, 4, -1], [4, 9, 5, 0, 8, 1, 8, 10, 1, 8, 11, 10, -1],
    [5, 4, 0, 5, 0, 11, 5, 11, 10, 11, 0, 3, -1], [5, 4, 8, 5, 8, 10, 10, 8, 11, -1],
    [9, 7, 8, 5, 7, 9, -1], [9, 3, 0, 9, 5, 3, 5, 7, 3, -1],
    [0, 7, 8, 0, 1, 7, 1, 5, 7, -1], [1, 5, 3, 3, 5, 7, -1],
    [9, 7, 8, 9, 5, 7, 10, 1, 2, -1], [10, 1, 2, 9, 5, 0, 5, 3, 0, 5, 7, 3, -1],
    [8, 0, 2, 8, 2, 5, 8, 5, 7, 10, 5, 2, -1], [2, 10, 5, 2, 5, 3, 3, 5, 7, -1],
    [7, 9, 5, 7, 8, 9, 3, 11, 2, -1], [9, 5, 7, 9, 7, 2, 9, 2, 0, 2, 7, 11, -1],
    [2, 3, 11, 0, 1, 8, 1, 7, 8, 1, 5, 7, -1], [11, 2, 1, 11, 1, 7, 7, 1, 5, -1],
    [9, 5, 8, 8, 5, 7, 10, 1, 3, 10, 3, 11, -1], [5, 7, 0, 5, 0, 9, 7, 11, 0, 1, 0, 10, 11, 10, 0, -1],
    [11, 10, 0, 11, 0, 3, 10, 5, 0, 8, 0, 7, 5, 7, 0, -1], [11, 10, 5, 7, 11, 5, -1],
    [10, 6, 5, -1], [0, 8, 3, 5, 10, 6, -1], [9, 0, 1, 5, 10, 6, -1],
    [1, 8, 3, 1, 9, 8, 5, 10, 6, -1], [1, 6, 5, 2, 6, 1, -1],
    [1, 6, 5, 1, 2, 6, 3, 0, 8, -1], [9, 6, 5, 9, 0, 6, 0, 2, 6, -1],
    [5, 9, 8, 5, 8, 2, 5, 2, 6, 3, 2, 8, -1], [2, 3, 11, 10, 6, 5, -1],
    [11, 0, 8, 11, 2, 0, 10, 6, 5, -1], [0, 1, 9, 2, 3, 11, 5, 10, 6, -1],
    [5, 10, 6, 1, 9, 2, 9, 11, 2, 9, 8, 11, -1], [6, 3, 11, 6, 5, 3, 5, 1, 3, -1],
    [0, 8, 11, 0, 11, 5, 0, 5, 1, 5, 11, 6, -1], [3, 11, 6, 0, 3, 6, 0, 6, 5, 0, 5, 9, -1],
    [6, 5, 9, 6, 9, 11, 11, 9, 8, -1], [5, 10, 6, 4, 7, 8, -1],
    [4, 3, 0, 4, 7, 3, 6, 5, 10, -1], [1, 9, 0, 5, 10, 6, 8, 4, 7, -1],
    [10, 6, 5, 1, 9, 7, 1, 7, 3, 7, 9, 4, -1], [6, 1, 2, 6, 5, 1, 4, 7, 8, -1],
    [1, 2, 5, 5, 2, 6, 3, 0, 4, 3, 4, 7, -1], [8, 4, 7, 9, 0, 5, 0, 6, 5, 0, 2, 6, -1],
    [7, 3, 9, 7, 9, 4, 3, 2, 9, 5, 9, 6, 2, 6, 9, -1], [3, 11, 2, 7, 8, 4, 10, 6, 5, -1],
    [5, 10, 6, 4, 7, 2, 4, 2, 0, 2, 7, 11, -1], [0, 1, 9, 4, 7, 8, 2, 3, 11, 5, 10, 6, -1],
    [9, 2, 1, 9, 11, 2, 9, 4, 11, 7, 11, 4, 5, 10, 6, -1], [8, 4, 7, 3, 11, 5, 3, 5, 1, 5, 11, 6, -1],
    [5, 1, 11, 5, 11, 6, 1, 0, 11, 7, 11, 4, 0, 4, 11, -1], [0, 5, 9, 0, 6, 5, 0, 3, 6, 11, 6, 3, 8, 4, 7, -1],
    [6, 5, 9, 6, 9, 11, 4, 7, 9, 7, 11, 9, -1], [10, 4, 9, 6, 4, 10, -1],
    [4, 10, 6, 4, 9, 10, 0, 8, 3, -1], [10, 0, 1, 10, 6, 0, 6, 4, 0, -1],
    [8, 3, 1, 8, 1, 6, 8, 6, 4, 6, 1, 10, -1], [1, 4, 9, 1, 2, 4, 2, 6, 4, -1],
    [3, 0, 8, 1, 2, 9, 2, 4, 9, 2, 6, 4, -1], [0, 2, 4, 4, 2, 6, -1],
    [8, 3, 2, 8, 2, 4, 4, 2, 6, -1], [10, 4, 9, 10, 6, 4, 11, 2, 3, -1],
    [0, 8, 2, 2, 8, 11, 4, 9, 10, 4, 10, 6, -1], [3, 11, 2, 0, 1, 6, 0, 6, 4, 6, 1, 10, -1],
    [6, 4, 1, 6, 1, 10, 4, 8, 1, 2, 1, 11, 8, 11, 1, -1], [9, 6, 4, 9, 3, 6, 9, 1, 3, 11, 6, 3, -1],
    [8, 11, 1, 8, 1, 0, 11, 6, 1, 9, 1, 4, 6, 4, 1, -1], [3, 11, 6, 3, 6, 0, 0, 6, 4, -1],
    [6, 4, 8, 11, 6, 8, -1], [7, 10, 6, 7, 8, 10, 8, 9, 10, -1],
    [0, 7, 3, 0, 10, 7, 0, 9, 10, 6, 7, 10, -1], [10, 6, 7, 1, 10, 7, 1, 7, 8, 1, 8, 0, -1],
    [10, 6, 7, 10, 7, 1, 1, 7, 3, -1], [1, 2, 6, 1, 6, 8, 1, 8, 9, 8, 6, 7, -1],
    [2, 6, 9, 2, 9, 1, 6, 7, 9, 0, 9, 3, 7, 3, 9, -1], [7, 8, 0, 7, 0, 6, 6, 0, 2, -1],
    [7, 3, 2, 6, 7, 2, -1], [2, 3, 11, 10, 6, 8, 10, 8, 9, 8, 6, 7, -1],
    [2, 0, 7, 2, 7, 11, 0, 9, 7, 6, 7, 10, 9, 10, 7, -1], [1, 8, 0, 1, 7, 8, 1, 10, 7, 6, 7, 10, 2, 3, 11, -1],
    [11, 2, 1, 11, 1, 7, 10, 6, 1, 6, 7, 1, -1], [8, 9, 6, 8, 6, 7, 9, 1, 6, 11, 6, 3, 1, 3, 6, -1],
    [0, 9, 1, 11, 6, 7, -1], [7, 8, 0, 7, 0, 6, 3, 11, 0, 11, 6, 0, -1], [7, 11, 6, -1],
    [7, 6, 11, -1], [3, 0, 8, 11, 7, 6, -1], [0, 1, 9, 11, 7, 6, -1],
    [8, 1, 9, 8, 3, 1, 11, 7, 6, -1], [10, 1, 2, 6, 11, 7, -1],
    [1, 2, 10, 3, 0, 8, 6, 11, 7, -1], [2, 9, 0, 2, 10, 9, 6, 11, 7, -1],
    [6, 11, 7, 2, 10, 3, 10, 8, 3, 10, 9, 8, -1], [7, 2, 3, 6, 2, 7, -1],
    [7, 0, 8, 7, 6, 0, 6, 2, 0, -1], [2, 7, 6, 2, 3, 7, 0, 1, 9, -1],
    [1, 6, 2, 1, 8, 6, 1, 9, 8, 8, 7, 6, -1], [10, 7, 6, 10, 1, 7, 1, 3, 7, -1],
    [10, 7, 6, 1, 7, 10, 1, 8, 7, 1, 0, 8, -1], [0, 3, 7, 0, 7, 10, 0, 10, 9, 6, 10, 7, -1],
    [7, 6, 10, 7, 10, 8, 8, 10, 9, -1], [6, 8, 4, 11, 8, 6, -1],
    [3, 6, 11, 3, 0, 6, 0, 4, 6, -1], [8, 6, 11, 8, 4, 6, 9, 0, 1, -1],
    [9, 4, 6, 9, 6, 3, 9, 3, 1, 11, 3, 6, -1], [6, 8, 4, 6, 11, 8, 2, 10, 1, -1],
    [1, 2, 10, 3, 0, 11, 0, 6, 11, 0, 4, 6, -1], [4, 11, 8, 4, 6, 11, 0, 2, 9, 2, 10, 9, -1],
    [10, 9, 3, 10, 3, 2, 9, 4, 3, 11, 3, 6, 4, 6, 3, -1], [8, 2, 3, 8, 4, 2, 4, 6, 2, -1],
    [0, 4, 2, 4, 6, 2, -1], [1, 9, 0, 2, 3, 4, 2, 4, 6, 4, 3, 8, -1],
    [1, 9, 4, 1, 4, 2, 2, 4, 6, -1], [8, 1, 3, 8, 6, 1, 8, 4, 6, 6, 10, 1, -1],
    [10, 1, 0, 10, 0, 6, 6, 0, 4, -1], [4, 6, 3, 4, 3, 8, 6, 10, 3, 0, 3, 9, 10, 9, 3, -1],
    [10, 9, 4, 6, 10, 4, -1], [4, 9, 5, 7, 6, 11, -1], [0, 8, 3, 4, 9, 5, 11, 7, 6, -1],
    [5, 0, 1, 5, 4, 0, 7, 6, 11, -1], [11, 7, 6, 8, 3, 4, 3, 5, 4, 3, 1, 5, -1],
    [9, 5, 4, 10, 1, 2, 7, 6, 11, -1], [6, 11, 7, 1, 2, 10, 0, 8, 3, 4, 9, 5, -1],
    [7, 6, 11, 5, 4, 10, 4, 2, 10, 4, 0, 2, -1], [3, 4, 8, 3, 5, 4, 3, 2, 5, 10, 5, 2, 11, 7, 6, -1],
    [7, 2, 3, 7, 6, 2, 5, 4, 9, -1], [9, 5, 4, 0, 8, 6, 0, 6, 2, 6, 8, 7, -1],
    [3, 6, 2, 3, 7, 6, 1, 5, 0, 5, 4, 0, -1], [6, 2, 8, 6, 8, 7, 2, 1, 8, 4, 8, 5, 1, 5, 8, -1],
    [9, 5, 4, 10, 1, 6, 1, 7, 6, 1, 3, 7, -1], [1, 6, 10, 1, 7, 6, 1, 0, 7, 8, 7, 0, 9, 5, 4, -1],
    [4, 0, 10, 4, 10, 5, 0, 3, 10, 6, 10, 7, 3, 7, 10, -1], [7, 6, 10, 7, 10, 8, 5, 4, 10, 4, 8, 10, -1],
    [6, 9, 5, 6, 11, 9, 11, 8, 9, -1], [3, 6, 11, 0, 6, 3, 0, 5, 6, 0, 9, 5, -1],
    [0, 11, 8, 0, 5, 11, 0, 1, 5, 5, 6, 11, -1], [6, 11, 3, 6, 3, 5, 5, 3, 1, -1],
    [1, 2, 10, 9, 5, 11, 9, 11, 8, 11, 5, 6, -1], [0, 11, 3, 0, 6, 11, 0, 9, 6, 5, 6, 9, 1, 2, 10, -1],
    [11, 8, 5, 11, 5, 6, 8, 0, 5, 10, 5, 2, 0, 2, 5, -1], [6, 11, 3, 6, 3, 5, 2, 10, 3, 10, 5, 3, -1],
    [5, 8, 9, 5, 2, 8, 5, 6, 2, 3, 8, 2, -1], [9, 5, 6, 9, 6, 0, 0, 6, 2, -1],
    [1, 5, 8, 1, 8, 0, 5, 6, 8, 3, 8, 2, 6, 2, 8, -1], [1, 5, 6, 2, 1, 6, -1],
    [1, 3, 6, 1, 6, 10, 3, 8, 6, 5, 6, 9, 8, 9, 6, -1], [10, 1, 0, 10, 0, 6, 9, 5, 0, 5, 6, 0, -1],
    [0, 3, 8, 5, 6, 10, -1], [10, 5, 6, -1], [11, 5, 10, 7, 5, 11, -1],
    [11, 5, 10, 11, 7, 5, 8, 3, 0, -1], [5, 11, 7, 5, 10, 11, 1, 9, 0, -1],
    [10, 7, 5, 10, 11, 7, 9, 8, 1, 8, 3, 1, -1], [11, 1, 2, 11, 7, 1, 7, 5, 1, -1],
    [0, 8, 3, 1, 2, 7, 1, 7, 5, 7, 2, 11, -1], [9, 7, 5, 9, 2, 7, 9, 0, 2, 2, 11, 7, -1],
    [7, 5, 2, 7, 2, 11, 5, 9, 2, 3, 2, 8, 9, 8, 2, -1], [2, 5, 10, 2, 3, 5, 3, 7, 5, -1],
    [8, 2, 0, 8, 5, 2, 8, 7, 5, 10, 2, 5, -1], [9, 0, 1, 5, 10, 3, 5, 3, 7, 3, 10, 2, -1],
    [9, 8, 2, 9, 2, 1, 8, 7, 2, 10, 2, 5, 7, 5, 2, -1], [1, 3, 5, 3, 7, 5, -1],
    [0, 8, 7, 0, 7, 1, 1, 7, 5, -1], [9, 0, 3, 9, 3, 5, 5, 3, 7, -1],
    [9, 8, 7, 5, 9, 7, -1], [5, 8, 4, 5, 10, 8, 10, 11, 8, -1],
    [5, 0, 4, 5, 11, 0, 5, 10, 11, 11, 3, 0, -1], [0, 1, 9, 8, 4, 10, 8, 10, 11, 10, 4, 5, -1],
    [10, 11, 4, 10, 4, 5, 11, 3, 4, 9, 4, 1, 3, 1, 4, -1], [2, 5, 1, 2, 8, 5, 2, 11, 8, 4, 5, 8, -1],
    [0, 4, 11, 0, 11, 3, 4, 5, 11, 2, 11, 1, 5, 1, 11, -1], [0, 2, 5, 0, 5, 9, 2, 11, 5, 4, 5, 8, 11, 8, 5, -1],
    [9, 4, 5, 2, 11, 3, -1], [2, 5, 10, 3, 5, 2, 3, 4, 5, 3, 8, 4, -1],
    [5, 10, 2, 5, 2, 4, 4, 2, 0, -1], [3, 10, 2, 3, 5, 10, 3, 8, 5, 4, 5, 8, 0, 1, 9, -1],
    [5, 10, 2, 5, 2, 4, 1, 9, 2, 9, 4, 2, -1], [8, 4, 5, 8, 5, 3, 3, 5, 1, -1],
    [0, 4, 5, 1, 0, 5, -1], [8, 4, 5, 8, 5, 3, 9, 0, 5, 0, 3, 5, -1],
    [9, 4, 5, -1], [4, 11, 7, 4, 9, 11, 9, 10, 11, -1],
    [0, 8, 3, 4, 9, 7, 9, 11, 7, 9, 10, 11, -1], [1, 10, 11, 1, 11, 4, 1, 4, 0, 7, 4, 11, -1],
    [3, 1, 4, 3, 4, 8, 1, 10, 4, 7, 4, 11, 10, 11, 4, -1], [4, 11, 7, 9, 11, 4, 9, 2, 11, 9, 1, 2, -1],
    [9, 7, 4, 9, 11, 7, 9, 1, 11, 2, 11, 1, 0, 8, 3, -1], [11, 7, 4, 11, 4, 2, 2, 4, 0, -1],
    [11, 7, 4, 11, 4, 2, 8, 3, 4, 3, 2, 4, -1], [2, 9, 10, 2, 7, 9, 2, 3, 7, 7, 4, 9, -1],
    [9, 10, 7, 9, 7, 4, 10, 2, 7, 8, 7, 0, 2, 0, 7, -1], [3, 7, 10, 3, 10, 2, 7, 4, 10, 1, 10, 0, 4, 0, 10, -1],
    [1, 10, 2, 8, 7, 4, -1], [4, 9, 1, 4, 1, 7, 7, 1, 3, -1],
    [4, 9, 1, 4, 1, 7, 0, 8, 1, 8, 7, 1, -1], [4, 0, 3, 7, 4, 3, -1], [4, 8, 7, -1],
    [9, 10, 8, 10, 11, 8, -1], [3, 0, 9, 3, 9, 11, 11, 9, 10, -1],
    [0, 1, 10, 0, 10, 8, 8, 10, 11, -1], [3, 1, 10, 11, 3, 10, -1],
    [1, 2, 11, 1, 11, 9, 9, 11, 8, -1], [3, 0, 9, 3, 9, 11, 1, 2, 9, 2, 11, 9, -1],
    [0, 2, 11, 8, 0, 11, -1], [3, 2, 11, -1], [2, 3, 8, 2, 8, 10, 10, 8, 9, -1],
    [9, 10, 2, 0, 9, 2, -1], [2, 3, 8, 2, 8, 10, 0, 1, 8, 1, 10, 8, -1],
    [1, 10, 2, -1], [1, 3, 8, 9, 1, 8, -1], [0, 9, 1, -1], [0, 3, 8, -1], [-1],
]

# Build a list-of-lists for fast lookup
_MC_TRI_TABLE: list[list[int]] = []
for _entry in _MC_TRI_TABLE_RAW:
    _MC_TRI_TABLE.append([e for e in _entry if e >= 0])


def _count_primitives(node: Mapping[str, Any]) -> int:
    node_type = node.get("type")
    if node_type in {"sphere", "capsule", "box"}:
        return 1
    if "child" in node and isinstance(node["child"], Mapping):
        return _count_primitives(node["child"])
    children = node.get("children")
    if isinstance(children, list):
        return sum(_count_primitives(child) for child in children if isinstance(child, Mapping))
    return 1

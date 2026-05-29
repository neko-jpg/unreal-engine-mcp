"""Pure-Python 3D superformula mesh generator."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

from server.generation.mesh_payload import ProceduralMeshPayload


@dataclass
class SuperformulaParams:
    m1: float = 6.0
    n1_1: float = 1.0
    n2_1: float = 1.0
    n3_1: float = 1.0
    a1: float = 1.0
    b1: float = 1.0
    m2: float = 6.0
    n1_2: float = 1.0
    n2_2: float = 1.0
    n3_2: float = 1.0
    a2: float = 1.0
    b2: float = 1.0


def sf2d(theta: float, m: float, n1: float, n2: float, n3: float, a: float, b: float) -> float:
    t1 = abs(math.cos(m * theta / 4.0) / a) ** n2
    t2 = abs(math.sin(m * theta / 4.0) / b) ** n3
    total = t1 + t2
    if total < 1.0e-10:
        return 0.0
    return total ** (-1.0 / n1)


def superformula_mesh(
    params: SuperformulaParams,
    resolution: int = 32,
    scale: float = 100.0,
    mcp_id: str = "superformula",
    request_id: int = 1,
) -> ProceduralMeshPayload:
    res = max(4, min(int(resolution), 256))
    lat_steps = res
    lon_steps = res * 2
    positions: List[List[float]] = []
    normals: List[List[float]] = []
    uvs: List[List[float]] = []
    indices: List[int] = []

    r_lat = [
        sf2d(-math.pi / 2.0 + math.pi * i / lat_steps, params.m1, params.n1_1, params.n2_1, params.n3_1, params.a1, params.b1)
        for i in range(lat_steps + 1)
    ]
    r_lon = [
        sf2d(2.0 * math.pi * j / lon_steps, params.m2, params.n1_2, params.n2_2, params.n3_2, params.a2, params.b2)
        for j in range(lon_steps + 1)
    ]
    for i, r1 in enumerate(r_lat):
        theta = -math.pi / 2.0 + math.pi * i / lat_steps
        for j, r2 in enumerate(r_lon):
            phi = 2.0 * math.pi * j / lon_steps
            x = r1 * math.cos(theta) * r2 * math.cos(phi) * scale
            y = r1 * math.cos(theta) * r2 * math.sin(phi) * scale
            z = r1 * math.sin(theta) * scale
            positions.append([x, y, z])
            length = math.sqrt(x * x + y * y + z * z)
            normals.append([x / length, y / length, z / length] if length > 1.0e-9 else [0.0, 0.0, 1.0])
            uvs.append([j / lon_steps, i / lat_steps])
    lon_count = lon_steps + 1
    for i in range(lat_steps):
        for j in range(lon_steps):
            v00 = i * lon_count + j
            v10 = (i + 1) * lon_count + j
            v01 = i * lon_count + j + 1
            v11 = (i + 1) * lon_count + j + 1
            indices.extend([v00, v10, v01, v01, v10, v11])
    return ProceduralMeshPayload(mcp_id=mcp_id, request_id=request_id, positions=positions, normals=normals, indices=indices, uvs=uvs)

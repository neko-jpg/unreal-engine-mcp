"""Tests for Python-side procedural generation migrated from Rust concepts."""

from __future__ import annotations

from server.generation.geometry import Aabb3, Obb3, segment_intersection_2d
from server.generation.lsystem import evaluate_lsystem
from server.generation.mesh_payload import MCPM_HEADER_SIZE, ProceduralMeshHeader, ProceduralMeshPayload
from server.generation.sdf import evaluate_sdf, sdf_to_voxel_surface_mesh
from server.generation.superformula import SuperformulaParams, superformula_mesh
from server.generation.wfc import solve_wfc_grid


def test_aabb_and_segment_intersection():
    a = Aabb3((0, 0, 0), (10, 10, 10))
    b = Aabb3((5, 5, 5), (15, 15, 15))
    assert a.intersects(b)
    assert a.contains_point((5, 5, 5))
    assert segment_intersection_2d((0, 0, 10, 10), (0, 10, 10, 0), 0.001) == (5.0, 5.0)


def test_obb_intersection():
    a = Obb3.from_euler_degrees((0, 0, 0), (50, 10, 50), yaw=0)
    b = Obb3.from_euler_degrees((0, 0, 0), (50, 10, 50), yaw=45)
    assert a.intersects_obb(b)
    assert a.contains_point((0, 0, 0))


def test_mesh_payload_header_roundtrip():
    payload = ProceduralMeshPayload(
        mcp_id="py_test",
        request_id=42,
        positions=[[0, 0, 0], [1, 0, 0], [0, 1, 0]],
        normals=[[0, 0, 1], [0, 0, 1], [0, 0, 1]],
        indices=[0, 1, 2],
    )
    data = payload.to_bytes()
    assert len(data) == payload.total_bytes()
    header = ProceduralMeshHeader.from_bytes(data[:MCPM_HEADER_SIZE])
    assert header.mcp_id == "py_test"
    assert header.vertex_count == 3
    assert header.index_count == 3


def test_sdf_eval_and_voxel_mesh():
    sphere = {"type": "sphere", "center": [0, 0, 0], "radius": 1.0}
    assert evaluate_sdf(sphere, [0, 0, 0]) < 0
    assert evaluate_sdf(sphere, [2, 0, 0]) > 0
    mesh = sdf_to_voxel_surface_mesh(sphere, resolution=8, mcp_id="sphere")
    assert len(mesh.positions) > 0
    assert len(mesh.indices) % 3 == 0


def test_lsystem_wfc_and_superformula():
    lsys = evaluate_lsystem(axiom="F", rules={"F": "F+F-F-F+F"}, iterations=2)
    assert lsys["segment_count"] == 25
    grid = solve_wfc_grid(
        2,
        2,
        tiles=[{"id": "grass", "weight": 1.0}],
        constraints=[
            {"left": "grass", "right": "grass", "direction": "east"},
            {"left": "grass", "right": "grass", "direction": "south"},
        ],
        seed=1,
    )
    assert len(grid["tiles"]) == 4
    mesh = superformula_mesh(SuperformulaParams(), resolution=8, scale=1.0, mcp_id="sf")
    assert len(mesh.positions) > 0
    assert mesh.uvs is not None

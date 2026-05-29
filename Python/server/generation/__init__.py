"""Procedural generation helpers for scene agents."""

from __future__ import annotations

from server.generation.cave_graph_generator import CaveGraphGenerator
from server.generation.geometry import Aabb3, Obb3, segment_intersection_2d
from server.generation.lsystem import evaluate_lsystem
from server.generation.mesh_payload import ProceduralMeshPayload
from server.generation.sdf import evaluate_sdf, estimate_sdf_bounds, sdf_to_voxel_surface_mesh
from server.generation.sdf_cave_field import (
    apply_domain_warp,
    apply_fractal_roughness,
    build_cave_sdf_from_graph,
    extract_mesh_marching_cubes,
)
from server.generation.superformula import SuperformulaParams, superformula_mesh
from server.generation.wfc import solve_wfc_grid

__all__ = [
    "Aabb3",
    "CaveGraphGenerator",
    "Obb3",
    "ProceduralMeshPayload",
    "SuperformulaParams",
    "apply_domain_warp",
    "apply_fractal_roughness",
    "build_cave_sdf_from_graph",
    "evaluate_lsystem",
    "evaluate_sdf",
    "estimate_sdf_bounds",
    "extract_mesh_marching_cubes",
    "sdf_to_voxel_surface_mesh",
    "segment_intersection_2d",
    "solve_wfc_grid",
    "superformula_mesh",
]

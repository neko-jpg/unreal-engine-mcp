"""Unit tests for quality vector and gates."""

from __future__ import annotations

from server.quality.quality_gate import QualityGate
from server.quality.quality_vector import QualityVectorBuilder


def test_quality_vector_penalizes_boxy_default_cave():
    metrics = {
        "main_mesh_exists": True,
        "triangle_count": 12000,
        "flat_surface_ratio": 0.58,
        "curvature_entropy": 0.12,
        "arch_score": 0.22,
        "detail_density_per_m2": 0.1,
        "default_material_actor_count": 4,
        "image_contrast": 0.22,
        "lighting_contrast_score": 0.25,
        "topology_score": 0.15,
        "performance_score": 0.9,
    }
    vector = QualityVectorBuilder().build(metrics)
    gate = QualityGate().check(vector, metrics)
    assert vector["overall"] < 70.0
    assert gate.passed is False
    assert "flat_surface_ratio" in gate.blockers


def test_quality_vector_accepts_strong_cave_metrics():
    metrics = {
        "main_mesh_exists": True,
        "triangle_count": 96000,
        "flat_surface_ratio": 0.18,
        "curvature_entropy": 0.74,
        "arch_score": 0.77,
        "detail_density_per_m2": 3.8,
        "stalactite_count": 18,
        "rock_debris_count": 42,
        "default_material_actor_count": 0,
        "normal_map_coverage": 0.92,
        "roughness_mean": 0.83,
        "wetness_coverage": 0.21,
        "moss_coverage": 0.12,
        "image_contrast": 0.71,
        "lighting_contrast_score": 0.76,
        "fog_density": 0.065,
        "topology_score": 0.70,
    }
    vector = QualityVectorBuilder().build(metrics, {"semantic_score": 0.78, "composition_score": 0.72})
    gate = QualityGate().check(vector, metrics)
    assert vector["overall"] >= 70.0
    assert gate.passed is True


def test_quality_vector_penalizes_missing_main_mesh():
    metrics = {
        "main_mesh_exists": False,
        "triangle_count": 0,
        "flat_surface_ratio": 0.20,
        "curvature_entropy": 0.65,
        "arch_score": 0.70,
        "detail_density_per_m2": 2.0,
        "default_material_actor_count": 0,
        "image_contrast": 0.55,
        "lighting_contrast_score": 0.60,
        "topology_score": 0.50,
    }
    vector = QualityVectorBuilder().build(metrics)
    assert vector["overall"] < 60.0


def test_quality_vector_penalizes_default_materials():
    metrics = {
        "main_mesh_exists": True,
        "triangle_count": 50000,
        "flat_surface_ratio": 0.20,
        "curvature_entropy": 0.60,
        "arch_score": 0.65,
        "detail_density_per_m2": 2.5,
        "default_material_actor_count": 3,
        "image_contrast": 0.55,
        "lighting_contrast_score": 0.60,
        "topology_score": 0.50,
    }
    vector_no_default = QualityVectorBuilder().build({**metrics, "default_material_actor_count": 0})
    vector_with_default = QualityVectorBuilder().build(metrics)
    assert vector_with_default["overall"] < vector_no_default["overall"]


def test_quality_vector_penalizes_floating_objects():
    metrics = {
        "main_mesh_exists": True,
        "triangle_count": 50000,
        "flat_surface_ratio": 0.20,
        "curvature_entropy": 0.60,
        "arch_score": 0.65,
        "detail_density_per_m2": 2.5,
        "default_material_actor_count": 0,
        "floating_object_count": 5,
        "image_contrast": 0.55,
        "lighting_contrast_score": 0.60,
        "topology_score": 0.50,
    }
    vector_clean = QualityVectorBuilder().build({**metrics, "floating_object_count": 0})
    vector_float = QualityVectorBuilder().build(metrics)
    assert vector_float["overall"] < vector_clean["overall"]


def test_quality_vector_individual_dimensions():
    metrics = {
        "main_mesh_exists": True,
        "triangle_count": 80000,
        "flat_surface_ratio": 0.15,
        "curvature_entropy": 0.80,
        "arch_score": 0.85,
        "detail_density_per_m2": 0.85,
        "detail_distribution_score": 0.85,
        "stalactite_count": 0.85,
        "rock_debris_count": 40,
        "default_material_actor_count": 0,
        "normal_map_coverage": 0.95,
        "roughness_mean": 0.88,
        "wetness_coverage": 0.25,
        "moss_coverage": 0.15,
        "image_contrast": 0.75,
        "lighting_contrast_score": 0.80,
        "fog_density": 0.07,
        "topology_score": 0.80,
    }
    vector = QualityVectorBuilder().build(metrics, {"semantic_score": 0.85, "composition_score": 0.80})
    assert vector["shape_score"] > 0.7
    assert vector["detail_score"] > 0.3
    assert vector["material_score"] > 0.6
    assert vector["lighting_score"] > 0.6

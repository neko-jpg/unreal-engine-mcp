### Foliage: 8 handlers promoted (part 1/3)

- Issue: #90
- PR: codex-stubs-w3-foliage-part1
- Wave: W3
- Handlers promoted: 8 / 20
- New `executed: true` cases:
  - `create_foliage_type` — UFoliageType asset creation
  - `register_static_mesh_foliage` — UFoliageType_InstancedStaticMesh::SetStaticMesh()
  - `register_actor_foliage` — UFoliageType_Actor configuration
  - `set_foliage_density` — UFoliageType::Density
  - `set_foliage_scale_range` — UFoliageType::ScaleX/Y/Z Min/Max
  - `set_foliage_random_yaw` — UFoliageType::RandomYaw
  - `set_foliage_align_to_normal` — UFoliageType::AlignToNormal
  - `set_foliage_cull_distance` — UFoliageType::CullDistance{Start,End}
- Approach (UE 5.7-safe): Direct UFoliageType property manipulation
- Tests added: `Python/tests/unit/test_w3_foliage_executed_envelope.py`

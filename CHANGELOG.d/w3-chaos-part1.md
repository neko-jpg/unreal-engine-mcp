## [Unreleased]

### Changed

- **Chaos #89**: Promote 8 Chaos/Physics stubs to executed envelope (part 1).
  - `create_collision_channel`: adds custom collision channel via UPhysicsSettings (spike reference handler)
  - `create_object_channel`: adds object-type collision channel via UPhysicsSettings
  - `create_trace_channel`: adds trace-type collision channel via UPhysicsSettings
  - `create_geometry_collection`: spawns actor with geometry collection metadata
  - `fracture_geometry_collection`: persists fracture type and seed configuration on GC actor
  - `create_chaos_field`: spawns AFieldSystemActor with radial falloff field metadata
  - `configure_chaos_solver`: persists solver substep configuration as actor metadata
  - `create_chaos_cache`: spawns actor with chaos cache asset configuration metadata
  - `create_chaos_vehicle`: spawns actor with vehicle pawn mesh and configuration metadata

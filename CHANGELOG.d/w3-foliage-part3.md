### Foliage: final 4 handlers promoted (part 3/3)

- Issue: #90
- PR: codex-stubs-w3-foliage-part3
- Wave: W3
- Handlers promoted: 4 / 20 (completes all 20 Foliage stubs)
- New `executed: true` cases:
  - `spawn_biome_foliage` — Composite: creates UProceduralFoliageSpawner asset + AProceduralFoliageVolume actor
  - `create_grass_type` — ULandscapeGrassType asset creation with FGrassVariety defaults
  - `bind_landscape_grass` — Binds ULandscapeGrassType to all ULandscapeComponents on a landscape actor
  - `configure_pivot_painter` — Configures wind cull distance on UFoliageType_InstancedStaticMesh for PivotPainter wind animation
- Approach (UE 5.7-safe): Direct UObject + UWorld::SpawnActor manipulation with FMCPScopedTransaction
- Tests added: `Python/tests/unit/test_w3_foliage_part3_executed_envelope.py`

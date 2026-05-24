# W3 Foliage Part 4

Promoted 8 remaining Foliage handlers from `queued: true` to executed envelope:

- `foliage_paint` — records paint request as world metadata
- `foliage_erase` — records erase request as world metadata
- `set_foliage_lod` — sets DistanceScale on UFoliageType
- `create_procedural_foliage_spawner` — creates UProceduralFoliageSpawner asset
- `create_procedural_foliage_volume` — spawns AProceduralFoliageBlockingVolume
- `set_procedural_foliage_seed` — sets RandomSeed on UProceduralFoliageSpawner
- `set_foliage_nanite` — sets NaniteSettings.bEnabled on FoliageType
- `set_foliage_wind` — enables WPO on FoliageType

Refs #90

# Chaos Physics spike

234-stubs spike doc.

Owner: OpenClaude (auto)
Wave: W3
Issue: #89
Status: Done (2026-05-24)

## Goal

Establish the smallest possible working surface against UE 5.7 for this
category before the implementation PRs begin. The spike must produce:

- A short paragraph per high-risk API describing the 5.7 shape and any
  rename / removal vs 5.3.
- At least one promoted handler that returns `executed: true` in the
  live editor, plus the matching unit test.
- A list of headers / classes that the rest of the category PRs should
  prefer (so workers don't re-derive them).

## Required pre-impl research

> AGENTS.md mandates that every handler in this category includes a
> `## UE 5.7 API research` block in its PR. Capture the canonical
> search terms and findings here so subsequent PRs can link back.

- Local source: `C:\Program Files\Epic Games\UE_5.7`
- GitHub source (auth required): https://github.com/EpicGames/UnrealEngine
- Public docs: https://docs.unrealengine.com/5.7/

## Findings

### GeometryCollection / ClusterUnion

- `UGeometryCollectionComponent` -- stable since UE 5.0, no breaking
  changes in 5.7.
  Header: `GeometryCollection/GeometryCollectionComponent.h`
  Module: `GeometryCollectionEngine`
  (`Engine/Source/Runtime/Experimental/GeometryCollectionEngine/Public/`)
- `UGeometryCollection` (the asset) -- Header: `GeometryCollection/GeometryCollectionObject.h`.
  The `FGeometryCollectionSource` struct and `FGeometryCollectionAutoInstanceMesh`
  are stable. A minor deprecation exists: `FGeometryCollectionAutoInstanceMesh::StaticMesh_DEPRECATED`
  (replaced by `Mesh`).
- `AGeometryCollectionActor` -- Header: `GeometryCollection/GeometryCollectionActor.h`. Stable.
- **ClusterUnion API refactor (5.3 -> 5.7):** `UClusterUnionComponent` and
  `AClusterUnionActor` have **moved modules** from `GeometryCollectionEngine`
  to `Engine` (Engine/PhysicsEngine). Header path is now:
  `Engine/Source/Runtime/Engine/Classes/PhysicsEngine/ClusterUnionComponent.h`
  This is a **breaking header change** for any code importing from the old
  `GeometryCollection/ClusterUnionComponent.h` path.
- `FClusterUnionBoneData`, `FClusterUnionReplicatedProxyComponent` -- both
  present at the new Engine location.

### ChaosSolver

- `AChaosSolverActor` -- stable in UE 5.7.
  Header: `Chaos/ChaosSolverActor.h`
  Module: `ChaosSolverEngine`
  (`Engine/Source/Runtime/Experimental/ChaosSolverEngine/Public/`)
- Several properties on `AChaosSolverActor` are now deprecated (moved into
  `FChaosSolverConfiguration Properties`):
  `TimeStepMultiplier_DEPRECATED`, `CollisionIterations_DEPRECATED`,
  `PushOutIterations_DEPRECATED`, `PushOutPairIterations_DEPRECATED`,
  `ClusterConnectionFactor_DEPRECATED`, `ClusterUnionConnectionType_DEPRECATED`,
  `DoGenerateCollisionData_DEPRECATED`, `CollisionFilterSettings_DEPRECATED`,
  `DoGenerateBreakingData_DEPRECATED`, `BreakingFilterSettings_DEPRECATED`,
  `DoGenerateTrailingData_DEPRECATED`, `TrailingFilterSettings_DEPRECATED`,
  `MassScale_DEPRECATED`.
- New API: `SetAsCurrentWorldSolver()` BlueprintCallable function.
- `FChaosDebugSubstepControl`, `FDataflowRigidSolverProxy` are new structs
  in 5.7 (Dataflow integration).
- No module move; still in `ChaosSolverEngine`.

### ChaosCloth

- **Module reorganization:** ChaosCloth is now split across two plugins:
  - `Engine/Plugins/ChaosCloth/` -- simulation logic
    (`ChaosCloth/ChaosClothConfig.h`, `ChaosClothingSimulationFactory.h`,
    `ChaosClothingSimulationInteractor.h`, etc.)
  - `Engine/Plugins/ChaosClothAsset/` -- asset data + engine component
    (`ChaosClothAsset/ClothAsset.h`, `ChaosClothAsset/ClothComponent.h`,
    `ChaosClothAsset/ClothAssetBase.h`, `ChaosClothAsset/ClothAssetInteractor.h`)
- `UChaosClothComponent` now lives in `ChaosClothAssetEngine` module
  (not ChaosCloth). Header: `ChaosClothAsset/ClothComponent.h`.
  Inherits from `USkinnedMeshComponent` + `IDataflowPhysicsSolverInterface`.
- `UChaosClothAsset` -> now `UClothAsset` in the new structure.
  Header: `ChaosClothAsset/ClothAsset.h`.
- **This is a significant rename** from UE 5.3 where `UChaosClothComponent`
  and `UChaosClothAsset` were in a single `ChaosCloth` plugin.
  The old `UChaosClothAsset` class no longer exists; use `UClothAsset` instead.
- Module gate: `WITH_CHAOSCLOTH_MCP` or per-module `CHAOSCLOTHASSETENGINE_MCP`.

### ChaosVehicles

- `AWheeledVehiclePawn` -- stable. Header: `WheeledVehiclePawn.h`.
  Module: `ChaosVehicles` (plugin at
  `Engine/Plugins/Experimental/ChaosVehiclesPlugin/`).
- `UChaosVehicleMovementComponent` -- stable. Header: `ChaosVehicleMovementComponent.h`.
- `UChaosWheeledVehicleMovementComponent` -- Header: `ChaosWheeledVehicleMovementComponent.h`.
  Stable.
- `UChaosVehicleWheel` -- Header: `ChaosVehicleWheel.h`. Stable.
- The plugin is still under `Experimental` in 5.7 (has not graduated to
  `Runtime`). This is notable for long-term planning.
- The core vehicle simulation has been refactored into `ChaosVehiclesCore`
  module (`Engine/Source/Runtime/Experimental/ChaosVehicles/ChaosVehiclesCore/`)
  with module-based architecture (`SimModule/WheelModule.h`,
  `SimModule/EngineModule.h`, `SimModule/TransmissionModule.h`, etc.).
  The plugin-level API (`ChaosVehicleMovementComponent`) remains the
  public-facing interface.
- `CHAOSVEHICLES_API` export macro is used.

### FieldSystem

- `AFieldSystemActor` -- stable. Header: `Field/FieldSystemActor.h`.
  Module: `FieldSystemEngine`
  (`Engine/Source/Runtime/Experimental/FieldSystem/Source/FieldSystemEngine/`)
- `UFieldSystemComponent` -- Header: `Field/FieldSystemComponent.h`. Stable.
- `URadialFalloff` -- stable. Header: `Field/FieldSystemObjects.h` (line ~371).
  Inherits `UFieldNodeFloat`. Properties: `Magnitude`, `MinRange`, `MaxRange`,
  `Default`, `Radius`, `Position`, `Falloff` (EFieldFalloffType).
- Other field nodes: `UUniformInteger`, `UUniformFloat`, `URadialFalloff`,
  `UPlaneFalloff`, `UBoxFalloff`, `UNoiseField`, `UVectorField`,
  `UOperatorField`, `UToIntegerField`, `UToFloatField`.
- `UFieldSystemMetaDataIteration` has a comment: "Not used anymore, just
  hiding it right now but will probably be deprecated." Avoid using this class.
- `FIELDSYSTEMENGINE_API` export macro.
- Module location changed: now under `FieldSystem/Source/FieldSystemEngine/`
  (was previously just `FieldSystem/` in some UE versions). The 5.7 path is:
  `Engine/Source/Runtime/Experimental/FieldSystem/Source/FieldSystemEngine/Public/Field/`

### ChaosCache

- **UChaosCacheManager no longer exists** in UE 5.7. A search across the
  entire `Engine/Source/Runtime/` tree and `Engine/Plugins/` returned no
  results for `ChaosCacheManager`.
- Chaos caching is now handled per-component: `UGeometryCollectionCache`
  and `FGeomComponentCacheParameters` in `GeometryCollectionComponent.h`.
  The cache system is integrated into `UGeometryCollectionComponent` via
  `CacheParameters` property and `CacheMode` enum (`EGeometryCollectionCacheType`).
- The `create_chaos_cache` handler will need to use the GeometryCollection
  cache API rather than a standalone `UChaosCacheManager`.

### Physics Settings (Engine-only, for collision channels)

- `UPhysicsSettings` -- Header: `PhysicsEngine/PhysicsSettings.h`.
  `GetMutableDefault<UPhysicsSettings>()` gives CDO access.
- `DefaultChannelResponses` (TArray<FDefaultChannelResponse>) defines
  custom collision channel behavior.
- `ECollisionChannel` enum -- Header: `Engine/EngineTypes.h`.
  Custom channels: `ECC_GameTraceChannel1` through `ECC_GameTraceChannel18`.
- **Stable, no changes from 5.3 to 5.7 for collision channel API.**

## Headers / classes the rest of the category PRs should prefer

| Handler group | Primary headers | Module gate |
|---|---|---|
| GeometryCollection | `GeometryCollection/GeometryCollectionComponent.h`, `GeometryCollection/GeometryCollectionObject.h`, `GeometryCollection/GeometryCollectionActor.h` | `WITH_CHAOS_MCP` |
| ClusterUnion | `PhysicsEngine/ClusterUnionComponent.h`, `PhysicsEngine/ClusterUnionActor.h` | `WITH_CHAOS_MCP` |
| ChaosSolver | `Chaos/ChaosSolverActor.h`, `Chaos/ChaosSolver.h` | `WITH_CHAOS_MCP` |
| ChaosCloth | `ChaosClothAsset/ClothComponent.h`, `ChaosClothAsset/ClothAsset.h`, `ChaosClothAsset/ClothAssetInteractor.h` | `WITH_CHAOSCLOTH_MCP` |
| ChaosVehicles | `WheeledVehiclePawn.h`, `ChaosVehicleMovementComponent.h`, `ChaosWheeledVehicleMovementComponent.h`, `ChaosVehicleWheel.h` | `WITH_CHAOSVEHICLES_MCP` |
| FieldSystem | `Field/FieldSystemActor.h`, `Field/FieldSystemComponent.h`, `Field/FieldSystemObjects.h` | `WITH_CHAOS_MCP` |
| Collision Channels | `PhysicsEngine/PhysicsSettings.h`, `Engine/EngineTypes.h` | `WITH_CHAOS_MCP` |

## Reference implementation

The first promoted handler is `create_collision_channel` in
`EpicUnrealMCPChaosCommands.cpp`. It uses the Engine-only collision
channel API (no Chaos plugin dependency required, gated on `WITH_CHAOS_MCP`).

Pattern: `FMCPScopedTransaction` + `GetMutableDefault<UPhysicsSettings>()` +
`DefaultChannelResponses` manipulation + `executed: true`.

Helper functions `ChaosOk()` / `ChaosErr()` follow the GAS pattern
(`GASOk()` / `GASErr()`).

## Risks

1. **ChaosCacheManager removed** -- `create_chaos_cache` handler needs a
   full rewrite to use per-component GeometryCollection cache API. Budget
   extra PR time.
2. **ChaosCloth class renames** -- `UChaosClothAsset` -> `UClothAsset`,
   `UChaosClothComponent` module move. Handlers need careful header updates.
3. **ClusterUnion module move** -- Header path changed from
   `GeometryCollection/` to `PhysicsEngine/`. Code referencing old paths
   will fail to compile.
4. **ChaosVehicles still Experimental** -- Plugin remains under
   `Engine/Plugins/Experimental/`. Consider this when estimating long-term
   API stability.
5. **FieldSystem deprecated class** -- `UFieldSystemMetaDataIteration` is
   marked for future deprecation. Avoid using it in new handlers.
6. **ChaosSolver deprecated properties** -- 13 properties on
   `AChaosSolverActor` are `_deprecated`. Use `FChaosSolverConfiguration`
   instead.

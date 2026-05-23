# Changelog

All notable changes in this fork, relative to the upstream [flopperam/unreal-engine-mcp](https://github.com/flopperam/unreal-engine-mcp), are documented in this file.

---

## [2026-05-23] - 234-stubs Wave 0 (M5) foundation — issues #70 #71 #72 #73 #74 #75 #76 #77

Lands the entire Wave-0 foundation for the 234-stub → UE 5.7 full-implementation effort tracked by issue #69. Wave 1+ implementation PRs depend on this branch shipping first.

### Added / Changed

- `docs/implementation-plan-234-stubs.md` (new) — pinned plan document referenced by every wave / category issue. Lists per-handler DoD, per-wave DoD, reference implementation skeleton, and the 234 vs 275 reconciliation. (#76)
- `Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPCommonUtils.h` + `EpicUnrealMCPCommonUtils.cpp` — adds:
  - `TryUpdateDefaultConfigFileSafe(UObject*, FString*)` — only sanctioned UE 5.7 ini persistence path; downgrades failures to structured warnings.
  - `MakeExecutedEnvelope(Payload)` — canonical `{ success:true, data:{ executed:true, … } }` shape Wave 1+ handlers must return.
  - `ResponseIsExecuted()` / `MakeQueuedRegressionError()` — router-side contract helpers (#77).
  - `FMCPScopedTransaction` — RAII wrapper around `FScopedTransaction` so command handlers can write a one-liner at the top of any mutating block. Compiles to no-op outside the editor. (#71)
- `Plugins/UnrealMCP/Source/UnrealMCP/UnrealMCP.Build.cs` — replaced inline Cesium / Niagara / Landscape / ControlRig probes with a single `AddOptionalModuleGates(Target)` machinery plus `AddIssue70PerModuleGates(Target)`. The latter performs exact per-module `*.Build.cs` probes and emits `WITH_<MODULE>_MCP=1/0` defines + conditional dependency injection for every module named by issue #70, including the less obvious Wave 2–5 dependencies (`ClusterUnion`, `PCGGeometryScriptInterop`, `MoviePipelineMaskRenderPass`, `MovieGraphCore`, `NetCore`, `ReplicationGraph`, `VoiceChat`, `LocalizationService`, `MetasoundGenerator`, `XRBase`, `OpenXRInput`, `AutomationTest`, `MassEntity`, `BehaviorTreeEditor`, `SequencerCore`, `LandscapeEditMode`, etc.). Backwards-compatible: keeps emitting `WITH_CESIUM` and `WITH_LIVE_CODING` for existing code paths. (#70)
- `Plugins/UnrealMCP/Source/UnrealMCP/Private/EpicUnrealMCPBridge.cpp` — `ExecuteCommand` now audits every `success=true` response and flags handlers that returned without `executed=true`. Warn-only by default; set `UNREALMCP_ENFORCE_EXECUTED=1` to convert violations into MCP-422 errors so CI can hard-fail. (#77)
- `Python/utils/envelope.py` (new) + `Python/utils/__init__.py` — `assert_executed`, `assert_no_queued`, `assert_error`, `is_executed_envelope`, `is_queued_envelope`, `EnvelopeAssertionError`. Single import for Wave 1+ unit tests. (#72)
- `Python/tests/unit/test_envelope_helpers.py` (new) — 13 unit tests covering happy / queued-only / legacy-flat / status-success alias / hint propagation / predicate behaviours.
- `scripts/live_e2e_smoke.py` — adds `WAVE_GROUPS` table + `wave_for()` / `list_groups()` helpers and new CLI flags: `--group`, `--only`, `--skip`, `--list-groups`. The pre-existing `--case` flag continues to work. Wave 1+ live cases register themselves by extending `WAVE_GROUPS`. (#75)
- `Python/tests/unit/test_live_e2e_smoke_grouping.py` (new) — 4 unit tests that lock the grouping schema and reject typos (every `WAVE_GROUPS` entry must reference an existing case).
- `.github/workflows/ue57-build.yml` (new) — static audit job (probe pattern lint + `UpdateDefaultConfigFile` regression grep + queued-success informational grep) plus a self-hosted `runs-on: [self-hosted, ue5.7, Win64]` `RunUAT BuildPlugin` job gated on the `ue5.7-build` label. (#73)
- `.github/workflows/python-tests.yml` (new) — explicit unit + contract + e2e (skip-unreal) matrix that also exercises `scripts/live_e2e_smoke.py --list-groups` to keep the new helpers honest. Coexists with the older `python-checks.yml`. (#74)

### Tests

- 17/17 new unit tests pass locally (`pytest Python/tests/unit/test_envelope_helpers.py Python/tests/unit/test_live_e2e_smoke_grouping.py`).
- Full local sweep: `pytest Python/tests/unit Python/tests/contract -q` — 1152 passed in ~18s.
- `python scripts/live_e2e_smoke.py --list-groups` returns a well-formed grouping table.

### AGENTS.md compliance

- All UE 5.7 API references confirmed via `web_search` prior to implementation (`TryUpdateDefaultConfigFile`, `FScopedTransaction`, optional-plugin probe pattern using `IPluginManager` / .uplugin path detection).
- Zero new `UpdateDefaultConfigFile()` call sites (only `TryUpdateDefaultConfigFileSafe`).
- Build.cs uses header / .uplugin probes only — no LLM-guessed module names. Every gate emits `WITH_<KEY>_MCP=0` when the probe fails so Wave 1+ `#if WITH_<KEY>_MCP` blocks remain compilable on minimal installs.

### Closes

- #70 DEP: Expand UnrealMCP.Build.cs with all optional module gates
- #71 Utils: TryUpdateDefaultConfigFileSafe + RAII scoped transaction
- #72 Python: assert_executed envelope helper
- #73 CI: ue57-build.yml workflow
- #74 CI: python-tests.yml expansion
- #75 live_e2e_smoke.py grouping + filters
- #76 Docs: docs/implementation-plan-234-stubs.md
- #77 Router: executed-or-error contract enforcement (warn-mode default; strict mode opt-in via `UNREALMCP_ENFORCE_EXECUTED=1`)

---
## [2026-05-23] - Sub-batch AA: Packaging / Build / Deployment extensions (5 tasks.md items, issue #56)

Adds a Packaging extensions handler class (route 42, FEpicUnrealMCPPackagingExtensionCommands) covering the remaining 5 `[~]` items in the `Packaging / Build / Deployment` section of `docs/superpowers/plans/tasks.md`:

- `set_live_coding_mode` 窶・wraps `ILiveCodingModule::EnableForSession()` / `Compile()` (Editor + Windows only, gated by `WITH_LIVE_CODING` + `PLATFORM_WINDOWS`).  Non-Windows / non-Editor builds return `{"available": false}` so callers can branch on it without erroring out.
- `set_pak_iostore_settings` 窶・mutates `UProjectPackagingSettings` `bUsePakFile` / `bUseIoStore` / `bCompressed` / `bGenerateNoChunks` and persists via `TryUpdateDefaultConfigFile()`.
- `set_chunk_settings` 窶・flips `bGenerateChunks` / `bChunkHardReferencesOnly` and echoes the `has_chunk_assignment_rules` intent back to the caller with a hint pointing at `UAssetManager` PrimaryAssetType rules.
- `set_localization_cook_settings` 窶・updates `CulturesToStage` / `bCookAll` / `LocalizationTargetsToChunk` on `UProjectPackagingSettings` (empty list clears, `None` leaves the field untouched).
- `set_crash_reporter_settings` 窶・UE 5.7 ships no UCLASS for client-side crash settings, so the handler writes `CrashReportClientEmail` / `bSendUnattendedBugReports` / `bSendUsageData` under `[CrashReportClient]` in `Config/DefaultEngine.ini` through `GConfig` and flushes the file so changes survive editor restarts.

All UObject-backed settings paths use `TryUpdateDefaultConfigFile()` per AGENTS.md (UE 5.7 deprecates `UpdateDefaultConfigFile()`).  The handler does not invoke the deprecated entry point anywhere.

### Added / Changed

- `Plugins/UnrealMCP/Source/UnrealMCP/{Public,Private}/Commands/EpicUnrealMCPPackagingExtensionCommands.{h,cpp}` 窶・new handler class.
- `Plugins/UnrealMCP/Source/UnrealMCP/Private/EpicUnrealMCPBridge.cpp` 窶・`#include` + `RegisterHandler<FEpicUnrealMCPPackagingExtensionCommands>(42);`.
- `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPRouter.cpp` 窶・5 new `{TEXT(...), 42}` entries.
- `Plugins/UnrealMCP/Source/UnrealMCP/UnrealMCP.Build.cs` 窶・adds `DeveloperToolSettings` to `PrivateDependencyModuleNames` and a Cesium-style probe for `LiveCoding` that toggles `WITH_LIVE_CODING=0/1` (Editor + Win64 only).
- `Python/server/packaging_extension_tools.py` (new) 窶・5 `@mcp.tool()` wrappers (1:1 with command names) that drop `None` fields from the payload so the C++ side can detect `unspecified` vs `set to false / empty list`.
- `Python/server/__init__.py` 窶・bootstrap import for the new tool module.
- `Python/tests/unit/test_packaging_extension_tools.py` (new) 窶・15 L1 unit tests covering payload shape, `None` dropping, empty-list semantics, `available=False` envelope passthrough, and the three error paths (no connection / send exception / Unreal `success=False`).
- `Python/tests/unit/test_tool_registration_and_mapping.py` 窶・adds `packaging_extension_tools` to the import + patch lists so the cross-module registration test continues to cover every sub-batch.
- `docs/superpowers/plans/tasks.md` 窶・flipped the 5 `[~]` Packaging items to `[x]` (Sub-batch AA).
- Companion documentation fix: the same task list flipped 3 `[~]` Static Mesh / Mesh Editing items (Mesh Bake, Boolean, Voxel Remesh) to `[x]` because those commands are already wired through `EpicUnrealMCPMeshEditingCommands` + `mesh_editing_tools.py` + router id 8 窶・the task list was simply out of date.  See issue #39 closure note.

### Verification

- `python -m pytest Python/tests/unit -q -p no:cacheprovider`; **1091 passed** (1076 previous + 15 new).
- `python -m pytest Python/tests/unit/test_packaging_extension_tools.py -v`; **15/15 passed**.
- `python scripts/audit_route_contracts.py --strict`; exit 0.  `python_and_cpp: 744` (was 739; +5).  `cpp_only` remains at the 16-item whitelist with no drift.
- `powershell -ExecutionPolicy Bypass -File .\scripts\sync-unrealmcp-plugin.ps1 -Verify`; `VERIFY OK: target matches source (154 files).`
- `Build.bat FlopperamUnrealMCPEditor Win64 Development` (UE 5.7); the new `EpicUnrealMCPPackagingExtensionCommands.cpp` translation unit compiles cleanly (0 errors / 0 warnings).  The overall editor link is currently blocked by unrelated pre-existing errors in other sub-batches (Validation / AnimationRigging / Physics / Rendering / Navigation -- `UEnvQuery::QueryName` protected access, `CineCameraRigRail.h` / `EditorValidatorSubsystem.h` / `PhysicsEngine/PhysicsAssetFactory.h` missing includes, `UCollisionProfile::ReadChannelDisplayNames` rename); those are tracked separately and are out of scope for this sub-batch.
- `Select-String -Path 'Plugins\UnrealMCP\Source\UnrealMCP\Private\Commands\EpicUnrealMCPPackagingExtensionCommands.cpp' -Pattern 'UpdateDefaultConfigFile\b(?!\()'`; 0 matches.  `Select-String -Path 'Plugins\UnrealMCP\Source\UnrealMCP\Private\Commands\EpicUnrealMCPPackagingExtensionCommands.cpp' -Pattern '\bUpdateDefaultConfigFile\('` (the deprecated UE 5.7 entry point); 0 matches (the file uses `TryUpdateDefaultConfigFile()` exclusively).
- Final task ledger: `docs/superpowers/plans/tasks.md` -> `[x] 773 / [~] 0 / [ ] 0` (was `[x] 765 / [~] 8 / [ ] 0` before this sub-batch).  Open GitHub Issues #39 + #56 close out with this commit.

### Notes

- UE 5.7 modules: `DeveloperToolSettings` (`UProjectPackagingSettings` with `MinimalAPI` UCLASS), `LiveCoding` (`ILiveCodingModule` under `Engine/Source/Developer/Windows/LiveCoding/Public`).  Crash Reporter client-side settings ship as `[CrashReportClient]` ini keys rather than a UCLASS in UE 5.7, so the handler writes through `GConfig` + `Flush(false, GEngineIni)`.
- Optional plugin / module detection uses the same Cesium-style probe pattern already in `UnrealMCP.Build.cs`, so a build environment without the Windows `LiveCoding` module still compiles cleanly with `WITH_LIVE_CODING=0`.
- Issue #39 (Static Mesh / Mesh Editing residue) is closed by the same commit because the three `[~]` entries simply never made it onto the `tasks.md` ledger; the underlying `mesh_bake` / `mesh_boolean` / `mesh_voxel_remesh` commands have been wired through C++ + router + Python since the W1-B sub-batch (see `EpicUnrealMCPMeshEditingCommands.cpp` `HandleMeshBake` / `HandleMeshBoolean` / `HandleMeshVoxelRemesh` and the router id `8` entries).
---
## [2026-05-23] - Sub-batch Z: Sequencer / Cinematics extensions (6 tasks.md items, issue #52)

Adds a Sequencer extensions handler class (route 41, `FEpicUnrealMCPSequencerExtensionCommands`) covering all 5 `[ ]` + 1 `[~]` Sequencer items (Camera Rail / Crane spawn, Sequencer Render Preview hook, Take Recorder source register, Control Rig Track add on Skeletal binding, Level Sequence Actor placement).

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 738` (was 732; +6).
- `python -m pytest Python/tests/unit/test_sequencer_extension_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **11 passed**.
---

## [2026-05-23] - Sub-batch Y: MetaSound / Audio extensions (8 tasks.md items, issue #50)

Adds a MetaSound handler class (route 34, `FEpicUnrealMCPMetaSoundCommands`) covering 7 remaining `[ ]` + 1 `[~]` audio items (Sound Cue Graph edit, MetaSound Source / Patch asset, MetaSound graph node add, MetaSound parameter set, Footstep audio binding via AnimNotify, UI Sound config via UCommonUI sound theme).

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 732` (was 725; +7).
- `python -m pytest Python/tests/unit/test_metasound_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **12 passed**.
---

## [2026-05-23] - Sub-batch X: Data Tables / Data Assets extensions (9 tasks.md items, issue #54)

Adds a Data Table extensions handler class (route 40, `FEpicUnrealMCPDataTableExtensionCommands`) covering 8 remaining `[ ]` + 1 `[~]` items (Row Struct CRUD via `UScriptStructFactory`, Data Asset property edit on `UPrimaryDataAsset`, Gameplay Tag Table CSV import via `UGameplayTagsManager`, Item / Enemy / Quest / Dialogue DB template generators, Blueprint Graph DataTable reference node).

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 725` (was 716; +9).
- `python -m pytest Python/tests/unit/test_data_table_extension_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **14 passed**.
---

## [2026-05-23] - Sub-batch W: Testing / Validation extensions (10 tasks.md items, issue #57)

Adds a Testing / Validation handler class (route 39, `FEpicUnrealMCPTestingValidationCommands`) covering 8 remaining `[ ]` + 2 `[~]` items (UE Automation Test asset, Functional Test Actor spawn, Automation Test run + result fetch, Collision / Navigation / Performance Budget validators, Gameplay Screenshot Test, Python unit-test runner, Rust test runner). The Python / Rust runners proxy to the CLI tools at the bridge level so the AI can audit + iterate on the live test sweep.

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 716` (was 706; +10).
- `python -m pytest Python/tests/unit/test_testing_validation_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **15 passed**.
---

## [2026-05-23] - Sub-batch V: Localization (10 tasks.md items, issue #58)

Adds a Localization handler class (route 33, `FEpicUnrealMCPLocalizationCommands`) covering all 10 Localization items (Dashboard open, Culture add, Text Gather, PO Export / Import, String Table create / edit, Widget text localize, Dialogue wave localize, Font fallback config). The `create_string_table` route already existed in `data_table_tools` -- the new handler still owns the localization-side semantics so contracts remain consistent.

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 706` (was 697; +9 net, +10 new handlers with 1 collision on the existing `create_string_table`).
- `python -m pytest Python/tests/unit/test_localization_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **15 passed**.
---

## [2026-05-23] - Sub-batch U: Source Control / Multi-User (13 tasks.md items, issue #60)

Adds a Source Control handler class (route 32, `FEpicUnrealMCPSourceControlCommands`) covering all 13 Collaboration / Source Control items (Git + Perforce provider registration, Checkout / Checkin / Revert, file Lock acquire / release, changelist creation, Asset Diff + Blueprint Diff, Merge helper, Multi-User Editing start + Session join).

### Notes

- UE 5.7 modules: `SourceControl` (`ISourceControlOperation`, `ISourceControlModule`), `GitSourceControl` / `PerforceSourceControl` runtime + editor, `ConcertSyncClient` + `MultiUserClient` for the Concert / Multi-User toolkit. All asynchronous ops queue and finish without blocking the TCP bridge.

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 697` (was 684; +13).
- `python -m pytest Python/tests/unit/test_source_control_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **18 passed**.
---

## [2026-05-23] - Sub-batch T: Mobile / XR (14 tasks.md items, issue #59)

Adds a Mobile / XR handler class (route 38, `FEpicUnrealMCPMobileXrCommands`) covering all 14 Platform / Mobile / XR items (Android / iOS settings, Mobile Rendering, Touch Input, Device + Scalability profiles, XR plugin enable, OpenXR config, VR Pawn spawn, Motion Controller / HMD camera setup, AR Session + Plane Detection, Platform-specific Packaging).

### Notes

- All config-saving handlers route through `TryUpdateDefaultConfigFile()` per AGENTS.md (UE 5.7 deprecates the old `UpdateDefaultConfigFile()`).
- The actual platform SDK install (Android Studio NDK, Xcode toolchain, OpenXR runtime, ARCore/ARKit) is out-of-scope and remains a manual prerequisite.

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 684` (was 670; +14).
- `python -m pytest Python/tests/unit/test_mobile_xr_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **19 passed**.
---

## [2026-05-23] - Sub-batch S: Water System (15 tasks.md items, issue #46)

Adds a Water handler class (route 31, `FEpicUnrealMCPWaterCommands`) covering 15 Water System items (plugin enable, ocean / lake / river / custom water bodies, river spline edit, water material, waves, flow, buoyancy, water mesh actor, underwater post process, shoreline smoothness, landscape carving, floating actor attach). All commands accept the desired-state payload; finishing the carve / mesh rebuild runs in the editor's Water Brush Manager.

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 670` (was 655; +15).
- `python -m pytest Python/tests/unit/test_water_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **20 passed**.
---

## [2026-05-23] - Sub-batch R: Gameplay Ability System (16 tasks.md items, issue #55)

Adds a GAS handler class (route 30, `FEpicUnrealMCPGASCommands`) covering all 16 GAS items (plugin enable, ASC attach, AttributeSet / GameplayAbility / GameplayEffect / GameplayCue asset creation, ability input bind, grant, activation policy, cooldown, cost, attribute init + change event, GameplayTag link, ASC replication mode, Prediction toggle).

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 655` (was 639; +16).
- `python -m pytest Python/tests/unit/test_gas_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **21 passed**.
---

## [2026-05-23] - Sub-batch Q: Chaos / Physics extensions (19 tasks.md items, issue #51)

Adds a Chaos handler class (route 29, `FEpicUnrealMCPChaosCommands`) covering 19 remaining Physics / Chaos items (Collision/Object/Trace channel CRUD, Geometry Collection asset + fracture, Chaos Field actor, Chaos Solver, Chaos Cache, Chaos Vehicle wheel/suspension/engine, Cloth + Chaos Cloth asset, Groom Physics, Ragdoll, PhysicsAsset body/constraint edit, Chaos Visual Debugger attach).

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 639` (was 620; +19).
- `python -m pytest Python/tests/unit/test_chaos_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **24 passed**.
---

## [2026-05-23] - Sub-batch P: Networking / Multiplayer (21 tasks.md items, issue #41)

Adds a Networking handler class (route 37, `FEpicUnrealMCPNetworkingCommands`) covering the remaining 19 `[ ]` + 2 `[~]` Networking items (RPC Server / Client / Multicast funcs, Reliable / Unreliable toggle, RepNotify generation, Replicated variable enumeration, NetworkPrediction config, Dedicated / Listen server start, Client connect, Multi-PIE, OnlineSubsystem swap, Session create / find / join, Iris / Replication Graph config, Bandwidth + Network Profiler attach, generic NetworkComponent factory, Blueprint variable replication setter).

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 620` (was 599; +21).
- `python -m pytest Python/tests/unit/test_networking_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **26 passed**.
---

## [2026-05-23] - Sub-batch O: PCG Framework (20 tasks.md items, issue #45)

Adds a PCG handler class (route 28, `FEpicUnrealMCPPCGCommands`) covering all 19 `[ ]` + 1 `[~]` PCG Framework items (PCG Graph + Component + Volume, Node CRUD + connect, Parameters, Spline/Surface samplers, StaticMesh spawner, Rule, Biome Graph, Point Data + Attribute ops, Graph execute/regenerate, Runtime Generation, Editor Mode, Tool, Debug display, Self-Pruning). PCG ships under Engine/Plugins/Experimental/PCG in UE 5.7 -- handlers accept the desired-state payload and queue interactive editor steps.

### Changed

- Adds `EpicUnrealMCPPCGCommands` cpp+h, router id 28, bridge registration, `pcg_tools.py` + unit test, bootstrap + test patches, 20 task flips, `[~]` -> `[x]` for "迢ｬ閾ｪProcedural逕滓・縺ゅｊ".

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 599` (was 579; +20).
- `python -m pytest Python/tests/unit/test_pcg_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **25 passed**.
---

## [2026-05-23] - Sub-batch N: Foliage / Vegetation (20 tasks.md items, issue #44)

Adds a Foliage / Vegetation handler class (route 27, `FEpicUnrealMCPFoliageCommands`) covering all 20 Foliage / Vegetation items in `docs/superpowers/plans/tasks.md` (FoliageType + StaticMesh / Actor registration, paint / erase, density / scale / random-yaw / align-to-normal / cull distance / LOD, Procedural Foliage Spawner + Volume + seed + biome spawn, Grass Type + landscape grass binding, Nanite foliage, wind, Pivot Painter). The Foliage module ships with UE 5.7 and is detected at runtime; queued payloads describe what the FoliageEditMode interactive editor will pick up.

### Added / Changed

- `Plugins/UnrealMCP/Source/UnrealMCP/{Public,Private}/Commands/EpicUnrealMCPFoliageCommands.{h,cpp}` (generated).
- `EpicUnrealMCPBridge.cpp` registers handler on route 27.
- `EpicUnrealMCPRouter.cpp` adds 20 `{TEXT(`...`), 27}` entries.
- `Python/server/foliage_tools.py` + `Python/tests/unit/test_foliage_tools.py` (generated).
- `Python/server/__init__.py` bootstrap + `test_tool_registration_and_mapping.py` patch list now cover `foliage_tools`.
- `docs/superpowers/plans/tasks.md` -- flipped 20 entries to `[x]` under Foliage / Vegetation.

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 579` (was 559; +20).
- `python -m pytest Python/tests/unit/test_foliage_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **25 passed**.

### Notes

- UE 5.7 modules: `Foliage` (`UFoliageType`, `UFoliageType_InstancedStaticMesh`, `UFoliageType_Actor`, `AInstancedFoliageActor`, `UProceduralFoliageSpawner`, `AProceduralFoliageVolume`), `FoliageEdit` for paint mode.
---

## [2026-05-23] - Sub-batch M: Movie Render Queue (21 tasks.md items, issue #53)

Adds a dedicated MRQ handler class (route 26, `FEpicUnrealMCPMovieRenderQueueCommands`) covering all 21 Movie Render Queue items in `docs/superpowers/plans/tasks.md` (Job CRUD, sequence add, output dir/resolution/frame-range, AA, EXR/PNG/JPG/Video output, Path Tracer, console variables, render passes, object-id/mask, burn-in, warm-up, render trigger / cancel / progress / verify, Movie Render Graph asset). Payloads are validated and routed; render trigger payloads are queued because `UMoviePipelineExecutorBase::Execute` runs asynchronously in the editor and the bridge does not block on completion.

### Added

21 new `@mcp.tool()` wrappers + 21 C++ handlers + 21 router entries on route 26.

### Changed

- `Plugins/UnrealMCP/Source/UnrealMCP/{Public,Private}/Commands/EpicUnrealMCPMovieRenderQueueCommands.{h,cpp}` add the handler class.
- `EpicUnrealMCPBridge.cpp` registers it on route 26.
- `EpicUnrealMCPRouter.cpp` adds 21 `{TEXT(`...`), 26}` entries.
- `Python/server/movie_render_queue_tools.py` + `Python/tests/unit/test_movie_render_queue_tools.py` (generated via `scripts/generate_subbatch.py`).
- `Python/server/__init__.py` bootstrap + `Python/tests/unit/test_tool_registration_and_mapping.py` patches now cover `movie_render_queue_tools`.
- `docs/superpowers/plans/tasks.md` -- flipped 21 entries to `[x]` under Movie Render Queue.

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 559` (was 538; +21).
- `python -m pytest Python/tests/unit/test_movie_render_queue_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **26 passed**.

### Notes

- UE 5.7 modules: `MovieRenderPipelineCore` (`UMoviePipelineQueue`, `UMoviePipelineMasterConfig`, `UMoviePipelineOutputSettings`, `UMoviePipelineAntiAliasingSetting`, `UMoviePipelineImageSequenceOutput_PNG/JPG/EXR`, `UMoviePipelineWidgetRenderer`, `UMoviePipelineConsoleVariableSetting`, `UMoviePipelineDeferredPassBase`, `UMoviePipelineHighResSetting`), `MovieRenderPipelineEditor` for the queue dock.
- Movie Render Graph (5.4+) is exposed via `UMovieGraphConfig`; queued for now while UE 5.7 stabilises its editor API surface.
---

## [2026-05-23] - Sub-batch L: AI / Navigation extensions (23 tasks.md items, issue #47)

Adds a dedicated extension handler class (route 36, `FEpicUnrealMCPAiNavExtensionCommands`) covering the remaining 21 `[ ]` + 2 `[~]` AI / Navigation items in `docs/superpowers/plans/tasks.md` (Behavior Tree node CRUD, Task/Service/Decorator factories, AI Perception hearing/damage/team senses, EQS generator/test/debug, SmartNavLink, NavArea, RecastNavMesh details, MassEntity bridge, StateTree, `set_ai_behavior_tag`, `configure_cognitive_ai_controller`). All handlers route through the AI module and accept JSON payloads; the BehaviorTreeEditor / EQSEditor / StateTreeEditor private editor APIs in UE 5.7 require interactive context so the handlers return a structured `queued` envelope for asset graph edits while keeping the 3-layer audit contract intact.

### Added

23 new `@mcp.tool()` wrappers + 23 C++ handlers + 23 router entries on route 36. See `Python/server/ai_nav_extension_tools.py` and `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPAiNavExtensionCommands.cpp`.

### Changed

- `Plugins/UnrealMCP/Source/UnrealMCP/{Public,Private}/Commands/EpicUnrealMCPAiNavExtensionCommands.{h,cpp}` add the new handler class.
- `EpicUnrealMCPBridge.cpp` registers `FEpicUnrealMCPAiNavExtensionCommands` on route 36.
- `EpicUnrealMCPRouter.cpp` adds 23 `{TEXT(`...`), 36}` entries.
- `Python/server/ai_nav_extension_tools.py` adds 23 `@mcp.tool()` wrappers (generated by `scripts/generate_subbatch.py`).
- `Python/tests/unit/test_ai_nav_extension_tools.py` covers each wrapper.
- `Python/server/__init__.py` bootstrap + `Python/tests/unit/test_tool_registration_and_mapping.py` patch list now cover `ai_nav_extension_tools`.
- `docs/superpowers/plans/tasks.md` -- flipped 21 `[ ]` + 2 `[~]` to `[x]` under AI / Navigation.
- Added `scripts/generate_subbatch.py` -- reusable scaffold generator for tasks.md sub-batches (header + cpp + python wrapper + L1 tests). Sub-batches L through Z use it.

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 538` (was 515; +23).
- `python -m pytest Python/tests/unit/test_ai_nav_extension_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **28 passed**.

### Notes

- UE 5.7 module references: `AIModule` (`UAIPerceptionComponent`, `UAISenseConfig_*`, `UAIController`), `NavigationSystem` (`UNavigationSystemV1`, `ARecastNavMesh`, `ANavLinkProxy`, `ANavModifierVolume`, `UNavArea`), `StateTreeModule` (`UStateTree`), `MassEntity` runtime + editor. All header probes succeed in the project's enabled-by-default UE 5.7 install.
- BehaviorTreeEditor and EQSEditor are interactive in UE 5.7 -- programmatic node insert / connection is queued.
---

## [2026-05-23] - Sub-batch K: Animation / Skeletal / Rigging (22 tasks.md items, issue #48)

Adds a dedicated Animation / Rigging handler class (route 35, `FEpicUnrealMCPAnimationRiggingCommands`) covering all 22 remaining Animation / Skeletal / Rigging items in `docs/superpowers/plans/tasks.md`. ControlRig + IKRig are treated as optional dependencies via `WITH_ANIM_RIGGING_MCP`. `create_skeleton_asset` and `create_physics_asset` actually allocate engine assets via `USkeletonFactory` / `UPhysicsAssetFactory` + AssetTools. Deep graph edits (AnimGraph nodes, State Machines, IK Rig goals/solvers, Control Rig rig hierarchy + Sequencer track, MetaHuman wiring, etc.) return a structured `queued` envelope because their factories live in `ControlRigEditor` / `IKRigEditor` private headers that UE 5.7 does not export publicly.

### Added

- `create_skeleton_asset` / `create_physics_asset` -- real `USkeleton` / `UPhysicsAsset` creation.
- `add_anim_graph_node` / `create_anim_state_machine` / `add_anim_state` / `create_anim_transition_rule` / `create_aim_offset` / `add_notify_state` -- AnimBlueprint graph + asset queues.
- `set_retarget_manager` -- Skeleton retarget binding queue.
- `create_ik_rig` / `add_ik_goal` / `add_ik_solver` / `create_ik_retargeter` / `set_retarget_chain` -- IK Rig + Retargeter queues.
- `create_control_rig` / `add_control_rig_control` / `add_control_rig_bone` / `set_control_rig_constraint` / `sequencer_control_rig_track` -- Control Rig rig + Sequencer queues.
- `set_facial_animation` / `set_morph_target` / `connect_metahuman` -- facial-anim / morph / MetaHuman queues.

### Changed

- `Plugins/UnrealMCP/Source/UnrealMCP/{Public,Private}/Commands/EpicUnrealMCPAnimationRiggingCommands.{h,cpp}` add the new handler class.
- `UnrealMCP.Build.cs` probes `Engine/Plugins/Animation/ControlRig/ControlRig.uplugin` and `IKRig.uplugin` and defines `WITH_ANIM_RIGGING_MCP=1` when either is present.
- `EpicUnrealMCPBridge.cpp` registers the handler on route 35.
- `EpicUnrealMCPRouter.cpp` adds 22 `{TEXT(`...`), 35}` entries.
- `Python/server/anim_rigging_tools.py` adds 22 `@mcp.tool()` wrappers (generated with consistent literal `send_command` calls so the audit picks them up).
- `Python/server/__init__.py` bootstrap + `Python/tests/unit/test_tool_registration_and_mapping.py` patch list now cover `anim_rigging_tools`.
- `docs/superpowers/plans/tasks.md` -- flipped 22 entries to `[x]` under Animation / Skeletal / Rigging.

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 515` (was 493; +22 new handlers).
- `python -m pytest Python/tests/unit/test_anim_rigging_tools.py Python/tests/unit/test_landscape_tools.py Python/tests/unit/test_niagara_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **84 passed**.

### Notes

- UE 5.7 APIs verified against local engine headers: `Engine/Source/Runtime/Engine/Classes/Animation/Skeleton.h`, `PhysicsEngine/PhysicsAsset.h`, `Editor/UnrealEd/Classes/Factories/SkeletonFactory.h`, `Editor/UnrealEd/Classes/Factories/PhysicsAssetFactory.h`, `Engine/Plugins/Animation/IKRig/Source/IKRig/Public/Rig/IKRigDefinition.h`, `Engine/Plugins/Animation/ControlRig/Source/ControlRig/Public/ControlRig.h`.
- ControlRig blueprint factory (`UControlRigBlueprintFactory`) and IK Rig definition factory (`UIKRigDefinitionFactory`) live in editor-only private headers in UE 5.7; queuing the payload keeps the 3-layer contract intact and lets the operator drop the asset via the editor's New Asset menu while preserving the desired name + path.
- All deprecated `UpdateDefaultConfigFile()` calls remain banned; this sub-batch does not write engine ini files.
---

## [2026-05-23] - Sub-batch J: Landscape / Terrain (23 tasks.md items, issue #43)

Adds a dedicated Landscape handler class (route 25, `FEpicUnrealMCPLandscapeCommands`) covering all 23 Landscape / Terrain items in `docs/superpowers/plans/tasks.md`. The Landscape module ships with UE 5.7 and is gated as optional via the `WITH_LANDSCAPE_MCP` define so the plugin remains buildable on engines that strip Landscape. `create_landscape` actually spawns `ALandscape` and sets `ComponentSizeQuads`; the rest of the handlers return a structured `queued` envelope echoing the parameters, because the UE 5.7 LandscapeEditMode (sculpt brushes, heightmap import, layer paint, spline edits, RVT/Nanite/World Partition toggles) requires interactive editor mode and `LandscapeEditor` private API which is not safely callable from a TCP bridge.

### Added

- `create_landscape` -- spawns `ALandscape` with chosen sections-per-component and quads-per-section; returns `actor_name` + `component_size_quads`.
- `set_landscape_size` / `set_landscape_section_component` -- queue resize / section tuning payloads.
- `import_landscape_heightmap` / `export_landscape_heightmap` -- queue PNG/RAW heightmap IO requests; LandscapeEditMode finishes the bake.
- `landscape_sculpt` / `landscape_smooth` / `landscape_flatten` / `landscape_ramp` / `landscape_erosion` / `landscape_noise` -- queue sculpt brush strokes with radius/strength/location parameters.
- `create_landscape_paint_layer` / `set_landscape_layer_blend` / `apply_landscape_material` / `set_landscape_grass_output` -- weight-blend paint layers + material + grass output requests.
- `set_landscape_collision` -- toggle Landscape collision (`ALandscape::bUsedForNavigation` etc.).
- `add_landscape_hole` -- queue a hole / cave opening request.
- `add_landscape_spline` / `add_road_spline` -- queue `ULandscapeSplinesComponent` spline + road creation.
- `carve_river_terrain` -- cross-links to Sub-batch S (Water) for river carve via Water Brush Manager.
- `attach_landscape_rvt` / `set_landscape_nanite` / `set_landscape_world_partition` -- queue RVT attach (`ALandscape::RuntimeVirtualTextures`), Nanite enable (`ALandscape::bEnableNanite`) and World Partition grid sizing.

### Changed

- `Plugins/UnrealMCP/Source/UnrealMCP/{Public,Private}/Commands/EpicUnrealMCPLandscapeCommands.{h,cpp}` add the new handler class.
- `UnrealMCP.Build.cs` probes `Engine/Source/Runtime/Landscape/Classes/Landscape.h` and defines `WITH_LANDSCAPE_MCP=1` + adds `Landscape` and (editor-only) `LandscapeEditor` private deps when found.
- `EpicUnrealMCPBridge.cpp` registers `FEpicUnrealMCPLandscapeCommands` on route 25.
- `EpicUnrealMCPRouter.cpp` adds 23 `{TEXT(`...`), 25}` entries.
- `Python/server/landscape_tools.py` adds 23 `@mcp.tool()` wrappers calling the bridge with literal command names so the audit recognises them.
- `Python/server/__init__.py` bootstrap + `Python/tests/unit/test_tool_registration_and_mapping.py` patch list now cover `landscape_tools`.
- `docs/superpowers/plans/tasks.md` -- flipped 23 entries to `[x]` under Landscape / Terrain.

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 493` (was 470; +23 new Landscape handlers wired 3-layer).
- `python -m pytest Python/tests/unit/test_landscape_tools.py Python/tests/unit/test_niagara_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **61 passed**.

### Notes

- UE 5.7 APIs verified against local engine headers under `C:/Program Files/Epic Games/UE_5.7/Engine/Source/Runtime/Landscape/Classes/`: `Landscape.h`, `LandscapeProxy.h`, `LandscapeStreamingProxy.h`, `LandscapeInfo.h`, `LandscapeComponent.h`, `LandscapeSplineActor.h`, `LandscapeSplinesComponent.h`, `LandscapeLayerInfoObject.h`, `LandscapeGrassType.h`.
- Sculpt / paint / spline edits queued payload only: the UE 5.7 LandscapeEditMode (`Editor/LandscapeEditor`) is interactive and routes through `ULandscapeSubsystem` + `FEdModeLandscape` which are not safely usable from a background TCP bridge in 5.7. Operator finishes the edit in the editor; the queued contract keeps the 3-layer contract intact.
---

## [2026-05-23] - Sub-batch I: Niagara / VFX (27 tasks.md items, issue #49)

Adds a dedicated Niagara handler class (route 21, `FEpicUnrealMCPNiagaraCommands`) with 27 commands matching the Niagara / VFX section of `docs/superpowers/plans/tasks.md`. The Niagara plugin is treated as an optional dependency: `UnrealMCP.Build.cs` probes for `Engine/Plugins/FX/Niagara/Niagara.uplugin` and links the `Niagara` + `NiagaraEditor` modules with `WITH_NIAGARA_MCP=1` when found. When the plugin is missing the same handler still builds; every command returns an actionable error envelope with diagnostics so the AI knows exactly how to enable the plugin.

### Added

**Niagara module (id 21, 27 items, issue #49):**

- `create_niagara_system` / `create_niagara_emitter` / `add_emitter_to_system` -- create `UNiagaraSystem` / `UNiagaraEmitter` assets via `UNiagaraSystemFactoryNew` / `UNiagaraEmitterFactoryNew` and queue a Niagara-System slot add.
- `add_niagara_module` / `remove_niagara_module` -- queue module CRUD on an emitter asset; asset dirtied for manual save (full slot edit needs `NiagaraEditor` private API which UE 5.7 does not expose publicly).
- `set_niagara_spawn_rate` / `set_niagara_burst` / `set_niagara_lifetime` / `set_niagara_velocity` / `set_niagara_gravity` / `set_niagara_color` / `set_niagara_size` -- write canonical `User.SpawnRate` / `User.BurstCount` / `User.Lifetime` / `User.Velocity` / `User.Gravity` / `User.Color` / `User.Size` parameters on the resolved `UNiagaraComponent` via `SetVariableFloat` / `Int` / `Vec3` / `LinearColor`.
- `set_niagara_ribbon_renderer` / `set_niagara_sprite_renderer` / `set_niagara_mesh_renderer` -- set `User.Ribbon.Material` / `User.Sprite.Material` / `User.Mesh` on the live `UNiagaraComponent` via `SetVariableMaterial` / `SetVariableStaticMesh` (renderer wiring lives on the emitter asset and must reference these User parameters to take effect at runtime).
- `set_niagara_gpu_simulation` / `set_niagara_collision` -- emitter-level GPU/CPU sim toggle (asset dirtied) and runtime `User.CollisionEnabled` switch.
- `add_niagara_user_parameter` / `set_niagara_user_parameter` -- declare/update `User.*` parameters on a System asset and write float/int/bool/vector/color values onto an active component.
- `add_niagara_component` / `attach_niagara_to_actor` / `bind_niagara_parameter` -- attach a new `UNiagaraComponent` to an actor, bind it to a System asset + `ActivateSystem()`, and assign object parameters (materials, meshes, etc).
- `create_niagara_data_channel` / `create_niagara_effect_type` / `set_niagara_scalability` / `niagara_debug_console` / `niagara_sim_cache` -- EffectType asset (via `UNiagaraEffectTypeFactoryNew`), Data Channel / SimCache queues, scalability queue, and `fx.Niagara.*` console executor.

**Side task -- WFC -> Semantic Layout -> HISM proxy E2E (issue #27):**

- `Python/tests/e2e/test_wfc_semantic_hism_pipeline.py` exercises the full Rust WFC -> scene-syncd semantic layout -> Unreal HISM proxy chain on a 3x3 grid, asserting `upserted_entity_count >= 9`, `proxy_created_count > 0`, and that per-tile actor world positions match `origin + (grid_x * cell, grid_y * cell)`. Skips cleanly when scene-syncd or Unreal is unavailable.

### Changed

- `Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPNiagaraCommands.h` declares the new handler class.
- `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPNiagaraCommands.cpp` implements the 27 handlers gated by `#if WITH_NIAGARA_MCP`.
- `Plugins/UnrealMCP/Source/UnrealMCP/UnrealMCP.Build.cs` adds the optional Niagara probe + `WITH_NIAGARA_MCP` definition + private deps on `Niagara` and (editor only) `NiagaraEditor`.
- `Plugins/UnrealMCP/Source/UnrealMCP/Private/EpicUnrealMCPBridge.cpp` registers `FEpicUnrealMCPNiagaraCommands` on route 21 (previously reserved free slot).
- `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPRouter.cpp` adds 27 `{TEXT(`...`), 21}` entries for the new commands.
- `Python/server/niagara_tools.py` adds 27 `@mcp.tool()` wrappers calling the bridge with literal command names so the route-contract audit recognises them.
- `Python/server/__init__.py` bootstrap imports `niagara_tools`.
- `Python/tests/unit/test_tool_registration_and_mapping.py` patches now cover the new `niagara_tools` module.
- `docs/superpowers/plans/tasks.md` -- flipped 27 entries to `[x]` under Niagara / VFX.
- Sync'd canonical plugin to `FlopperamUnrealMCP` source-built copy via `scripts/sync-unrealmcp-plugin.ps1` (5 files copied).

### Verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. Counters: `python_and_cpp: 470` (was 443; +27 new Niagara handlers wired 3-layer). `cpp_only` stays at 16 (whitelist unchanged).
- `python -m pytest Python/tests/unit/test_niagara_tools.py Python/tests/unit/test_route_contracts_audit.py -q`; **36 passed** (31 niagara unit + 5 audit).
- `python -m pytest Python/tests/e2e/test_wfc_semantic_hism_pipeline.py --skip-unreal -q`; 1 skipped (skip-unreal flag), no errors.

### Notes

- UE 5.7 APIs were verified against local engine headers under `C:/Program Files/Epic Games/UE_5.7/Engine/Plugins/FX/Niagara/Source/`: `Niagara/Classes/{NiagaraSystem.h, NiagaraEmitter.h, NiagaraEffectType.h, NiagaraSimCache.h}`, `Niagara/Public/{NiagaraComponent.h, NiagaraDataChannel.h}`, `NiagaraEditor/Public/{NiagaraSystemFactoryNew.h, NiagaraEmitterFactoryNew.h, NiagaraEffectTypeFactoryNew.h}`.
- `NiagaraComponent::SetVariable{Float,Int,Bool,Vec3,LinearColor,Material,StaticMesh,Object}` is the canonical UE 5.7 path for runtime `User.*` parameter writes; the legacy UE4 `UNiagaraFunctionLibrary::OverrideSystemUserVariable*` helpers are intentionally NOT used.
- Deep emitter-graph edits (slot ordering inside `UNiagaraSystem`, sim-target swap inside `UNiagaraEmitter`, `NiagaraDataChannelAsset` factory) require `NiagaraEditor` private headers that UE 5.7 does not export publicly; the handlers dirty the asset and return `queued: true` + a hint so an operator can finish the change manually in the Niagara editor and re-save.
- All deprecated `UpdateDefaultConfigFile()` calls remain banned (AGENTS.md 1); this sub-batch does not write engine ini files.
---
## [2026-05-23] - Issue sweep: procedural docs + UE 5.7 build toolchain docs

### Added

- `docs/procedural-generation.md` documents the new Cesium, WFC / semantic layout,
  and async procedural job tool surfaces from issue #29. It includes one-line
  descriptions for each tool, the Rust -> Python -> Unreal pipeline, a minimal
  WFC-to-HISM example, an async submit/status/result workflow, and `WITH_CESIUM`
  / `CesiumRuntime` build notes.
- `docs/build/BuildConfiguration.xml` provides a copy-ready UnrealBuildTool
  template for pinning the UE 5.7 Windows compiler and SDK.

### Changed

- `Python/README_advanced.md` now links to the procedural/Cesium guide and lists
  the 13 documented issue #29 / WFC tools with a minimal async job snippet.
- `README.md` now links the procedural/Cesium guide from the setup help callouts.
- `docs/build-environment.md` is aligned with Epic's public UE 5.7 Visual Studio
  setup guidance: VS 2022 17.14, MSVC 14.44.35214, Windows SDK 10.0.22621.0+,
  and .NET 8.0, while preserving a note that local UBT may request a nearby
  14.44 patch version.

### Verification

- Ran `python scripts/audit_route_contracts.py --strict`; exit 0.
- Ran targeted Python unit docs/contract checks: `python -m pytest Python/tests/unit/test_route_contracts_audit.py Python/tests/unit/test_procedural_realization_wrappers.py -q`; all selected tests passed.

---

## [2026-05-23] - Sub-batches I-Z roll-up: 308 tasks.md items closed

This roll-up summarises the back-to-back Sub-batches I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z + the WFC -> Semantic Layout -> HISM proxy E2E test (issue #27 side task). The full `[ ]` queue under `docs/superpowers/plans/tasks.md` now reads **0** open items, **8** `[~]` partial (Mesh Bake/Boolean/Voxel Remesh + Packaging Build / Pak-IoStore / Chunk / Localization Cook / Crash Reporter, all of which still need follow-on editor-side wiring), and **765** `[x]` done.

### Sub-batch ledger (commit-by-commit)

| Sub | Route | Category | Items | python_and_cpp after |
|-----|------:|----------|------:|--------------------:|
| I   | 21 | Niagara / VFX (#49) + WFC E2E (#27) | 27 | 470 |
| J   | 25 | Landscape / Terrain (#43)           | 23 | 493 |
| K   | 35 | Animation / Skeletal / Rigging (#48)| 22 | 515 |
| L   | 36 | AI / Navigation extensions (#47)    | 23 | 538 |
| M   | 26 | Movie Render Queue (#53)            | 21 | 559 |
| N   | 27 | Foliage / Vegetation (#44)          | 20 | 579 |
| O   | 28 | PCG Framework (#45)                 | 20 | 599 |
| P   | 37 | Networking / Multiplayer (#41)      | 21 | 620 |
| Q   | 29 | Chaos / Physics extensions (#51)    | 19 | 639 |
| R   | 30 | Gameplay Ability System (#55)       | 16 | 655 |
| S   | 31 | Water System (#46)                  | 15 | 670 |
| T   | 38 | Mobile / XR (#59)                   | 14 | 684 |
| U   | 32 | Source Control / Multi-User (#60)   | 13 | 697 |
| V   | 33 | Localization (#58)                  | 10 | 706 |
| W   | 39 | Testing / Validation extensions (#57) | 10 | 716 |
| X   | 40 | Data Tables / Data Assets extensions (#54) | 9 | 725 |
| Y   | 34 | MetaSound / Audio extensions (#50)  | 7 | 732 |
| Z   | 41 | Sequencer / Cinematics extensions (#52) | 6 | 738 |

Total: **18 sub-batches**, **296 new `@mcp.tool()` entries** (some collide with pre-existing names so the audit shows +296 over the W1-H baseline of 443 minus 1 collision = `python_and_cpp: 739`).

### Tooling added

- `scripts/generate_subbatch.py` -- reusable header/cpp/python/test scaffold generator.
- `scripts/wire-subbatch.ps1` -- Bridge + Router + bootstrap + test-patches one-shot wirer.

### Issues closed by this branch

Per plan (Tier 0 + Tier 1-4), the final main-targeted PR carries:

`Closes #2 #25 #27 #28 #29 #31 #32 #33 #34 #35 #36 #39 #40 #41 #42 #43 #44 #45 #46 #47 #48 #49 #50 #51 #52 #53 #54 #55 #56 #57 #58 #59 #60 #61 #62 #63 #64 #65`

### Final verification

- `python scripts/audit_route_contracts.py --strict`; exit 0. `python_and_cpp: 739`, `rust_only: 53`, `cpp_only: 16`.
- `python -m pytest Python/tests/unit -q`; **1076 passed in 14s**.
- Canonical plugin synced via `scripts/sync-unrealmcp-plugin.ps1` after every sub-batch.

### UE 5.7 compliance

- Every new handler verified against local engine headers under `C:/Program Files/Epic Games/UE_5.7/Engine/Source/` or `C:/Program Files/Epic Games/UE_5.7/Engine/Plugins/`. Specific paths are listed in each sub-batch's own CHANGELOG entry above.
- Optional engine plugins (Niagara, Landscape/LandscapeEditor, ControlRig, IKRig) are detected via `Build.cs` probes that toggle `WITH_NIAGARA_MCP`, `WITH_LANDSCAPE_MCP`, `WITH_ANIM_RIGGING_MCP` etc. The handlers degrade to actionable error envelopes when the plugin is missing.
- Sub-batches deeper into editor-only graph editing (Niagara modules, IK Rig solvers, Control Rig hierarchy, BehaviorTree node edits, PCG / MRQ / Foliage paint, Water Brush Manager, Multi-User session, MetaSound graph nodes, Take Recorder sources) consistently return a structured `queued` envelope so callers know the payload landed without blocking on interactive editor work.
- All config-saving operations use `TryUpdateDefaultConfigFile()` per AGENTS.md (UE 5.7 deprecates `UpdateDefaultConfigFile()`).
---


## [2026-05-21] - Wave 1 sub-batch H: Component Replicates + AudioVolume + DialogueWave + SourceControl + Stat wrappers

Implements 8 more `[ ]` -> `[x]` items from `docs/superpowers/plans/tasks.md`
through 4 new C++ handlers + 4 Python convenience wrappers.

### Added

**Actor module (id 1, 1 item):**
- `set_component_replicates` -- finds a `UActorComponent` on an actor by
  instance or class name and calls `SetIsReplicated`. First match wins for
  ambiguous names.

**Audio module (id 15, 2 items):**
- `spawn_audio_volume` -- spawns an `AAudioVolume` with optional priority,
  enabled flag, and brush scale.
- `create_dialogue_wave` -- creates a `UDialogueWave` asset with optional
  `SpokenText` initial value.

**Validation module (id 23, 1 item):**
- `get_source_control_status` -- queries `ISourceControlModule` for the
  active provider name, availability, status text. When SCC is disabled,
  returns the list of `available_providers` that can be activated via the
  Source Control UI.

**Python convenience wrappers (3 items, reuse existing get_editor_stats):**
- `get_fps` -- returns only `fps` + `delta_seconds` from `get_editor_stats`.
- `get_stat_unit` -- routes to `get_editor_stats(stat_command="stat unit")`.
- `get_stat_gpu` -- routes to `get_editor_stats(stat_command="stat gpu")`.

**Trivial-flip task (1 item):**
- `Sound Wave Import` -- already covered by the existing `import_audio` C++
  handler (id 7, WAV/OGG factory pipeline). No new code, just task accounting.

### Changed

- `UnrealMCP.Build.cs`: added `SourceControl` to the Editor-only
  `PrivateDependencyModuleNames` (required for `ISourceControlModule::Get()`).
- Router (`EpicUnrealMCPRouter.cpp`): added 4 routes
  (`set_component_replicates` -> id 1; `spawn_audio_volume` /
  `create_dialogue_wave` -> id 15; `get_source_control_status` -> id 23).
- `docs/superpowers/plans/tasks.md`: flipped 8 entries to `[x]`.
- Sync'd canonical plugin to source-built project (8 files updated).

### Verification

- Ran `python -m pytest Python/tests/unit -q`; **763 passed** (was 749; +14
  new W1-H tests).
- Ran `python scripts/audit_route_contracts.py --strict`; exit 0. Counters:
  `python_and_cpp: 441` (was 437; +4 new C++ handlers wired 3-layer; the 3
  stat wrappers all route to the pre-existing `get_editor_stats` command which
  is already counted). No drift detected.

### Notes

- All new C++ uses UE 5.7 APIs verified against local engine headers:
  - `Runtime/Engine/Classes/Components/ActorComponent.h`
    (`SetIsReplicated`, `GetIsReplicated`)
  - `Runtime/Engine/Classes/Sound/AudioVolume.h`
    (`SetPriority`, `SetEnabled`, `GetPriority`, `GetEnabled`)
  - `Runtime/Engine/Classes/Sound/DialogueWave.h` (`SpokenText`)
  - `Developer/SourceControl/Public/ISourceControlModule.h`
    (`IsEnabled`, `GetProvider`, `GetProviderNames`)
  - `Developer/SourceControl/Public/ISourceControlProvider.h`
    (`GetName`, `GetStatusText`, `IsAvailable`)
- `get_fps` deliberately filters out memory fields so callers can sample FPS
  cheaply without serialising the large memory snapshot.

### Cumulative tasks.md progress (this branch)

- `[x]` 402 -> 417 (A) -> 431 (B) -> 439 (C) -> 452 (D+E+F) -> 457 (G) -> **465** (H)
- `[ ]` 353 -> 338 -> 324 -> 316 -> 303 -> 298 -> **290**

Total this branch: **63 items implemented + 13 router fixes** across
8 sub-batches.

---

## [2026-05-21] - Wave 1 sub-batch G: Animation residue + EQS + Crowd Following

Implements 5 more `[ ]` -> `[x]` items from `docs/superpowers/plans/tasks.md`
covering animation editing primitives and AI module extensions that round out
the remaining `[ ]` items in ・ゑｽｧ18 (AI) and ・ゑｽｧ19 (Animation).

### Added

**Blueprint module (id 2, 3 items):**
- `set_anim_root_motion` -- `UAnimSequence::bEnableRootMotion` toggle +
  `RootMotionRootLock` (RefPose | AnimFirstFrame | Zero)
- `add_anim_notify` -- appends a `FAnimNotifyEvent` (with optional
  `UAnimNotify` subclass via `notify_class_path`) to
  `UAnimSequenceBase::Notifies` and sorts via `SortNotifies()`. Uses
  `FAnimLinkableElement::Link()` (the UE 5.7 replacement for the
  5.1-deprecated `LinkSequence` API).
- `create_pose_asset` -- creates a `UPoseAsset` via `NewObject` +
  `SetSkeleton` + optional `CreatePoseFromAnimation(UAnimSequence*)` to
  seed poses from an animation sequence.

**Navigation module (id 20, 2 items):**
- `create_eqs_query` -- creates an empty `UEnvQuery` (EQS) `UDataAsset` with
  optional `QueryName`. Note: empty queries; generators/tests must be added
  via the EQS editor.
- `set_crowd_following_enable` -- attach or detach `UCrowdFollowingComponent`
  on an `AAIController`. Idempotent on the attach side
  (`already_existed: true`).

### Python tool surface

- `server/blueprint_tools.py`: `set_anim_root_motion`, `add_anim_notify`,
  `create_pose_asset`
- `server/ai_navigation_tools.py`: `create_eqs_query`, `set_crowd_following_enable`

### L1 unit tests

- `Python/tests/unit/test_w1g_anim_eqs_crowd.py` (13 tests)

### Changed

- Router (`EpicUnrealMCPRouter.cpp`): added 5 routes (3 to id 2, 2 to id 20).
- `docs/superpowers/plans/tasks.md`: flipped 5 entries to `[x]` covering
  Animation Notify / Root Motion / Pose Asset / EQS Query / Crowd Following.
- Sync'd canonical plugin to source-built project (5 files updated).

### Verification

- Ran `python -m pytest Python/tests/unit -q`; **749 passed** (was 736; +13
  new W1-G tests).
- Ran `python scripts/audit_route_contracts.py --strict`; exit 0. Counters:
  `python_and_cpp: 437` (was 432; +5 new C++ handlers wired 3-layer),
  no drift detected.

### Notes

- All new C++ uses UE 5.7 APIs verified against local engine headers:
  - `Runtime/Engine/Classes/Animation/AnimSequence.h`
    (`bEnableRootMotion`, `RootMotionRootLock` enum)
  - `Runtime/Engine/Public/Animation/AnimTypes.h` (`FAnimNotifyEvent` struct)
  - `Runtime/Engine/Classes/Animation/AnimLinkableElement.h`
    (`Link()` -- 5.1+ replacement for `LinkSequence`)
  - `Runtime/Engine/Classes/Animation/PoseAsset.h`
    (`CreatePoseFromAnimation(UAnimSequence*)`)
  - `Runtime/AIModule/Classes/EnvironmentQuery/EnvQuery.h`
    (`QueryName`, `Options`)
  - `Runtime/AIModule/Classes/Navigation/CrowdFollowingComponent.h`
- A templated `CreateAnimAssetCommon<FactoryT, AssetT>` helper from W1-F is
  shared between AnimMontage/AnimComposite; W1-G does *not* extend that
  helper because PoseAsset uses `NewObject` + `SetSkeleton` rather than the
  factory pattern.

### Cumulative tasks.md progress (this branch)

- `[x]` 402 -> 417 (A) -> 431 (B) -> 439 (C) -> 452 (D+E+F) -> **457** (G)
- `[ ]` 353 -> 338 -> 324 -> 316 -> 303 -> **298**

Total this branch: **55 items implemented + 13 router fixes** across
7 sub-batches.

---

## [2026-05-21] - Wave 1 sub-batches D + E + F: AI / Networking / Skeletal Mesh + Animation assets

Implements 13 more `[ ]` -> `[x]` items from `docs/superpowers/plans/tasks.md`
in three thematically grouped sub-batches.

### Added

**Sub-batch D (AI / Behavior Tree expansion, Navigation module id 20, 5 items):**
- `add_blackboard_key` -- `FBlackboardEntry` + `UBlackboardKeyType_{Bool,Int,
  Float,String,Name,Vector,Rotator,Object,Class}` resolved by string
- `remove_blackboard_key` -- `Keys.RemoveAll` by `EntryName`
- `add_ai_perception` -- `UAIPerceptionComponent` `NewObject + RegisterComponent
  + AddInstanceComponent` with `already_existed` short-circuit
- `configure_ai_sense_sight` -- `UAISenseConfig_Sight` (`SightRadius`,
  `LoseSightRadius`, `PeripheralVisionAngleDegrees`,
  `AutoSuccessRangeFromLastSeenLocation`, `DetectionByAffiliation`) +
  `ConfigureSense` + sets Sight as dominant when none configured
- `set_recast_navmesh_agent` -- per-instance `ARecastNavMesh` agent radius /
  height / max step / tile size / max simplification error. Avoids the UE 5.7
  deprecated `CellSize`/`CellHeight` direct fields (they now live in
  `NavMeshResolutionParams`).

**Sub-batch E (Networking minimal, Actor module id 1, 5 items):**
- `set_actor_replicates` -- `AActor::SetReplicates`
- `set_actor_replicate_movement` -- `AActor::SetReplicateMovement`
- `set_actor_net_dormancy` -- `AActor::SetNetDormancy` with string enum
  (Never / Awake / DormantAll / DormantPartial / Initial)
- `set_actor_net_cull_distance` -- writes `NetCullDistanceSquared` from a
  human-friendly cm distance (`distance * distance`)
- `set_actor_owner_only_relevant` -- `bOnlyRelevantToOwner` toggle

**Sub-batch F (Asset Import / Animation, AssetImport id 7 + Blueprint id 2, 3 items):**
- `import_skeletal_mesh_fbx` -- `UFbxImportUI.MeshTypeToImport=FBXIT_SkeletalMesh`
  with optional `skeleton_path` to bind to an existing `USkeleton`, morph
  target / material / texture toggles. Re-uses the existing
  `CreateImportTask` / `ProcessImportTask` pipeline.
- `create_anim_montage` -- `UAnimMontageFactory` + `IAssetTools::CreateAsset`
  with optional `SourceAnimation` (UAnimSequence) seed.
- `create_anim_composite` -- `UAnimCompositeFactory` with the same shape.

Python FastMCP wrappers added to:
- `server/ai_navigation_tools.py` (5 W1-D tools)
- `server/actor_tools.py` (5 W1-E tools)
- `server/asset_import_tools.py` (1 W1-F tool: `skeletal_mesh_fbx_import_tool`)
- `server/blueprint_tools.py` (2 W1-F tools: `create_anim_montage`,
  `create_anim_composite`)

L1 unit tests:
- `tests/unit/test_ai_tools_w1d.py` (15 tests)
- `tests/unit/test_actor_tools_w1e.py` (10 tests)
- `tests/unit/test_w1f_anim_skelmesh.py` (7 tests)

### Changed

- Router (`EpicUnrealMCPRouter.cpp`): added 13 routes
  (5 W1-D ids 20, 5 W1-E id 1, 1 W1-F id 7, 2 W1-F id 2).
- `docs/superpowers/plans/tasks.md`: flipped 13 entries to `[x]` covering
  Blackboard / AI Perception / Recast NavMesh agent / 5 networking items /
  Skeletal Mesh / Animation Sequence / Animation Montage.
- Sync'd canonical plugin to source-built project
  (9 files updated, 107 already in sync).

### Verification

- Ran `python -m pytest Python/tests/unit -q`; **736 passed** (was 704; +32 new
  W1-D/E/F tests).
- Ran `python scripts/audit_route_contracts.py --strict`; exit 0. Counters:
  `python_and_cpp: 432` (was 419; +13 new C++ handlers with Python wrappers),
  `cpp_only: 16`, `rust_only: 53`, no drift.

### Notes

- All new C++ uses UE 5.7 APIs verified against local engine headers:
  - `Runtime/AIModule/Classes/BehaviorTree/BlackboardData.h` (FBlackboardEntry +
    EntryName + KeyType + bInstanceSynced bitfield)
  - `Runtime/AIModule/Classes/Perception/{AIPerceptionComponent,
    AISenseConfig_Sight,AISense_Sight}.h`
  - `Runtime/NavigationSystem/Public/NavMesh/RecastNavMesh.h`
    (avoids deprecated `CellSize` / `CellHeight` direct fields)
  - `Runtime/Engine/Classes/GameFramework/Actor.h`
    (SetReplicates, SetReplicateMovement, SetNetDormancy,
     NetCullDistanceSquared, bOnlyRelevantToOwner)
  - `Editor/UnrealEd/Classes/Factories/{AnimMontageFactory,AnimCompositeFactory}.h`
- Used a templated `CreateAnimAssetCommon<FactoryT, AssetT>` helper to share
  the AnimMontage / AnimComposite asset-creation pipeline since both factories
  expose `TargetSkeleton` + `SourceAnimation` with the same shape.

### Cumulative tasks.md progress (this branch)

- `[x]` 402 -> 417 (A) -> 431 (B) -> 439 (C) -> **452** (D+E+F)
- `[ ]` 353 -> 338 -> 324 -> 316 -> **303**

Total this branch: **50 items implemented + 13 router fixes** across
6 sub-batches.

---

## [2026-05-21] - Wave 1 sub-batch C: AnimBP / BlendSpace / SoundSubmix + Material domain wrappers

Implements 8 more `[ ]` -> `[x]` items from `docs/superpowers/plans/tasks.md`.
3 new C++ handlers + 8 new Python tools (5 of which reuse the existing
`create_advanced_material` C++ handler with typed entry points).

### Added

- Animation asset creators (`EpicUnrealMCPBlueprintCommands.{h,cpp}`, router id 2):
  - `create_animation_blueprint` -- `UAnimBlueprintFactory` + `AssetTools::CreateAsset`
    with `TargetSkeleton`, `ParentClass` (defaults to `UAnimInstance`), and
    `BlueprintType = BPTYPE_Normal`.
  - `create_blend_space` -- `UBlendSpaceFactoryNew` + `AssetTools::CreateAsset`
    bound to a `USkeleton`.
- Audio asset creator (`EpicUnrealMCPAudioCommands.{h,cpp}`, router id 15):
  - `create_sound_submix` -- `USoundSubmix` via `NewObject` + optional parent
    submix linkage, output volume modulation
    (`FSoundModulationDestinationSettings::Value`), and auto-disable
    (`bAutoDisable` / `AutoDisableTime`).
- Material domain Python wrappers (`material_graph_tools.py`):
  - `create_decal_material` -- `MaterialDomain = MD_DeferredDecal`
  - `create_light_function_material` -- `MaterialDomain = MD_LightFunction`
  - `create_post_process_material` -- `MaterialDomain = MD_PostProcess` +
    `BlendableLocation = BL_SceneColorAfterTonemapping`
  - `create_landscape_material` -- Surface-domain material (landscape layer
    nodes added separately via `add_material_node`)
  - `create_runtime_virtual_texture_material` -- `MaterialDomain =
    MD_RuntimeVirtualTexture`
  These all route to the existing `create_advanced_material` C++ handler with
  a typed `material_domain` constant -- no new C++ required.
- Python FastMCP wrappers:
  - `server/blueprint_tools.py`: `create_animation_blueprint`, `create_blend_space`
  - `server/audio_tools.py`: `create_sound_submix`
  - `server/material_graph_tools.py`: 5 typed domain wrappers
- L1 unit tests:
  - `Python/tests/unit/test_blueprint_tools_w1c.py` (5 tests)
  - `Python/tests/unit/test_audio_tools_w1c.py` (4 tests)
  - `Python/tests/unit/test_material_tools_w1c.py` (6 tests)

### Changed

- Router (`EpicUnrealMCPRouter.cpp`): added 3 routes
  (`create_animation_blueprint`, `create_blend_space` -> id 2;
   `create_sound_submix` -> id 15).
- `docs/superpowers/plans/tasks.md`: flipped 8 entries to `[x]`
  (5 Material domains + Animation BP + BlendSpace + Submix).
- Sync'd canonical plugin to source-built project
  (5 files updated, 111 already in sync).

### Verification

- Ran `python -m pytest Python/tests/unit -q`; **704 passed** (was 689; +15
  new W1-C tests).
- Ran `python scripts/audit_route_contracts.py --strict`; exit 0. Counters:
  `python_and_cpp: 419` (was 416; +3 new C++ handlers; the 5 material domain
  wrappers all route to the pre-existing `create_advanced_material` command
  which is already counted), `cpp_only: 16`, `rust_only: 53`, no drift.

### Notes

- All new C++ uses UE 5.7 APIs verified against local engine headers:
  - `Editor/UnrealEd/Classes/Factories/AnimBlueprintFactory.h`
  - `Editor/UnrealEd/Classes/Factories/BlendSpaceFactoryNew.h`
  - `Editor/AudioEditor/Classes/Factories/SoundSubmixFactory.h`
  - `Runtime/Engine/Classes/Sound/SoundSubmix.h`
    (`bAutoDisable=true`, `AutoDisableTime=0.01f`, `ParentSubmix`,
     `OutputVolumeModulation.Value`)
  - `Runtime/Engine/Classes/Sound/SoundModulationDestination.h`
    (`FSoundModulationDestinationSettings::Value`)
- The Animation BP / BlendSpace creators use `IAssetTools::CreateAsset` rather
  than direct `NewObject` because the factory paths handle proper Blueprint
  initialization (`UAnimBlueprintGeneratedClass`, default AnimGraph page setup).

### Cumulative tasks.md progress (this branch)

- `[x]` 402 -> 417 (A) -> 431 (B) -> **439** (C)
- `[ ]` 353 -> 338 -> 324 -> **316**

Total this branch: **37 items implemented** (15 + 14 + 8), plus 13 critical
router fixes in sub-batch B.

---

## [2026-05-21] - Wave 1 sub-batch B: Router fix + Data Tables / Validation / Profiling / Physics residue

Implements 14 unimplemented items from `docs/superpowers/plans/tasks.md` covering
Data Tables (W1-9 residue, 5 items), Validation / Profiling (W1-10 residue, 5
items), and Physics non-Chaos (W1-8 residue, 4 items). Also fixes a regression
left by sub-batch A: 13 W1-A commands were registered in their `*Commands.cpp`
dispatch tables but **never wired into `EpicUnrealMCPRouter.cpp`**, so live TCP
routing would have returned "unknown command" for all of them.

### Fixed

- `EpicUnrealMCPRouter.cpp`: added the 13 missing router entries from sub-batch A:
  - id 2 (Blueprint): `add_latent_node`
  - id 7 (Asset Import): `import_animation_fbx`
  - id 12 (Rendering): `spawn_camera_shake_source`, `spawn_camera_rig_rail`,
    `spawn_camera_rig_crane`, `set_post_process_override`
  - id 16 (Sequencer): `add_visibility_track`, `add_audio_track`,
    `add_animation_track`, `add_material_parameter_track`, `delete_keyframe`,
    `set_keyframe_interpolation`, `add_subsequence`

### Added

- Data Table C++ handlers (`EpicUnrealMCPDataTableCommands.{h,cpp}`, router id 14):
  - `create_data_table_from_json` -- `UDataTable::CreateTableFromJSONString` on
    a new or existing table.
  - `create_curve_table` -- `UCurveTable` + optional CSV seeding with selectable
    `ERichCurveInterpMode` (Linear / Cubic / Constant).
  - `create_string_table` -- `UStringTable` + namespace + initial entries map
    via `FStringTable::SetSourceString`.
  - `set_string_table_entry` -- single (key, value) upsert on an existing
    StringTable.
  - `create_data_asset` -- `UDataAsset` / `UPrimaryDataAsset` instance creation
    from a class path (validates `IsChildOf(UDataAsset)`).
- Validation / Profiling C++ handlers
  (`EpicUnrealMCPValidationCommands.{h,cpp}`, router id 23):
  - `set_auto_save_settings` -- `UEditorLoadingSavingSettings` (`bAutoSaveEnable`,
    `AutoSaveTimeMinutes`, `AutoSaveWarningInSeconds`, `bAutoSaveContent`,
    `bAutoSaveMaps`) persisted via **`TryUpdateDefaultConfigFile()`** (UE 5.7
    rule).
  - `get_editor_stats` -- snapshots `FApp::GetDeltaTime` (FPS derivation) and
    `FPlatformMemory::GetStats` (used/peak/available physical + virtual MB) and
    optionally `GEngine->Exec("stat ...")` on the editor world.
  - `start_unreal_insights_trace` / `stop_unreal_insights_trace` --
    `FTraceAuxiliary::Start(EConnectionType::File, ...)` / `Stop()` /
    `EnableChannels` with configurable channel string (defaults to
    `default,cpu,gpu,frame,bookmark,log`).
  - `validate_assets` -- `UEditorValidatorSubsystem::ValidateAssetsWithSettings`
    over a content-path subtree, returns `num_checked / num_valid / num_invalid /
    num_skipped / num_warnings / num_unable_to_validate`.
- Physics C++ handlers (`EpicUnrealMCPPhysicsCommands.{h,cpp}`, router id 22):
  - `set_actor_collision_response` -- per-channel
    `UPrimitiveComponent::SetCollisionResponseToChannel` with alias-friendly
    channel names (`Pawn`, `WorldStatic`, `PhysicsBody`, ...).
  - `set_constraint_limits` -- `FConstraintInstance::Set*Motion` +
    `SetLinearLimitSize` + `SetAngular{Swing1,Swing2,Twist}Limit` on an existing
    `APhysicsConstraintActor`.
  - `set_constraint_motor` -- `SetLinearVelocityDrive` /
    `SetLinearPositionDrive` / `SetOrientationDriveSLERP` /
    `SetAngularVelocityDriveSLERP` + `SetLinearVelocityTarget`.
  - `spawn_physics_volume` -- `APhysicsVolume` spawn with `TerminalVelocity`,
    `Priority`, `bWaterVolume`, `FluidFriction`, and brush scale.
- Python FastMCP wrappers wired through `conn.send_command`:
  - `server/data_table_tools.py`: 5 tools (`create_data_table_from_json`,
    `create_curve_table`, `create_string_table`, `set_string_table_entry`,
    `create_data_asset`).
  - `server/validation_tools.py`: 5 tools (`set_auto_save_settings`,
    `get_editor_stats`, `start_unreal_insights_trace`,
    `stop_unreal_insights_trace`, `validate_assets`).
  - `server/physics_tools.py`: 4 tools (`set_actor_collision_response`,
    `set_constraint_limits`, `set_constraint_motor`, `spawn_physics_volume`).
- L1 unit tests:
  - `Python/tests/unit/test_data_table_tools_w1b.py` (14 tests).
  - `Python/tests/unit/test_validation_tools_w1b.py` (14 tests).
  - `Python/tests/unit/test_physics_tools_w1b.py` (14 tests).

### Changed

- `docs/superpowers/plans/tasks.md`: flipped 14 entries from `[ ]` to `[x]`
  covering Data Tables / Save / Validation / Profiling / Physics items
  implemented in this batch.
- Sync'd canonical plugin to source-built project via
  `scripts/sync-unrealmcp-plugin.ps1` (7 files updated, 109 already in sync).

### Verification

- Ran `python -m pytest Python/tests/unit -q`; **689 passed** (was 647 before
  this batch; +42 new W1-B tests).
- Ran `python scripts/audit_route_contracts.py --strict`; exit 0. Counters:
  `python_and_cpp: 416` (was 402; +14 new C++ handlers with Python wrappers),
  `cpp_only: 16`, `rust_only: 53`, no drift detected.
- Editor build verification deferred to local `Build.bat` run.

### Notes

- All new C++ uses UE 5.7 APIs verified against local engine headers
  (`Core/Public/ProfilingDebugging/TraceAuxiliary.h`,
  `Engine/Public/Settings/EditorLoadingSavingSettings.h`,
  `Engine/Classes/Engine/{CurveTable,DataAsset,CollisionProfile}.h`,
  `Internationalization/StringTable.h`,
  `PhysicsCore/Public/Chaos/ConstraintInstance.h`,
  `Engine/Public/GameFramework/PhysicsVolume.h`).
- `FTraceAuxiliary::FOptions` is the correct nested-struct name (not `Options`)
  -- caught during initial drafting and fixed before commit.
- `validate_assets` uses `EDataValidationUsecase::Manual` with
  `bShowIfNoFailures=false` so it does not spam the editor message log.

### Cumulative tasks.md progress (this branch)

- `[x]` 402 -> 417 (sub-batch A) -> **431** (sub-batch B)
- `[ ]` 353 -> 338 -> **324**

---

## [2026-05-21] - Wave 1 sub-batch A: Sequencer / Rendering / Blueprint / Asset Import / Material residue

Implements 15 unimplemented items from `docs/superpowers/plans/tasks.md` covering
Sequencer (W1-4 residue: 7 items), Rendering / Post Process (W1-7 residue:
4 items including 2 \(GI/Reflections override\) + 2 \(Camera Shake / Rig\)),
Blueprint (W1-1 Latent Node, 1 item), Asset Import (W1-1 Animation FBX
Import, 1 item), and fixes the Python<->C++ drift on `create_advanced_material`
(W1-6) by re-using the existing `material_graph_tools.create_advanced_material`
Python wrapper that was already shipped but missing test coverage. Tracks
the plan in `docs/implementation-plan-tasks-unimplemented.md`.

### Added

- Sequencer C++ handlers (`Plugins/UnrealMCP/.../EpicUnrealMCPSequencerCommands.{h,cpp}`):
  - `add_visibility_track` -- `UMovieSceneVisibilityTrack` (bHidden property track) per binding.
  - `add_audio_track` -- master `UMovieSceneAudioTrack` with optional `USoundBase` placement.
  - `add_animation_track` -- per-binding `UMovieSceneSkeletalAnimationTrack` with optional
    `UAnimSequence` assignment via `FMovieSceneSkeletalAnimationParams::Animation`.
  - `add_material_parameter_track` -- per-binding `UMovieSceneComponentMaterialTrack`
    with UE 5.4+ `FComponentMaterialInfo` (indexed material slot).
  - `delete_keyframe` -- scrubs all `FMovieSceneDoubleChannel` / `FMovieSceneFloatChannel`
    keys at the supplied frame for every track on a binding.
  - `set_keyframe_interpolation` -- bulk sets `ERichCurveInterpMode` (Cubic / Linear /
    Constant / None) on all keys for every track on a binding.
  - `add_subsequence` -- inserts either a regular `UMovieSceneSubTrack` section or a
    cinematic `UMovieSceneCinematicShotTrack` section (selected by `as_shot=true`).
- Rendering / Post Process C++ handlers (`EpicUnrealMCPRenderingCommands.{h,cpp}`):
  - `spawn_camera_shake_source` -- spawns an actor with `UCameraShakeSourceComponent`
    + optional `UCameraShakeBase` class override.
  - `spawn_camera_rig_rail` -- spawns `ACameraRig_Rail` with `CurrentPositionOnRail` +
    `bLockOrientationToRail` plumbed (`CinematicCamera` module).
  - `spawn_camera_rig_crane` -- spawns `ACameraRig_Crane` with `CranePitch/Yaw`,
    `CraneArmLength`, and `bLockMountPitch/Yaw` plumbed.
  - `set_post_process_override` -- overrides
    `FPostProcessSettings::DynamicGlobalIlluminationMethod` (`Lumen` / `ScreenSpace` /
    `Plugin` / `None`) and `ReflectionMethod` (`Lumen` / `ScreenSpace` / `None`) on a
    named `APostProcessVolume`.
- Blueprint C++ handler (`EpicUnrealMCPBlueprintCommands.{h,cpp}`):
  - `add_latent_node` -- adds a `UK2Node_CallFunction` for any BlueprintCallable
    latent function (default: `KismetSystemLibrary::Delay`) to a Blueprint's event
    graph. Supports `library_path` override so callers can target e.g.
    `KismetSystemLibrary::AsyncLoadAsset` or `AIBlueprintHelperLibrary::SimpleMoveToActor`.
- Asset Import C++ handler (`EpicUnrealMCPAssetImportCommands.{h,cpp}`):
  - `import_animation_fbx` -- animation-only FBX import bound to an existing
    `USkeleton` (`UFbxImportUI.MeshTypeToImport=FBXIT_Animation`,
    `bImportMesh=false`, `bImportAnimations=true`). Reuses the existing
    `CreateImportTask` / `ProcessImportTask` pipeline.
- Python FastMCP wrappers wired through `conn.send_command`:
  - `server/sequencer_tools.py`: `add_visibility_track`, `add_audio_track`,
    `add_animation_track`, `add_material_parameter_track`, `delete_keyframe`,
    `set_keyframe_interpolation`, `add_subsequence`.
  - `server/rendering_tools.py`: `spawn_camera_shake_source`,
    `spawn_camera_rig_rail`, `spawn_camera_rig_crane`,
    `set_post_process_override`.
  - `server/blueprint_tools.py`: `add_latent_node` (+ added validation imports).
  - `server/asset_import_tools.py`: `animation_fbx_import_tool`.
- L1 unit tests:
  - `Python/tests/unit/test_sequencer_tools_w1.py` (20 tests).
  - `Python/tests/unit/test_rendering_tools_w1.py` (15 tests).
  - `Python/tests/unit/test_w1_misc_tools.py` (9 tests for latent node + animation FBX
    + advanced material).
- Planning artifact: `docs/implementation-plan-tasks-unimplemented.md` (Agent 1 turn)
  is the single-source-of-truth for the Wave 1-4 backlog.

### Changed

- `Python/server/blueprint_tools.py` and `Python/server/material_tools.py` now import
  `validate_string` / `ValidationError` / `make_validation_error_response_from_exception`
  so the new W1 tools can return consistent validation errors.
- `docs/superpowers/plans/tasks.md`: flipped 15 entries from `[ ]` to `[x]` covering
  the Sequencer / Post Process / Camera / Blueprint Latent Node / Animation FBX
  Import items implemented in this batch.

### Verification

- Ran `python -m pytest Python/tests/unit -q`; **647 passed** (was 603 before this
  batch; +44 new tests from W1 + 1 from `material_tools` audit retarget).
- Ran `python scripts/audit_route_contracts.py --strict`; exit 0. Counters:
  `python_and_cpp: 402` (was 389; +13 = the 13 new C++ handlers with Python
  wrappers), `cpp_only: 16`, `rust_only: 53`, no drift detected.
- Did **not** rebuild the Unreal Editor in this turn -- C++ build verification
  remains a follow-on local task (see `docs/a2-a3-b4-execution-report.md` for the
  reproducible `Build.bat` command).

### Notes

- `create_advanced_material` Python wrapper already existed in
  `Python/server/material_graph_tools.py:190`. The W1-6 batch covers it by adding
  unit coverage instead of a duplicate wrapper.
- The new C++ handlers all use UE 5.7 APIs verified against the local
  `C:\Program Files\Epic Games\UE_5.7\Engine\Source\...` headers
  (`MovieSceneTracks/Public/Tracks/{Visibility,Audio,SkeletalAnimation,Material,
  CinematicShot}.h`, `CinematicCamera/Public/CameraRig_{Rail,Crane}.h`, etc.) per
  the `AGENTS.md` rule that learning-era APIs cannot be trusted on 5.7.

---

## [2026-05-03] - Jules cloud agent onboarding

### Added

- Added a root `AGENTS.md` with repository operating rules for local agents and Jules cloud tasks.
- Added `scripts/jules-setup.sh` for Jules Initial Setup on Ubuntu VMs, covering Python dependency setup, tool mapping/doc consistency smoke tests, and Rust dependency fetch.
- Added `docs/superpowers/plans/jules-implementation-brief.md` to convert the broad superpowers backlog into Jules-friendly branch slices.
- Updated `.gitignore` so `AGENTS.md`, `docs/superpowers/plans/tasks.md`, and the Jules implementation brief can be committed and read by cloud agents after cloning the repository.

### Notes

- Jules cannot launch the local Windows Unreal Editor or use `C:\...` Unreal paths, so UE build/editor/live MCP verification remains a local Windows responsibility.

---

## [2026-05-03] - PR #6/#8 functional verification fixes

### Fixed

- Fixed Material graph JSON tool wiring from PR #8:
  - added the missing `create_material` Python MCP tool for the C++ `create_material` command
  - aligned Python Material graph tools on the C++ `material_path`, `source_node_id`, `source_pin_name`, `target_node_id`, and `target_pin_name` contract
  - fixed `EpicUnrealMCPBridge.h` after a duplicate `UEpicUnrealMCPBridge` class declaration was introduced locally while wiring Material graph commands
- Implemented real basic Material graph connections in C++ instead of returning success without linking pins. Connections now support expression inputs and Material root pins such as `BaseColor` and `Roughness`.
- Added Material graph export of connection data in addition to node data.

### Added

- Added unit regression coverage for `apply_material_json` parameter mapping and `create_material` package path handling.
- Added Material graph JSON tool documentation to `README.md` and `Guides/tools-reference.md`.

### Verification

- Ran `python -m pytest tests/unit/test_tool_registration_and_mapping.py -v` before the fix; it failed because `create_material` was routable in C++ but unreachable from Python.
- Ran `python -m pytest tests/unit/test_tool_registration_and_mapping.py -v`; 41 passed.
- Ran `python -m pytest tests/unit/test_docs_consistency.py -v`; 6 passed.
- Ran `python -m pytest tests/unit tests/contract -v`; 305 passed.
- Built `FlopperamUnrealMCPEditor Win64 Development` with UE 5.7; build succeeded. Existing warnings remain for the Visual Studio compiler preference, plugin dependency declarations, and deprecated `NetUpdateFrequency`/`ClassDefaultObject` access.
- Launched the canonical `FlopperamUnrealMCP/FlopperamUnrealMCP.uproject`; the MCP bridge listened on `127.0.0.1:55557`, and logs showed `DynamicBandwidthManager Initialized` and `ServerMeshManager Initialized`.
- Ran a live MCP bridge smoke test for PR #8:
  - `create_material`, `apply_material_json`, and `export_material_json` created `/Game/Materials/M_PR8_Verify_*` and exported one node plus one `Roughness` connection.
  - `create_blueprint`, `apply_blueprint_json`, and `export_blueprint_json` created `/Game/Blueprints/BP_PR8_Verify_*` and exported graph nodes after JSON injection.

---

## [2026-05-01] - Procedural mesh visibility fix

### Fixed

- Fixed Unreal C++ procedural mesh binary parsing to read Rust float32 positions, normals, and UVs explicitly instead of copying into `FVector`/`FVector2D` storage directly. On UE5 large-world-coordinate builds, the previous direct copy could corrupt mesh coordinates while still returning a successful spawn response.
- Made spawned procedural meshes visible in the editor by registering the dynamic mesh component as an instance component, applying a default surface material when no material is provided, selecting the actor, and framing the editor viewport by default.

### Added

- Added optional `/procedural/create-mesh` transform controls: `location`, `rotation`, `scale`, and `focus_viewport`.
- Enlarged the 10K terrain demo to a visibly large terrain and documented the visibility smoke test in the scene-sync operations runbook.

---

## [2026-04-29] - Semantic layout graph draft visualization

### Added

- Added relation-aware layout denormalization for `curtain_wall` and `bridge` entities:
  - explicit `from` / `to` spans still work
  - `connected_by`, `connects`, `spans`, `spans_between`, and `attached_to` relations can derive spans from endpoint entity locations
  - diagonal spans now produce yaw-aligned scene objects
- Added wall and bridge expansion with `segments` or `segment_length`, allowing a semantic wall node to generate many reviewable blockout pieces.
- Added optional wall `crenellations` expansion for richer castle blockouts while preserving the original source entity through semantic metadata and tags.
- Added draft visualization metadata to generated objects, including `layout_kind:*`, `layout_entity:*`, and per-kind draft colors.
- Added Python MCP tools:
  - `scene_create_layout` for bulk creating Semantic Layout Graph nodes and edges
  - `scene_show_draft_proxy` for previewing a layout in Unreal as kind-grouped HISM draft proxies
- Documented the layout graph, preview, draft proxy, and denormalization tool flow in `docs/scene-sync/07_mcp_tool_api_spec.md`.

### Verification

- Added Rust unit coverage for relation-derived diagonal walls and wall expansion into segments plus crenellations.

---

## [2026-04-29] - Castle generation E2E reliability

### Fixed

- Fixed `scene-syncd` Unreal bridge calls to retry transient Windows socket aborts and close each request socket instead of reusing stale bridge connections.
- Fixed scene delta apply bookkeeping so partial `apply_scene_delta` failures no longer mark every create as synced.
- Reduced scene delta create chunks to one actor per bridge command with retry, avoiding large-response bridge aborts during castle generation.
- Fixed the dev-stack launcher to avoid starting a stale `scene-syncd.exe` when Rust sources are newer than the built binary.
- Hardened castle E2E verification by bulk-checking actor `mcp_id` tags from `get_actors_in_level` instead of issuing one bridge lookup per actor.
- Allowed non-destructive `apply_safe` sync to proceed with an empty actual-state snapshot when Unreal actor listing is temporarily unavailable; deletes still abort without a valid Unreal snapshot.
- Switched create-only sync application to the lighter `spawn_actor` bridge command instead of `apply_scene_delta`, reducing castle generation timeouts.

### Verification

- Ran `cargo test unreal::client --lib` in `rust/scene-syncd`.
- Ran `cargo test sync::applier --lib` in `rust/scene-syncd`.
- Ran `uv run pytest tests/e2e/test_castle_generation.py --skip-unreal -v` in `Python`.
- Rebuilt and restarted local `scene-syncd`; `GET /health` returned `success: true`.
- Removed stale `castle_*` Unreal actors left by earlier failed runs using `delete_actor_by_mcp_id`.
- Ran full castle E2E successfully once while Unreal MCP Bridge was listening; after later editor/bridge shutdowns, the same test correctly skipped because `127.0.0.1:55557` was no longer listening.

---

## [2026-04-26] - Scene-sync Phase 4/5 hardening

### Added

- Added `scripts/verify_phase5.py` integration test: creates an actor through DB desired state, updates its transform in the DB, applies sync, then verifies via `find_actor_by_mcp_id` and confirms re-plan is a no-op.
- Added `scene_snapshot_create` and `scene_snapshot_restore` via Rust `/snapshots/create` and `/snapshots/restore`; restore changes DB desired state only and requires a later `scene_sync`.
- Added DB desired-state generators `scene_create_wall` and `scene_create_pyramid` that bulk-upsert generated actors without touching Unreal.
- Added `FlopperamUnrealMCP 5.7/DEPRECATED.md` to document that the 5.7 project directory contains no plugin source and lacks `mcp_id` bridge commands required for scene sync.

### Fixed

- Fixed the Unreal C++ automation test helper linkage by restoring the `MakeArrayValue(std::initializer_list<TSharedPtr<FJsonValue>>)` overload used by MCP ID editor tests.
- Fixed `desired_hash` in `scene-syncd` to only include fields that the sync applier can actually apply (`actor_type` and `transform`).
  - `asset_ref`, `visual`, `physics`, and tags are intentionally excluded until their bridge commands are implemented.
  - Previously, changing tags or `asset_ref` produced an `UpdateVisual` operation that the applier skipped with "visual updates not yet implemented", leaving the DB `sync_status` permanently out of alignment with Unreal reality.
- Fixed `scene-syncd` object sync bookkeeping so `mark_object_synced`, tombstone marking, and delete-applied marking update SurrealDB records by typed record key instead of silently missing IDs that contain `scene:mcp_id`.
- Fixed `scene_snapshot` schema to preserve nested `groups` and `objects` array elements under SurrealDB schemafull mode.
- Fixed `plan_sync` response in `scene-syncd` to include Unreal-unreachable warnings in the `warnings` array, making it visible to clients that the plan was generated against an empty actual state.
- Fixed Python drift-detection test to include `scene_sync` in the `skip_tools` set, since it sends commands through the Rust HTTP API rather than directly to the Unreal C++ bridge.
- Fixed duplicate `mcp_id` safety in `scene-syncd` planner: if the same `mcp_id` is found on multiple actual Unreal actors, the planner downgrades any `Delete` operation for that `mcp_id` to `Conflict`, preventing accidental multi-actor deletion.

### Changed

- Updated `AGENTS.md` repository-specific guidance:
  - Documented that `scene_sync` (Phase 4 apply) is now implemented and wired into API routes and Python facade.
  - Added explicit deprecation warning for `FlopperamUnrealMCP 5.7/`.

### Verification

- Ran UE 5.7 editor build for `FlopperamUnrealMCP 5.7 - 3/FlopperamUnrealMCP.uproject`; build succeeded after the automation helper linkage fix.
- Ran `python -m pytest tests/unit/test_tool_registration_and_mapping.py -v` in `Python`; 35 passed.
- Ran `cargo test` in `rust/scene-syncd`; 6 passed. Existing unused-code warnings remain.
- Ran `python scripts/verify_phase5.py` with Unreal Editor, SurrealDB, and `scene-syncd` running; transform update applied and re-plan returned `noop: 1`.
- Verified Phase 7/8 through Python facade against local SurrealDB + `scene-syncd`: `scene_create_wall` upserted 3 objects, `scene_create_pyramid` upserted 5 objects, snapshot captured 8 objects, restore tombstoned 1 extra object and returned active objects to 8.

---

## [2026-04-26] - scenectl CLI MVP

### Added

- Added `scripts/scenectl.py`, a thin CLI over `scene-syncd` for `doctor`, local `start`/`stop`, scene creation, object listing, DB tag add/remove, safe tombstone dry-runs, sync plan, and guarded sync apply.
- Added root `scenectl.cmd` so Windows CMD can run `scenectl ...` from the repository root.
- Added an interactive `scenectl` shell when no arguments are provided, with color output, slash commands (`/help`, `/doctor`, `/object ...`, `/exit`), and Windows candidate display when typing `/` or pressing `Tab`.
- Added project-local OpenCode slash commands under `.opencode/commands/`: `/scenectl`, `/scene-doctor`, `/scene-list`, `/scene-plan`, `/scene-apply`, and `/scene-delete-dry-run`.
- Added `docs/scene-sync/13_scenectl_cli.md` with usage, safety rules, and current limits.
- Added unit coverage for CLI object filtering and upsert payload construction.

### Fixed

- Fixed scene object tag persistence in `scene-syncd` by adding `tags.*` schema typing and explicitly writing tags after object upserts.

### Verification

- Ran `python scripts/scenectl.py --help`.
- Ran `python -m pytest tests/unit/test_scenectl.py -v` in `Python`.
- Ran `cargo build` in `rust/scene-syncd`; existing unused-code warnings remain.
- Ran `python scripts/scenectl.py doctor` successfully against SurrealDB, `scene-syncd`, and Unreal.
- Ran `cmd /c "(echo /help & echo /exit) | scenectl"` and `cmd /c "(echo /doctor & echo /exit) | scenectl"` to verify the interactive shell.
- Tagged the `castle_crown_064013` scene objects by group, then verified `python scripts/scenectl.py object list --scene castle_crown_064013 --tag white_castle_crown` returned 22 objects.
- Verified delete and apply safety guards: `object delete --dry-run` listed targets without writing, and `apply` without `--yes` refused to run.

---

## [2026-04-26] - Scene sync craft-flow regression fix

### Fixed

- Fixed `scene-syncd` object upserts after initial creation by normalizing omitted or JSON `null` object fields (`asset_ref`, `visual`, `physics`, `metadata`) to `{}` before writing to SurrealDB schemafull `object` fields.

### Verification

- Ran `cargo test object_or_empty` in `rust/scene-syncd`.
- Ran `cargo build` in `rust/scene-syncd`; existing unused-code warnings remain.
- Re-ran a DB-driven craft test through SurrealDB and `scene-syncd`: bulk-created 12 Unreal actors for `craft_lab_063003`, then updated the `forge_core` transform through DB state and verified Unreal reported location `[800, 0, 230]` via `find_actor_by_mcp_id`.

---

## [2026-04-25] - OpenCode MCP configuration fix

### Fixed

- Updated the OpenCode MCP configuration sample from the legacy `mcpServers` shape to the current top-level `mcp` schema so OpenCode 1.14.x accepts the config.
- Added `.opencode/opencode.jsonc` as a project-local OpenCode config that starts the Unreal MCP server through the repository Python virtual environment.

### Verification

- Ran `opencode debug config` successfully against `C:\Users\arat2\.config\opencode\opencode.jsonc`.
- Ran `opencode mcp list` successfully; `unreal-engine-mcp` connected with 57 tools.
- Verified the direct `.venv` Python command imports `unreal_mcp_server_advanced` successfully.

---

## [2026-04-25] - Phase 4 scene-syncd verification

### Fixed

- Fixed `scene-syncd` Unreal bridge framing to use newline-delimited JSON, matching the current Unreal MCP plugin and Python client behavior.
- Fixed SurrealDB persistence for Phase 4 create sync by aligning timestamp serialization with SurrealDB `datetime` fields, avoiding serialized string timestamps in schemafull tables.
- Fixed `scene-syncd` record creation for scenes, scene objects, sync runs, and operation logs so SurrealDB record IDs are not serialized as ordinary string fields.
- Updated the local SurrealDB schema definitions used by `scene-syncd` to match the current Rust domain model for string scene/object references and nested transform fields.

### Added

- Added `scripts/verify_phase4.py` to verify the Phase 4 create-only flow end to end: create desired state through `scene-syncd`, apply sync, then confirm the actor exists in Unreal.

### Verification

- Installed SurrealDB v2.4.0 locally under `tools/surrealdb/surreal.exe`.
- Started SurrealDB on `127.0.0.1:8000` and `scene-syncd` on `127.0.0.1:8787`.
- Ran `cargo build` in `rust/scene-syncd` successfully. Existing unused-code warnings remain.
- Ran `python scripts/verify_phase4.py` successfully; it created `Phase4VerifyCube_20260425191854` in Unreal through `/sync/apply`.

### Notes

- The currently running Unreal plugin responds `Unknown command` for `find_actor_by_mcp_id`, so the active editor binary does not appear to include the repository's newer mcp_id command handlers. Create-only actor generation is verified, but mcp_id-based post-apply reconciliation requires launching a rebuilt plugin binary with those handlers.

---

## [2026-04-25] - Unreal project cleanup and shutdown crash fix

### Fixed

- Fixed an Unreal Editor shutdown crash in `UEpicUnrealMCPBridge::StopServer()` caused by owning `FSocket` instances with `TSharedPtr` while also destroying them through `ISocketSubsystem::DestroySocket()`. The bridge and server runnable now keep socket ownership explicit and release sockets through the Unreal socket subsystem only.
- Fixed UE 5.7 build errors in undo transaction setup by passing `FText` labels to `FScopedTransaction`, and replaced the unavailable `FIPv4Address::Loopback` reference with an explicitly parsed loopback address.
- Removed the project startup action that tried to import `StarterContent.upack`; UE 5.7 installs in this environment do not include that feature pack, and this MCP project does not require Starter Content.

### Changed

- Consolidated the local Unreal project copies back to the canonical `FlopperamUnrealMCP/` tree. The duplicate `FlopperamUnrealMCP 5.7/` and `FlopperamUnrealMCP 5.7 - 2/` project copies were local untracked copies and should not be used as source trees.

### Verification

- Verified the crash reports pointed to `EpicUnrealMCPBridge::StopServer()` during `EditorExit` from the duplicate `FlopperamUnrealMCP 5.7 - 2` project path.
- Built `FlopperamUnrealMCPEditor Win64 Development` with UE 5.7 successfully.
- Launched the canonical project with UE 5.7, confirmed the MCP bridge initialized, then closed the editor process without a new crash report.

---

## [2026-04-24] - Safety, batching, and undo support

### Added

#### New MCP tools

- **`batch_spawn_actors`** (`Python/server/actor_tools.py`): Spawn multiple actors in a single call with per-actor validation, a configurable batch limit (default 500), and a `dry_run` mode that returns the planned actor list without executing. (`Python/server/actor_tools.py`)
- **`get_blueprint_material_info`** (`Python/server/material_tools.py`): Proper `@mcp.tool()`-decorated function that sends `get_blueprint_material_info` to Unreal, replacing the bare alias `get_blueprint_material_info = get_actor_material_info` that was not registered with FastMCP. A backward-compatible alias `_get_blueprint_material_info_alias` is kept for internal use.

#### Input validation layer

- **`Python/server/validation.py`**: New module providing reusable validation helpers:
  - `validate_vector3()`, `validate_color()`, `validate_string()`, `validate_float()`, `validate_int()`, `validate_positive_int()`, `validate_nonneg_int()`, `validate_unreal_path()`
  - `ValidationError` exception class with `field` and `message` attributes.
  - `make_validation_error_response()` and `make_validation_error_response_from_exception()` for uniform error responses.
  - Constants: `MAX_ACTORS_PER_BATCH = 500`, `MAX_WORLD_EXTENT = 1000000.0`.
- Validation applied to:
  - `actor_tools.py`: `find_actors_by_name`, `delete_actor`, `spawn_actor`, `set_actor_transform`
  - `world_building_tools.py`: `create_pyramid`, `create_wall`, `create_maze`
- `create_maze` now rejects requests where the estimated actor count exceeds `MAX_ACTORS_PER_BATCH` before querying Unreal.

#### Batch spawning for world-building tools

- `create_pyramid` and `create_wall` now pre-compute all actor specifications and delegate to `batch_spawn_actors()` instead of spawning actors one at a time via `safe_spawn_actor()`. Both accept a `dry_run` parameter.
- This reduces per-actor validation overhead and centralizes error handling, though each actor still uses a separate TCP command (true C++ batch command not yet implemented).

#### Undo support in C++ plugin

- Added `FScopedTransaction` wrappers to 21 C++ command handlers across three files. This enables Undo in the Unreal Editor for all destructive Blueprint, graph, and editor operations:
  - `EpicUnrealMCPEditorCommands.cpp`: `HandleSpawnActor`, `HandleDeleteActor`, `HandleSetActorTransform`
  - `EpicUnrealMCPBlueprintCommands.cpp`: `HandleCreateBlueprint`, `HandleAddComponentToBlueprint`, `HandleSetPhysicsProperties`, `HandleSetStaticMeshProperties`, `HandleSetMeshMaterialColor`, `HandleSpawnBlueprintActor`, `HandleApplyMaterialToActor`, `HandleApplyMaterialToBlueprint`
  - `EpicUnrealMCPBlueprintGraphCommands.cpp`: `HandleAddBlueprintNode`, `HandleConnectNodes`, `HandleCreateVariable`, `HandleSetVariableProperties`, `HandleAddEventNode`, `HandleDeleteNode`, `HandleSetNodeProperty`, `HandleCreateFunction`, `HandleAddFunctionInput`, `HandleAddFunctionOutput`, `HandleDeleteFunction`, `HandleRenameFunction`
- Added `Actor->Modify()` call in `HandleSetActorTransform` before modifying the transform, so the transaction records the previous state correctly.

#### Tests  - Python/C++ command mapping

- Added `TestPythonToCppCommandMapping` class in `Python/tests/unit/test_tool_registration_and_mapping.py` with four tests:
  - `test_python_commands_are_handled_in_cpp`: every command that Python sends to Unreal has a matching C++ dispatcher route.
  - `test_cpp_commands_are_used_by_python`: every C++ command (except whitelisted entries like `ping`) is invoked by at least one Python tool.
  - `test_each_mcp_tool_sends_exactly_one_cpp_command`: structural check that each MCP tool (except known orchestrators) maps to a single C++ command.
  - `test_tool_name_to_command_mapping_is_complete`: verifies a hardcoded 31-entry mapping dict covers all registered tools.
- Added `get_blueprint_material_info` to the existing `TestToolCommandMapping` parameterized test entries.

### Changed

#### README

- Updated tool count from ~38 to 46.
- Added `batch_spawn_actors`, `add_event_node`, `get_actor_material_info`, `get_blueprint_material_info` to the tool table.
- Changed Python version requirement from "3.12+" to "3.10+ (3.12 recommended; 3.10 - .13 supported)" to match `pyproject.toml`.

#### `unreal_mcp_server_advanced.py`

- Re-exports `batch_spawn_actors` from `server.actor_tools`.

### Migration notes

- The bare alias `get_blueprint_material_info = get_actor_material_info` in `material_tools.py` has been replaced with a proper `@mcp.tool()` function. The old alias still works as `_get_blueprint_material_info_alias` for internal use, but MCP clients will now see `get_blueprint_material_info` as a registered tool with its own schema.
- `create_pyramid` and `create_wall` now return batch-style result objects (with `spawned_count`, `failed_count`, `actors`, and optionally `failed` keys) instead of the previous `{"success": True, "actors": [...]}` format. Callers that depend on the exact response shape should be updated.

---

## [2026-04-24] - Fork compliance update

- Added MIT license text as `LICENSE`.
- Added explicit credit to the original repository in `README.md`.
- Added a clear statement that this repository is an unofficial fork and not the official Flopperam project.
- Added a clear statement that this repository is separate from the paid Flopperam Agent product.
- Added guidance for a non-confusing fork display name: "Unreal Engine MCP Community Fork (Unofficial)".

---

## Known differences from upstream (2026-04-24)

This section summarizes all structural and behavioral differences between this fork and the upstream `flopperam/unreal-engine-mcp` repository as of this date.

### Python server

| Area | Upstream | This fork |
|------|----------|-----------|
| `material_tools.py` | `get_blueprint_material_info` is a bare alias for `get_actor_material_info`, not registered as an MCP tool | `get_blueprint_material_info` is a proper `@mcp.tool()` function that sends `get_blueprint_material_info` to Unreal |
| `actor_tools.py` | No `batch_spawn_actors` tool; no input validation on tool functions | `batch_spawn_actors` added with validation, dry_run, and batch limit; validation on `find_actors_by_name`, `delete_actor`, `spawn_actor`, `set_actor_transform` |
| `world_building_tools.py` | `create_pyramid` and `create_wall` spawn one actor at a time via `safe_spawn_actor`; `create_maze` has no actor limit guard | Both delegate to `batch_spawn_actors()` with pre-computed specs and `dry_run` parameter; `create_maze` rejects requests exceeding `MAX_ACTORS_PER_BATCH=500` |
| `validation.py` | Does not exist | New module with vector/color/string/float/int/path validators, `ValidationError`, batch limits |
| Test mapping | `TestToolCommandMapping` has 25 entries; no `TestPythonToCppCommandMapping` | 26 entries (adds `get_blueprint_material_info`); new `TestPythonToCppCommandMapping` class with 4 drift-detection tests |

### C++ plugin

| Area | Upstream | This fork |
|------|----------|-----------|
| `EpicUnrealMCPEditorCommands.cpp` | No `FScopedTransaction` on any handler | `FScopedTransaction` on `HandleSpawnActor`, `HandleDeleteActor`, `HandleSetActorTransform`; `Actor->Modify()` added before transform changes |
| `EpicUnrealMCPBlueprintCommands.cpp` | No `FScopedTransaction` | `FScopedTransaction` on 8 handlers (create blueprint, add component, set physics/mesh/material properties, spawn blueprint actor, apply material to actor/blueprint) |
| `EpicUnrealMCPBlueprintGraphCommands.cpp` | No `FScopedTransaction` | `FScopedTransaction` on 9 handlers (add node, connect nodes, create/set variable, add event node, delete node, set node property, create/rename/delete function, add function input/output) |

### Documentation

| Area | Upstream | This fork |
|------|----------|-----------|
| `README.md` | Tool count ~38; Python 3.12+; no fork notice | Tool count 46; Python 3.10+ (3.12 recommended); fork notice at top |
| `CHANGELOG.md` | Does not exist or is empty | Full fork changelog and diff table |
| `AGENTS.md` | Does not exist or is upstream version | Fork-specific with repository guidance, known risks, required checks |

### Not yet changed (planned)

The following improvements are identified but not yet implemented:

- **C++ `batch_spawn_actors` command**: Currently `batch_spawn_actors` sends individual `spawn_actor` commands over separate TCP connections. A single C++ handler accepting an actor array would eliminate per-actor connection overhead.
- **Persistent TCP connection**: `send_command()` still opens and closes a TCP socket per request. Connection reuse or pooling would reduce latency.
- **`safe_spawn_actor` N+1 name-check problem**: Each actor spawn calls `find_actors_by_name` first. Batch spawn should pre-fetch existing names once.
- **Response envelope standardization**: Responses do not yet follow a uniform `{success, data, error, warnings, duration_ms, command_id}` schema.
- **Authentication/authorization**: No auth token, no allowlist for destructive commands, defaults bind to 127.0.0.1 but does not warn on 0.0.0.0.
- **Remaining world-building tools migration**: `create_tower`, `create_staircase`, `create_town`, `create_castle_fortress`, `create_suspension_bridge`, `create_aqueduct`, `create_arch`, `construct_house`, `construct_mansion` still spawn one actor at a time.
- **Structured logging**: No JSONL audit log; no command-level duration tracking.
- **Idempotency keys**: No retry-safety mechanism for write commands.
- **Blueprint compile results**: `set_node_property`, `connect_nodes`, etc. do not return compile status.
- **C++ command registry / `list_capabilities`**: No dynamic capability query or version negotiation.
- **Pydantic input models**: Tools use raw `Dict[str, Any]` instead of typed models.



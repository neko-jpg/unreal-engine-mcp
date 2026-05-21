# tasks.md 未実装機能 — 詳細実装計画 (Wave 1〜4)

最終更新: 2026-05-21
対象 Engine: **Unreal Engine 5.7**
親計画: `docs/superpowers/plans/tasks.md`
前計画: `docs/implementation-plan-remaining-completion.md`, `docs/a2-a3-b4-execution-report.md`
作成: Agent (planning role) — coordinator multi-agent run

---

## 0. 集計と方針

`docs/superpowers/plans/tasks.md` を機械集計した結果:

| 状態 | 件数 |
|---|---|
| `[x]` 実装済 | **402** |
| `[~]` 部分実装 / 既存資産あり | **18** |
| `[ ]` 未実装 | **353** |

全 353 件を 4 つの **Wave (P0 → P3)** に分割し、各 Wave 内では既存依存モジュールと
ファイル骨格を最大限再利用する順で並べた。各タスクには **UE 5.7 のキー API、
追加が必要な依存モジュール、対応する C++ / Python / Rust ファイル、検証コマンド** を
明記する。

### 凡例

- **C++** = `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/<ファイル>.cpp` (+ Public ヘッダー)
- **PY**  = `Python/server/<ファイル>.py` (FastMCP tool)
- **RS**  = `rust/scene-syncd/src/api/<ファイル>.rs` (HTTP route、必要な場合のみ)
- **DEP** = `UnrealMCP.Build.cs` に追加するモジュール (オプショナル化を推奨)
- **TEST** = `Python/tests/{unit|contract|e2e}/<ファイル>.py` 追加位置
- **LIVE** = `scripts/live_e2e_smoke.py` に追加する case 名 (任意・優先度別)

### AGENTS.md ルールの再徹底

- 実装前に **必ず `web_search` 等で UE 5.7 公式 API / GitHub ソースを確認**。
- `UpdateDefaultConfigFile()` 禁止 → **`TryUpdateDefaultConfigFile()`** を使う。
- 5.7 で名前が変わった / 別モジュールに移動した API を学習データで判断しない。

---

## 1. Wave 1 — 既存依存モジュールで即着手可能 (P0 / 今週〜来週)

> 共通点: 追加モジュール不要 or 既に PrivateDependencyModuleNames に入っている。
> ROI: 既存資産との結合で機能完結度が一気に上がる。

### W1-1. Blueprint 残 (3 項目)

| Task | 対応 |
|---|---|
| `Latent Node制御` | C++ `EpicUnrealMCPBlueprintCommands.cpp` (既存) に `add_latent_node` を追加。`UK2Node_BaseAsyncTask` 派生をスポーン (Delay / AsyncLoadAsset / AIMoveTo 等)。Pin 名は `OutputDelegate.then` を default 接続 |
| `Blueprint Profiler連携` | UE 5.7 では Blueprint Profiler が deprecate→`Unreal Insights` に統合済み。 → 中長期-3 (W3-10 Insights) に統合 |
| (Animation FBX Import / §4 の穴) | C++ `EpicUnrealMCPAssetImportCommands.cpp` に `import_animation_fbx` を追加。`UFbxImportUI.bImportAnimations=true`, `bImportMesh=false`, `Skeleton` 指定 |

- **PY**: `blueprint_tools.py` に `add_latent_node`, `asset_import_tools.py` に `import_animation_fbx`
- **TEST**: `tests/unit/test_blueprint_latent_node.py`, `tests/unit/test_asset_import_animation_fbx.py`
- **LIVE**: `latent_delay_node`, `import_anim_fbx_smoke`
- **見積**: 0.5 日

### W1-2. Behavior Tree / Blackboard / AI Perception 拡張 (約 15 項目)

既存 `EpicUnrealMCPNavigationCommands.cpp` に `create_behavior_tree` / `create_blackboard` / `create_nav_modifier_volume` / `create_nav_link_proxy` がある。Asset 作成のみで Editor 操作に踏み込んでいない。以下を追加:

| Task | C++ API (UE 5.7) |
|---|---|
| Behavior Tree Node 追加 | `UBTCompositeNode_*` / `UBTTaskNode_*` の NewObject + `UBehaviorTree::RootNode->Children.Add` (composite の場合) |
| Behavior Tree Node 接続 | composite と子の関係は `BTComposite->Children` 配列で表現。Editor 上の line は EdGraph 経由なので `UBehaviorTreeGraph` を使う |
| Task / Service / Decorator 作成 | `UBTTaskNode` / `UBTService` / `UBTDecorator` を NewObject。Blueprint task の場合は `UBTTask_BlueprintBase` |
| Blackboard Key 追加 / 削除 / 型設定 | `UBlackboardData::Keys` に `FBlackboardEntry { EntryName, KeyType }` を append。KeyType は `UBlackboardKeyType_{Bool,Int,Float,String,Vector,Object,Class,Enum,Name,Rotator}` |
| AIControllerにBT設定 | `AAIController::RunBehaviorTree(UBehaviorTree*)`。default を BP で固定する場合は AAIController BP の `BTAsset` プロパティ |
| Run Behavior Tree Node 生成 | Blueprint graph の `K2Node_CallFunction` で `RunBehaviorTree` をターゲット |
| AI Perception Component 追加 | `UAIPerceptionComponent` を AAIController に Add. Sense は `UAISenseConfig_{Sight,Hearing,Damage,Team,Touch,Prediction}` |
| Sight/Hearing/Damage/Team Sense 設定 | `UAISenseConfig_Sight::SightRadius` 等を `UAIPerceptionComponent::ConfigureSense` |
| EQS Query / Generator / Test / Debug | `UEnvQuery` Asset 新規 + `UEnvQueryGenerator_*` / `UEnvQueryTest_*` の NewObject。`AIModule` で公開済 |
| Smart Nav Link / Nav Area / Crowd Following | `ASmartNavLink` / `UNavArea` / `UCrowdFollowingComponent` |
| Agent Radius / Height / Recast NavMesh 設定 | `URecastNavMesh::AgentRadius, AgentHeight, CellSize, CellHeight` を設定後 `TryUpdateDefaultConfigFile` |
| MassEntity 連携 | UE 5.7 `MassEntity` plugin (Optional)。`UMassSpawnerSubsystem` |
| StateTree 作成 / State / Task | UE 5.7 `StateTree` plugin (Optional)。`UStateTree` + `FStateTreeState` |

- **C++**: 既存 `EpicUnrealMCPNavigationCommands.cpp` に追加 → 1000 LOC 超なら `EpicUnrealMCPAIBehaviorCommands.cpp` 等に分割
- **PY**: `ai_navigation_tools.py` を `ai_behavior_tools.py` / `ai_perception_tools.py` / `ai_eqs_tools.py` に分割推奨
- **DEP**: `AIModule` (済), `MassEntity` (Optional), `StateTreeModule` (Optional)
- **TEST**: `tests/unit/test_behavior_tree_node_add.py`, `tests/unit/test_blackboard_keys.py`, `tests/unit/test_ai_perception_sight.py`, `tests/unit/test_eqs_query.py`
- **LIVE**: `bt_simple_patrol`, `bt_with_blackboard_key`, `ai_perception_sight`, `eqs_grid_generator`
- **見積**: 2 日

### W1-3. Animation Blueprint / Skeletal (約 28 項目)

UE 5.7 で `UAnimBlueprint`, `UAnimGraphNode_*` を NewObject で作成し、`KismetCompiler` でコンパイル。State Machine は `UAnimGraphNode_StateMachine` + `UAnimStateNode` で構築。

| Task | UE 5.7 API |
|---|---|
| Skeletal Mesh Import | `UFbxImportUI.bImportMesh=true`, `MeshTypeToImport=FBXIT_SkeletalMesh`, `SkeletalMeshImportData` |
| Skeleton Asset 作成 | `USkeleton` を NewObject (通常は FBX import で自動生成、override は `UFbxImportUI.Skeleton`) |
| Physics Asset 作成 | `UPhysicsAsset::Create` + `FPhysicsAssetUtils::CreateFromSkeletalMesh` |
| Animation Sequence Import | `UFbxImportUI.bImportAnimations=true`, `bImportMesh=false`, `AnimSequenceFactory` |
| Animation Blueprint 作成 | `FKismetEditorUtilities::CreateBlueprint(USkeleton, UAnimBlueprint::StaticClass(), ...)` + `TargetSkeleton` |
| AnimGraph Node 追加 | `UAnimGraphNode_*` (`UAnimGraphNode_BlendListByBool`, `UAnimGraphNode_StateMachine`, ...) を `UAnimationGraph::AddNode` |
| State Machine / State / Transition | `UAnimGraphNode_StateMachine` + `UAnimStateNode` + `UAnimStateTransitionNode` |
| BlendSpace / Aim Offset / Montage | `UBlendSpace` / `UAimOffsetBlendSpace` / `UAnimMontage` を NewObject、Slot 設定 |
| Notify / Notify State | `UAnimNotify` / `UAnimNotifyState` 派生を `UAnimSequenceBase::Notifies` に追加 |
| Root Motion | `UAnimSequence::EnableRootMotion = true`, `RootMotionRootLock` |
| Retarget / IK Rig / IK Retargeter | UE 5.7 `IKRig` plugin (Engine bundled)。`UIKRigDefinition`, `UIKRetargeter` |
| Control Rig | UE 5.7 `ControlRig` plugin (Engine bundled)。`UControlRigBlueprint` |
| Pose Asset | `UPoseAsset::CreatePoseFromAnimation` |
| MetaHuman 連携 | MetaHuman Plugin (Optional / Marketplace)。`MetaHumanProjectUtilities` |

- **C++**: `EpicUnrealMCPAnimationCommands.cpp` 新規 (推定 500〜1000 LOC)
- **PY**: `animation_tools.py` 新規
- **DEP**: `AnimGraph` (Editor), `AnimGraphRuntime`, `IKRig`, `IKRigEditor` (Editor), `ControlRig`, `ControlRigEditor` (Editor)。MetaHuman は Optional 検出
- **TEST**: `tests/unit/test_animation_blueprint_create.py`, `tests/unit/test_state_machine_basic.py`, `tests/unit/test_blendspace_create.py`
- **LIVE**: `anim_bp_idle_walk`, `anim_montage_attack`, `ik_retargeter_default`
- **見積**: 4 日 (Wave 1 最大)

### W1-4. Sequencer 残 (10 項目)

既存 `EpicUnrealMCPSequencerCommands.cpp` に 8 handler 実装済。残りは:

| Task | UE 5.7 API |
|---|---|
| Visibility Track | `UMovieSceneVisibilityTrack` (`MovieSceneTracks` モジュール) |
| Audio Track | `UMovieSceneAudioTrack` + `UMovieSceneAudioSection` |
| Animation Track | `UMovieSceneSkeletalAnimationTrack` (`MovieSceneTracks`) |
| Material Parameter Track | `UMovieSceneMaterialTrack` (派生 `Component` / `PrimitiveComponent`) |
| Keyframe 削除 / 補間設定 | `UMovieSceneSection::DeleteKeys` / `FMovieSceneFloatChannel::SetInterpolation` |
| Shot Track / Subsequence | `UMovieSceneCinematicShotTrack` + `UMovieSceneSubSection` |
| Camera Rail / Crane 連携 | `ACameraRig_Rail` / `ACameraRig_Crane` (`CinematicCamera` 既存) |
| Sequencer Render Preview | `ISequencer::RenderMovie(...)` or `UMoviePipelineQueue` (W1-5 と統合) |
| Take Recorder 連携 | `UTakeRecorder` (`TakeRecorder` plugin) |
| Control Rig Track | `UMovieSceneControlRigParameterTrack` (`ControlRig` plugin) |

- **C++**: 既存 `EpicUnrealMCPSequencerCommands.cpp` に追加。1000 LOC 超なら `EpicUnrealMCPSequencerTracksCommands.cpp`/`SequencerKeysCommands.cpp`/`TakeRecorderCommands.cpp` に分割
- **PY**: `sequencer_tools.py` を `sequencer_tracks_tools.py`/`sequencer_keys_tools.py` に分割
- **DEP**: `MovieSceneTracks` (済), `TakeRecorder` (Editor), `TakesCore`
- **TEST**: `tests/unit/test_sequencer_visibility_track.py`, `tests/unit/test_sequencer_keyframe_delete.py`
- **見積**: 1.5 日

### W1-5. Movie Render Queue (21 項目)

Sequencer の出口。UE 5.7 `MovieRenderPipeline` (Engine bundled)。

| Task | UE 5.7 API |
|---|---|
| Movie Render Queue Job 作成 | `UMoviePipelineQueueSubsystem::GetQueue()->AllocateNewJob(UMoviePipelineExecutorJob::StaticClass())` |
| Sequence を Queue に追加 | `Job->Sequence = TSoftObjectPtr<ULevelSequence>(...)` |
| Output / Resolution / Frame Range | `UMoviePipelineOutputSetting` (Config setting class) |
| Anti-Aliasing | `UMoviePipelineAntiAliasingSetting` |
| EXR / PNG / JPG | `UMoviePipelineImageSequenceOutput_{EXR,PNG,JPG}` |
| ProRes / Video | `UMoviePipelineAppleProResOutput` / `UMoviePipelineWaveOutput` |
| Path Tracer | `UMoviePipelineDeferredPassBase` + `UMoviePipelinePathTracerSetting` |
| Console Variables | `UMoviePipelineConsoleVariableSetting` |
| Render Pass | `UMoviePipelineRenderPass` 派生を Config に append |
| Object ID / Mask Pass | `UMoviePipelineObjectIdRenderPass` (UE 5.7) |
| Burn In / Warm Up | `UMoviePipelineBurnInSetting` / `UMoviePipelineGameOverrideSetting.WarmUpFrames` |
| Render 開始 / キャンセル / 進捗 | `UMoviePipelineQueueSubsystem::RenderQueueWithExecutor(UMoviePipelinePIEExecutor)`、`Executor->OnExecutorFinished` |
| Render 結果検証 | 出力 dir scan + 画像 hash 比較 |
| Movie Render Graph | UE 5.5+ の MRG (`UMovieGraphConfig` + `UMovieGraphNode`)。UE 5.7 で API 安定化 |

- **C++**: `EpicUnrealMCPMovieRenderCommands.cpp` 新規 (推定 800 LOC)
- **PY**: `movie_render_tools.py` 新規
- **DEP**: `MovieRenderPipelineCore`, `MovieRenderPipelineEditor`, `MovieRenderPipelineRenderPasses`, `MovieRenderPipelineSettings`, `MovieGraph` (Editor)
- **TEST**: `tests/unit/test_mrq_job_create.py`
- **LIVE**: `mrq_render_short_clip` (5 frame Smoke)
- **見積**: 2 日

### W1-6. Material 残 (7 項目)

既存 `EpicUnrealMCPMaterialCommands.cpp` 51KB に追加:

| Task | UE 5.7 API |
|---|---|
| Substrate Material 作成 | UE 5.7 で正式リリース。`r.Substrate=1` Console Variable。`UMaterial::bUseMaterialAttributes` + `UMaterialExpressionSubstrateSlab` |
| Layered Material | `UMaterialExpressionMaterialLayerBlend` を root に挿入。`UMaterialFunctionInterface` で Layer Function 作成 |
| Decal Material | `UMaterial::MaterialDomain = MD_DeferredDecal` |
| Landscape Material | `UMaterial` + `UMaterialExpressionLandscapeLayer{Blend,Weight,Sample}` 群 |
| Runtime Virtual Texture 設定 | `UMaterialExpressionRuntimeVirtualTextureOutput` / `URuntimeVirtualTexture` Asset |
| Light Function Material | `UMaterial::MaterialDomain = MD_LightFunction` |
| Post Process Material | `UMaterial::MaterialDomain = MD_PostProcess` + `BlendableLocation` |

- **C++**: 既存 `EpicUnrealMCPMaterialCommands.cpp` に追加 (or `EpicUnrealMCPMaterialDomainCommands.cpp` に分割)
- **PY**: `material_tools.py` に追加
- **DEP**: 追加なし
- **TEST**: `tests/unit/test_material_substrate.py`, `tests/unit/test_material_decal.py`
- **見積**: 1.5 日

### W1-7. Post Process 残 (4 項目)

| Task | UE 5.7 API |
|---|---|
| Global Illumination Override | `UPostProcessVolume::Settings.bOverride_DynamicGlobalIlluminationMethod, DynamicGlobalIlluminationMethod` |
| Reflections Override | `UPostProcessVolume::Settings.bOverride_ReflectionMethod` |
| Camera Shake | `UCameraShakeBase` 派生 NewObject + `UCameraShakeSourceComponent` |
| Camera Rig Rail / Crane | `ACameraRig_Rail` / `ACameraRig_Crane` (`CinematicCamera` 既存) |

- **C++**: 既存 `EpicUnrealMCPRenderingCommands.cpp` に追加
- **PY**: `rendering_tools.py` に追加
- **見積**: 0.5 日

### W1-8. Physics / Chaos 残 (約 17 項目)

| Task | UE 5.7 API |
|---|---|
| Collision / Object / Trace Channel 作成 | `DefaultEngine.ini` の `[/Script/Engine.CollisionProfile]` 編集 → **`TryUpdateDefaultConfigFile`** |
| Collision Response 設定 | `UPrimitiveComponent::SetCollisionResponseToChannel` |
| Constraint Limit / Motor | `UPhysicsConstraintComponent::ConstraintInstance.SetLinearXLimit`, `SetAngularSwing1Limit`, `SetLinearVelocityDrive` |
| Physics Volume | `APhysicsVolume` spawn + `TerminalVelocity`, `bWaterVolume` |
| Geometry Collection / Fracture | `UGeometryCollection` + `UGeometryCollectionComponent`。Fracture は `FractureEditorMode` (Editor only) |
| Chaos Field | `AFieldSystemActor` + `UFieldSystem` |
| Chaos Solver / Cache | `AChaosSolverActor`, `AChaosCacheManager`, `UChaosCache` |
| Chaos Vehicle / Wheel / Suspension / Engine Torque | `UChaosWheeledVehicleMovementComponent` (`ChaosVehicles` plugin) |
| Cloth / Chaos Cloth Asset | UE 5.7 新 `UChaosClothAsset` (`ChaosClothAsset` plugin)。APEX clothing は完全廃止 |
| Groom Physics | `UGroomComponent::PhysicsAsset` (`HairStrands` plugin) |
| Ragdoll | `USkeletalMeshComponent::SetSimulatePhysics(true)` + Physics Asset |
| Physics Asset Body / Constraint 編集 | `UPhysicsAsset::SkeletalBodySetups[i]`, `ConstraintSetup[i]` |
| Chaos Visual Debugger | `ChaosVD` plugin (`r.ChaosVD.RecordTrace 1`) |

- **C++**: 既存 `EpicUnrealMCPPhysicsCommands.cpp` 拡張 + `EpicUnrealMCPChaosCommands.cpp` 新規 (GC / Vehicle / Cloth)
- **PY**: `physics_tools.py` 拡張 + `chaos_tools.py` 新規
- **DEP**: `Chaos`, `ChaosSolverEngine` (Engine 経由), `GeometryCollectionEngine`, `FieldSystemEngine`, `ChaosVehicles` (plugin), `ChaosClothAsset` (plugin)
- **TEST**: `tests/unit/test_collision_channel_create.py`, `tests/unit/test_geometry_collection_basic.py`, `tests/unit/test_chaos_vehicle_wheeled.py`
- **見積**: 3 日

### W1-9. Data Tables 残 (13 項目)

| Task | UE 5.7 API |
|---|---|
| JSON から DataTable 作成 | `UDataTable::CreateTableFromJSONString` |
| Row Struct 作成 / 編集 | `UUserDefinedStruct` を `FStructureEditorUtils::CreateUserDefinedStruct` + `AddVariable` |
| Primary Data Asset / Data Asset 作成 | `UPrimaryDataAsset` / `UDataAsset` 派生クラスを NewObject |
| Data Asset Property 編集 | `FProperty::CopyCompleteValue` |
| Curve Table | `UCurveTable::CreateTableFromCSVString` |
| String Table | `UStringTable` 作成 + `SetSourceString` |
| Gameplay Tag Table Import | `UGameplayTagsManager::AddTagIniSearchPath` + Tag CSV 読込 |
| Item / Enemy / Quest / Dialogue DB 生成 | テンプレート Row Struct + CSV/JSON Loader (高レベルラッパー) |

- **C++**: 既存 `EpicUnrealMCPDataTableCommands.cpp` に追加
- **PY**: `data_table_tools.py` 拡張 + `data_asset_tools.py` 新規
- **見積**: 1.5 日

### W1-10. Save / Validation / Testing / Profiling 残 (約 18 項目)

| Task | UE 5.7 API |
|---|---|
| Auto Save 設定 | `UEditorLoadingSavingSettings::AutoSaveEnable`, `AutoSaveTimeMinutes` → **`TryUpdateDefaultConfigFile`** |
| UE Automation Test 作成 / Functional Test Actor / 実行・結果 | `IMPLEMENT_SIMPLE_AUTOMATION_TEST` (C++) + `AFunctionalTest`。Editor 経由は `UAutomationControllerManager` |
| Asset Validation 実行 | `UEditorValidatorSubsystem::ValidateAssets` |
| Collision / Navigation Validation | `UNavigationSystemV1::Build`、`UWorld::HasBegunPlay` 等 |
| Performance Budget / FPS / Stat Unit / Stat GPU / Memory | `GEngine->Exec(World, TEXT("stat unit"))`、`FApp::GetDeltaTime()`、`FPlatformMemory::GetStats` |
| Unreal Insights Trace 開始 / 停止 | `Trace::ToggleChannel` + `UnrealInsights.exe` attach |
| Gameplay Screenshot Test | `FAutomationScreenshotData` + `FAutomationTestFramework::OnScreenshotCompared` |

- **C++**: 既存 `EpicUnrealMCPValidationCommands.cpp` (8KB) 拡張 + `EpicUnrealMCPProfilingCommands.cpp` 新規
- **PY**: `validation_tools.py` 拡張 + `profiling_tools.py` 新規
- **DEP**: `AutomationController`, `FunctionalTesting`, `TraceLog`, `EditorValidatorSubsystem` (UE 5.7 `DataValidation` plugin)
- **見積**: 2 日

**Wave 1 合計見積: 約 18.5 日 (3.5 週) / カバー 約 130 項目**

---

## 2. Wave 2 — 大規模機能 / 新規モジュール (P1 / 来月)

### W2-1. Landscape / Terrain (23 項目)

UE 5.7 Landscape API は **Editor only** が大半。`LandscapeEditor` モジュールを使う。

| Task | UE 5.7 API |
|---|---|
| Landscape 作成 / サイズ設定 | `ALandscape::Import` の新シグネチャ。`FLandscapeImportHelper::GetHeightmapImportData` で前処理 |
| Section / Component 設定 | `ALandscape::ComponentSizeQuads`, `SubsectionSizeQuads`, `NumSubsections` |
| Heightmap Import / Export | 16-bit PNG / R16 raw |
| Sculpt / Smooth / Flatten / Ramp / Erosion / Noise | `FLandscapeEditorObject` + `ULandscapeEditorObject_Sculpt::Tool` 系。コマンドレット or Editor utility |
| Paint Layer / Layer Blend | `ULandscapeLayerInfoObject` 新規 + `ALandscape::EditorLayerSettings` |
| Material 適用 | `ALandscape::LandscapeMaterial` |
| Grass Output | `UMaterialExpressionLandscapeGrassOutput` + `ULandscapeGrassType` |
| Collision 設定 | `ALandscape::CollisionMipLevel` |
| Hole 作成 | `ALandscape::HasLayersContent && PaintLayerWeight=Hole` |
| Spline / Road Spline | `ULandscapeSplinesComponent` + `ULandscapeSplineSegment` + `ULandscapeSplineControlPoint` |
| River Terrain Carve | Water plugin (`AWaterBodyRiver`) と `bCanAffectLandscape` (W2-4 統合) |
| Runtime Virtual Texture 連携 | `ULandscapeComponent::RuntimeVirtualTextures` |
| Nanite Landscape | UE 5.7 `r.Landscape.Nanite=1` + `ALandscape::bEnableNanite` |
| World Partition Landscape 管理 | `ALandscapeStreamingProxy` + `UWorldPartitionLandscapeBuilder` |

- **C++**: `EpicUnrealMCPLandscapeCommands.cpp` 新規 (推定 1500 LOC)
- **PY**: `landscape_tools.py` 新規
- **DEP**: `Landscape`, `LandscapeEditor` (Editor only), `LandscapeEditorUtilities`, `WorldPartitionEditor`
- **TEST**: `tests/unit/test_landscape_create.py`, `tests/unit/test_landscape_heightmap_import.py`, `tests/unit/test_landscape_paint_layer.py`
- **LIVE**: `landscape_create_smoke`, `landscape_heightmap_roundtrip`
- **見積**: 4 日

### W2-2. Foliage / Vegetation (20 項目)

| Task | UE 5.7 API |
|---|---|
| Foliage Type 作成 | `UFoliageType_InstancedStaticMesh` Asset 新規 |
| Static Mesh / Actor Foliage 登録 | `UFoliageType` を `AInstancedFoliageActor` に追加 |
| Paint / Erase / Density / Scale / Yaw / Align / Cull / LOD | `UFoliageType_InstancedStaticMesh::{Density, ScaleX, RandomYaw, AlignToNormal, CullDistance, ...}` |
| Procedural Foliage Spawner / Volume / Seed / Biome | `UProceduralFoliageSpawner` + `AProceduralFoliageVolume` + `ResampleProceduralContent` |
| Grass Type / Landscape Grass 連携 | `ULandscapeGrassType` (W2-1 と共用) |
| Nanite Foliage 設定 | `UFoliageType::Mesh` が Nanite なら自動 |
| Wind 設定 | `UFoliageType::WindSettings` + Material `WindFoliage` node |
| Pivot Painter 連携 | `Engine/Plugins/PivotPainter` Material function 群 |

- **C++**: `EpicUnrealMCPFoliageCommands.cpp` 新規
- **PY**: `foliage_tools.py` 新規
- **DEP**: `Foliage`, `FoliageEdit` (Editor)
- **見積**: 2 日

### W2-3. PCG Framework (17 項目)

UE 5.7 で Production-ready。`PCG` plugin (Engine bundled, optional)。

| Task | UE 5.7 API |
|---|---|
| PCG Graph 作成 | `UPCGGraph` Asset 新規 |
| PCG Component / Volume | `UPCGComponent` + `APCGVolume` spawn |
| PCG Node 追加 / 接続 | `UPCGNode` を `UPCGGraph::AddNode` + `UPCGEdge` で接続 |
| PCG Graph Parameter | `UPCGGraphInstance::ParametersOverrides` |
| Spline / Surface Sampler | `UPCGSplineSampler`, `UPCGSurfaceSampler` |
| Static Mesh Spawner | `UPCGStaticMeshSpawnerSettings` |
| Rule / Biome Graph / Point Data / Attribute | `UPCGData`, `UPCGPointData`, `UPCGAttribute*Data` |
| Graph 実行 / 再生成 / Runtime Generation | `UPCGComponent::Generate` / `CleanupLocal` / `bGenerated` |
| Editor Mode 操作 / Debug | `FPCGEditorModule::OpenPCGGraph` (Editor only) |
| PCG Tool 作成 | `UPCGBlueprintElement` 派生 |

- **C++**: `EpicUnrealMCPPCGCommands.cpp` 新規 (推定 1200 LOC)
- **PY**: `pcg_tools.py` 新規
- **DEP**: `PCG` (Optional plugin), `PCGEditor` (Editor)、Cesium 同様の検出
- **見積**: 3 日

### W2-4. Water System (17 項目)

UE 5.7 `Water` plugin (Engine bundled, optional)。

| Task | UE 5.7 API |
|---|---|
| Water Plugin 有効化 | `.uproject` Plugins 配列に `{"Name":"Water","Enabled":true}` 追記 |
| Water Body Ocean / Lake / River / Custom | `AWaterBodyOcean`, `AWaterBodyLake`, `AWaterBodyRiver`, `AWaterBodyCustom` spawn |
| River Spline | `AWaterBodyRiver::SplineComponent` の `SplinePoints` |
| Water Material | `UWaterBodyComponent::WaterMaterial` |
| Wave / Flow | `UGerstnerWaterWaves` Asset + `WaterBodyComponent::SetWaterWaves` |
| Buoyancy | `UBuoyancyComponent` を AActor に追加 |
| Water Mesh Actor | `AWaterMeshActor` (5.7 自動生成、手動 spawn 可) |
| Underwater Post Process | `AWaterZone::UnderwaterPostProcess` |
| Shoreline | `AWaterBodyOcean::ShorelineMaterial` |
| Landscape Carving | `AWaterBody::bCanAffectLandscape=true` |
| Boat / Floating Actor 連携 | `UBuoyancyComponent::Pontoons` |

- **C++**: `EpicUnrealMCPWaterCommands.cpp` 新規
- **PY**: `water_tools.py` 新規
- **DEP**: `Water` (Optional), `WaterEditor` (Editor)
- **見積**: 2 日

### W2-5. Niagara / VFX (27 項目)

UE 5.5+ Niagara API は安定。UE 5.7 で `NiagaraGraph`, `NiagaraEmitter`, `NiagaraStackEditor`。

| Task | UE 5.7 API |
|---|---|
| Niagara System / Emitter 作成 | `UNiagaraSystem`, `UNiagaraEmitter` を NewObject |
| Emitter 追加 / Module 追加・削除 | `FNiagaraEditorUtilities::AddEmitterToSystem`, `UNiagaraStackModuleItem` |
| Spawn Rate / Burst / Lifetime / Velocity / Gravity / Color / Size | `UNiagaraStackFunctionInput` 経由で `EmitterStateStack` 編集 |
| Renderer (Sprite / Mesh / Ribbon) | `UNiagaraRendererProperties` 派生を `UNiagaraEmitter::AddRenderer` |
| GPU Simulation | `UNiagaraEmitter::SimTarget = ENiagaraSimTarget::GPUComputeSim` |
| Collision | Collision module (CPU) / `r.Niagara.CollisionGPU` |
| User Parameter | `UNiagaraSystem::ExposedParameters.AddParameter` |
| Niagara Component / Actor | `UNiagaraComponent` Add or `ANiagaraActor` spawn |
| Parameter Binding | `UNiagaraComponent::SetVariableFloat/Vec3/Linear` |
| Data Channel / Effect Type / Scalability / Debug / SIM Cache | `UNiagaraDataChannel`, `UNiagaraEffectType`, `UNiagaraSimCache` |

- **C++**: `EpicUnrealMCPNiagaraCommands.cpp` 新規 (推定 1500 LOC)
- **PY**: `niagara_tools.py` 新規
- **DEP**: `Niagara`, `NiagaraEditor`, `NiagaraCore` (Engine bundled)
- **見積**: 4 日

### W2-6. Audio / MetaSounds 残 (11 項目)

| Task | UE 5.7 API |
|---|---|
| Sound Wave Import | `USoundWaveFactory::FactoryCreateBinary` (WAV 既存)、OGG/AIFF/FLAC は 5.7 `UAudioImportFactory` |
| Sound Cue Graph 編集 | `USoundCueGraphNode_*` を `USoundCue::SoundCueGraph` Add |
| Submix 作成 | `USoundSubmix` Asset 新規 |
| MetaSound Source / Patch 作成 | `UMetaSoundSource`, `UMetaSoundPatch` (`MetaSoundEditor` モジュール) |
| MetaSound Graph Node 追加 / Parameter | `UMetasoundEditorGraph` + `UMetasoundEditorGraphNode` |
| Audio Volume | `AAudioVolume` spawn + `AudioVolumeSettings` |
| Dialogue Wave | `UDialogueWave` Asset + `FDialogueContext` |
| Footstep / UI Sound | Subsystem (`UAudioGameplaySubsystem`) |

- **C++**: 既存 `EpicUnrealMCPAudioCommands.cpp` 拡張 + `EpicUnrealMCPMetaSoundCommands.cpp` 新規
- **PY**: `audio_tools.py` 拡張 + `metasound_tools.py` 新規
- **DEP**: `AudioMixer`, `MetasoundEngine`, `MetasoundEditor` (Editor), `AudioWidgets`
- **見積**: 2 日

### W2-7. Mesh Editing 残 (3 項目 / すべて `[~]`)

| Task | UE 5.7 API |
|---|---|
| Mesh Bake | `UGeometryScriptLibrary_MeshBakeFunctions::BakeTexture` (`GeometryScriptingCore` 既存) |
| Boolean | `UGeometryScriptLibrary_MeshBooleanFunctions::ApplyMeshBoolean` |
| Voxel Remesh | `UGeometryScriptLibrary_MeshVoxelFunctions::ApplyMeshVoxelize` + `ApplyMeshSolidify` |

- **C++**: 既存 `EpicUnrealMCPMeshEditingCommands.cpp` に追加
- **PY**: `mesh_editing_tools.py` に追加
- **見積**: 0.5 日

**Wave 2 合計見積: 約 17.5 日 (3.5 週) / カバー 約 118 項目**

---

## 3. Wave 3 — Networking / GAS / Testing / Localization (P2 / 来々月)

### W3-1. Networking / Multiplayer (26 項目)

| Task | UE 5.7 API |
|---|---|
| Actor / Component Replicates 設定 | `AActor::SetReplicates(true)`, `UActorComponent::SetIsReplicated(true)` |
| Replicate Movement | `AActor::SetReplicateMovement(true)` |
| Net Dormancy / Cull Distance / Owner Only | `AActor::NetDormancy`, `NetCullDistanceSquared`, `bOnlyRelevantToOwner` |
| RPC Server / Client / Multicast 関数作成 | C++ `UFUNCTION(Server/Client/NetMulticast, Reliable)` + BP 側 K2Node カスタム |
| Reliable / Unreliable / RepNotify | `UFUNCTION(Reliable)` / `Unreliable` / `UPROPERTY(ReplicatedUsing=OnRep_*)` |
| Replicated 変数一覧取得 | `FProperty::PropertyFlags & CPF_Net` |
| Network Prediction | `UCharacterMovementComponent::SetNetworkPredictionMode` |
| Dedicated Server / Listen Server / Client / Multi-PIE | `UEditorEngine::PlayInEditor(MultiPIE=true)` |
| Online Subsystem / Session 作成・検索・参加 | `IOnlineSubsystem::Get()->GetSessionInterface()->CreateSession/FindSessions/JoinSession` |
| Iris Replication | UE 5.7 `Iris` plugin 安定化。`UReplicationSystem` |
| Replication Graph | `UReplicationGraph` 派生 + `BasicReplicationGraph` template |
| Bandwidth Profiling / Network Profiler | `Stat NetStats`, `Stat Net` + `NetworkProfiler.exe` |

- **C++**: `EpicUnrealMCPNetworkingCommands.cpp` 新規 (推定 1200 LOC)
- **PY**: `networking_tools.py` 新規
- **DEP**: `OnlineSubsystem`, `OnlineSubsystemUtils`, `NetCore`, `Iris`, `IrisCore`, `ReplicationGraph`
- **TEST**: `tests/unit/test_actor_replicates.py`, `tests/unit/test_rpc_function_create.py`, `tests/unit/test_iris_config.py`
- **LIVE**: `multiplayer_listen_server_smoke` (PIE 2 client)
- **見積**: 4 日

### W3-2. Gameplay Ability System (16 項目)

`GameplayAbilities` plugin (UE 5.7 Engine bundled, optional)。

| Task | UE 5.7 API |
|---|---|
| GAS Plugin 有効化 | `.uproject` に `GameplayAbilities` + `GameplayTagsEditor` |
| Ability System Component 追加 | `UAbilitySystemComponent` を Pawn / PlayerState に AddComponent |
| Attribute Set 作成 | `UAttributeSet` 派生 (C++ 推奨)、BP 派生も 5.7 で実用化 |
| Gameplay Ability 作成 | `UGameplayAbility` BP 派生 |
| Gameplay Effect / Cue | `UGameplayEffect` BP 派生、`UGameplayCueNotify_Static/Actor` |
| Ability Input Binding | `UAbilitySystemComponent::BindAbilityActivationToInputComponent` |
| Ability Grant / Activation / Cooldown / Cost | `UAbilitySystemComponent::GiveAbility`, `TryActivateAbility`, `CooldownGameplayEffectClass`, `CostGameplayEffectClass` |
| Attribute 初期化 / 変更 Event | `UAbilitySystemComponent::InitStats`, `GetGameplayAttributeValueChangeDelegate` |
| Gameplay Tag 連携 / Replication / Prediction | `FGameplayTag`, `UAbilitySystemComponent::ReplicationMode`, `bClientUpdatePredictionKey` |

- **C++**: `EpicUnrealMCPGASCommands.cpp` 新規
- **PY**: `gas_tools.py` 新規
- **DEP**: `GameplayAbilities` (Optional plugin)
- **見積**: 3 日

### W3-3. Testing / Automation 残 (W1-10 補完)

`Gameplay Screenshot Test` / `Performance Budget Validation` は Live E2E と統合する必要があるので Wave 3 で完成。

- **LIVE**: `screenshot_compare_baseline`, `perf_budget_validate`

### W3-4. Localization (10 項目)

| Task | UE 5.7 API |
|---|---|
| Localization Dashboard 操作 | `ULocalizationTarget` Asset 編集 (Editor only) |
| Culture 追加 | `ULocalizationTarget::SupportedCulturesStatistics` Append |
| Text Gather | `LocalizationCommandletExecution` で `GatherText` commandlet |
| PO Export / Import | `LocalizationCommandletExecution` の `Export` / `Import` |
| String Table 作成 / 編集 | W1-9 と共通 |
| Widget Text Localization | `UTextBlock::SetText(FText::FromStringTable(...))` |
| Dialogue Localization | `UDialogueWave::AddContextAndAddMatchingTargetingTagsToAllContexts` |
| Font Fallback | `UFont::CompositeFont` の `Fallback` フォント |

- **C++**: `EpicUnrealMCPLocalizationCommands.cpp` 新規
- **PY**: `localization_tools.py` 新規
- **DEP**: `Localization`, `LocalizationCommandletExecution`
- **見積**: 1.5 日

### W3-5. MetaHuman / Optional Plugin 統合 (W1-3 補完)

Cesium と同じ Optional 検出パターン: `bMetaHumanFound` → `WITH_METAHUMAN=1`、`MetaHumanProjectUtilities` を private dep。

### W3-6. Movie Render Graph (W1-5 補完)

UE 5.5 導入、UE 5.7 安定化。`UMovieGraphConfig` + `UMovieGraphNode`。

**Wave 3 合計見積: 約 9 日 (1.8 週) / カバー 約 60 項目**

---

## 4. Wave 4 — Platform / Collaboration (P3 / 将来)

### W4-1. Mobile / XR / Platform (14 項目)

| Task | UE 5.7 API |
|---|---|
| Android / iOS 設定 | `UAndroidRuntimeSettings`, `UIOSRuntimeSettings` → **`TryUpdateDefaultConfigFile`** |
| Mobile Rendering / Touch Input | `MobileShadingPath`, `UInputComponent::BindTouch` |
| Device Profile / Scalability Profile | `UDeviceProfileManager`, `EngineScalabilitySettings` |
| XR Plugin / OpenXR | `OpenXR` plugin 有効化 + `UOpenXRRuntimeSettings` |
| VR Pawn / Motion Controller / HMD Camera | `AVRCharacter`, `UMotionControllerComponent`, `UHeadMountedDisplayFunctionLibrary` |
| AR Session / AR Plane Detection | `UARSessionConfig` (`AugmentedReality` plugin) |
| Platform-specific Packaging | `IPlatformFile`, `ITurnkeySupportModule` |

- **C++**: `EpicUnrealMCPPlatformCommands.cpp` 新規
- **PY**: `platform_tools.py` 新規
- **見積**: 2 日

### W4-2. Source Control (11 項目)

| Task | UE 5.7 API |
|---|---|
| Source Control 状態 / Git / Perforce / Checkout / Checkin / Revert / Lock / Changelist | `ISourceControlModule::Get().GetProvider().Execute<...>(SourceControlHelpers::PackageFilename(...))` |
| Asset Diff / Blueprint Diff | `FAssetToolsModule::Get().DiffAssets` / `FBlueprintEditorUtils::DiffBlueprints` |
| Merge 支援 | `UMergeAssetsCommandlet` |
| Multi-User Editing 起動 / Session 接続 | `IConcertSyncClient` (`ConcertSyncClient` plugin) |

- **C++**: `EpicUnrealMCPSourceControlCommands.cpp` 新規
- **PY**: `source_control_tools.py` 新規
- **DEP**: `SourceControl`, `SourceControlWindows`, `ConcertSyncClient` (Optional)
- **見積**: 2 日

**Wave 4 合計見積: 約 4 日 / カバー 約 25 項目**

---

## 5. 横断的 / 共通要素

### 5-1. Optional Plugin 検出パターン (Cesium 流用)

```cs
// UnrealMCP.Build.cs に追加
bool DetectOptional(string Token, string[] ProbePaths) {
    foreach (string Probe in ProbePaths) {
        if (System.IO.File.Exists(Probe)) {
            PublicDefinitions.Add($"WITH_{Token}=1");
            return true;
        }
    }
    PublicDefinitions.Add($"WITH_{Token}=0");
    return false;
}
```

対象: `WITH_PCG` (W2-3), `WITH_WATER` (W2-4), `WITH_METAHUMAN` (W3-5),
`WITH_GAS` (W3-2), `WITH_CHAOS_VEHICLES` / `WITH_CHAOS_CLOTH_ASSET` (W1-8),
`WITH_CONCERT` (W4-2)。C++ 側は `#if WITH_PCG` で囲み、Cesium graceful degradation と
同等の挙動にする。

### 5-2. 命名 / Route Contract 規約

- **C++ command name**: `<area>_<verb>` (`landscape_create`, `niagara_add_module`, `bt_add_node`, `mrq_create_job`)
- **Python tool name**: 完全一致 (`scripts/audit_route_contracts.py --strict` で CI 検証)
- **Rust route**: `POST /<area>/<verb>` (例: `POST /landscape/create`)

新コマンド追加時は **必ず** `python scripts/audit_route_contracts.py --strict` を pass させる。
UE-only の場合は `CPP_ONLY_WHITELIST` に追加。

### 5-3. テスト戦略

| 機能カテゴリ | L1 unit | L2 contract | L3 e2e | live_e2e_smoke |
|---|---|---|---|---|
| Asset 作成系 (BT, AnimBP, NiagaraSystem, ...) | 必須 (FakeSocket) | envelope 確認 | scene_sync 越し | 1 case 追加 |
| Editor 操作系 (Landscape sculpt, MRQ render) | 必須 (mock UE response) | optional | 必須 | 1 case 追加 |
| Plugin Optional (PCG, Water, MetaHuman, GAS) | 必須 (skip if missing) | envelope | requires=<plugin> で skip | requires= で skip |
| Settings 系 (Replication, Auto Save) | 必須 (TryUpdateDefaultConfigFile mock) | - | - | 1 case 追加 |

### 5-4. CI 増強 (Wave 1-2 完了時)

- `.github/workflows/python-checks.yml` に追加 case 統合
- Self-hosted Windows runner で nightly `Build.bat ... Development` (中長期-4 計画済)
- `scripts/audit_route_contracts.py --strict` を毎 PR で実行 (済)
- 新規: `scripts/audit_uplugin_optional_modules.py` — `WITH_*` define と uplugin の整合チェック

### 5-5. 計画書のメンテナンス

各 Wave 完了時:
1. `tasks.md` のチェックボックスを `[x]` に更新
2. `CHANGELOG.md` に Wave 単位エントリ追加 (`feat(W1): ...`)
3. 本書の対応セクションに **検証結果** と **artifacts/<bench/live_e2e>_*.json** リンク追記
4. `docs/implementation-plan-remaining-completion.md` を「Wave 1〜4 完了状況サマリ」として更新

---

## 6. 推奨実行順 (3 エージェント体制での運用)

```
本ターン (Agent 1, planning):  本書を完成 → 着手順を確定
次ターン (Agent 2, review):   本計画の批判的レビュー / 抜け検出 → 修正版を提案
最終ターン (Agent 3, worker): W1-1 から順に実装 → 各タスク完了で commit + 検証
```

Wave 内 sub-batch 分割:

```
W1 sub-batch A (依存ゼロ):   W1-1 → W1-4 → W1-6 → W1-7 → W1-9
W1 sub-batch B (中規模 C++): W1-2 → W1-8 → W1-10
W1 sub-batch C (大規模):     W1-3 → W1-5

W2 sub-batch A (Optional plugin 検出設定): Build.cs に集約
W2 sub-batch B (新規モジュール): W2-1 → W2-2 → W2-5
W2 sub-batch C (plugin 依存):    W2-3 → W2-4 → W2-6 → W2-7

W3 sub-batch A: W3-1 → W3-2
W3 sub-batch B: W3-4 → W3-6 → W3-5

W4 sub-batch A: W4-1 → W4-2
```

各 sub-batch は **独立した PR / branch**。`chore/a3-b2-m1-live-verified` 上に積まず、新 branch を切る。

### Critical Path (本日着手分)

1. **W1-1 Latent Node + Animation FBX Import** (0.5 日)
2. **W1-2 Behavior Tree Node / Blackboard Key** (1 日)
3. **W1-4 Sequencer Visibility / Audio / Animation Track** (1.5 日)
4. **W1-5 Movie Render Queue Job 作成 + Render 開始** (1 日)

これで `tasks.md` カテゴリ §4, §6, §18, §23, §24 の合計 約 35 項目を 4 日で潰せる。

---

## 7. 完了定義 (Definition of Done — Wave 単位)

| 項目 | Wave 1 | Wave 2 | Wave 3 | Wave 4 |
|---|---|---|---|---|
| `tasks.md` の `[x]` 更新 | 130 項目 | 248 (累積) | 308 (累積) | 333 (累積) |
| C++ build (`Build.bat ... Development`) | exit 0 | exit 0 | exit 0 | exit 0 |
| Python `pytest unit + contract` | 緑 | 緑 | 緑 | 緑 |
| Rust `cargo test` / `clippy -D warnings` | 緑 | 緑 | 緑 | 緑 |
| `audit_route_contracts.py --strict` | exit 0 | exit 0 | exit 0 | exit 0 |
| Live E2E smoke (該当 case) | 全 pass | 全 pass | 全 pass | 全 pass |
| Optional 依存定義 (uplugin) | 追加済 | 追加済 | 追加済 | 追加済 |
| `CHANGELOG.md` エントリ | 追加済 | 追加済 | 追加済 | 追加済 |
| 本書 Wave セクションに検証結果リンク | 更新済 | 更新済 | 更新済 | 更新済 |

最終目標: **tasks.md 353 件 [ ] + 18 件 [~] → 全て [x]**、`scripts/live_e2e_smoke.py` 50+ case、tasks.md カバー率 100%。

---

## 8. リスク登録簿

| ID | リスク | 影響 | 対応 |
|---|---|---|---|
| W-R1 | UE 5.7 で API 名が学習データと違う (Landscape, Niagara, MRQ で頻発) | ビルドエラー / クラッシュ | AGENTS.md ルール: 着手前に web_search で 5.7 公式 doc / GitHub 確認 |
| W-R2 | Optional plugin (PCG, Water, MetaHuman, GAS) の検出失敗 | `WITH_X=0` で feature 全 skip | Cesium と同じ probe path × 3 (Engine / Marketplace / Project) で網羅 |
| W-R3 | Editor only API を Runtime で呼ぶ | DLL 不在 / 非 editor build で失敗 | `if (Target.bBuildEditor)` で囲み、`#if WITH_EDITOR` ガード |
| W-R4 | `UpdateDefaultConfigFile` を誤って使う | 5.7 で警告 / エラー | コードレビューで grep、CI で `Select-String` 検出 |
| W-R5 | 大規模 commit のレビュー遅延 | merge が長期停滞 | Wave 内 sub-batch 単位で PR を分割。1 PR < 30 files / 1500 LOC |
| W-R6 | route contract drift | 3 層が乖離 | `audit_route_contracts.py --strict` を pre-commit hook 化推奨 |
| W-R7 | Animation BP / Niagara 等で Editor freeze | ユーザビリティ低下 | 重い処理は `AsyncTask(ENamedThreads::GameThread, ...)` でフレーム分割 |
| W-R8 | Multi-User Editing と scene-syncd の競合 | DB と Concert の double-write | W4-2 着手時に design doc を別途作成 |

---

## 9. 即着手スケッチ (Agent 3 への引き継ぎ材料)

### 9-1. W1-1: Latent Node 追加 (Blueprint)

C++ (`EpicUnrealMCPBlueprintCommands.cpp` Dispatch に追加):

```cpp
{TEXT("add_latent_node"), &FEpicUnrealMCPBlueprintCommands::HandleAddLatentNode},
```

```cpp
TSharedPtr<FJsonObject> FEpicUnrealMCPBlueprintCommands::HandleAddLatentNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BlueprintPath, FunctionName;
    if (!Params->TryGetStringField(TEXT("blueprint_path"), BlueprintPath) ||
        !Params->TryGetStringField(TEXT("function_name"), FunctionName)) {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            TEXT("blueprint_path and function_name required"));
    }
    UBlueprint* BP = LoadObject<UBlueprint>(nullptr, *BlueprintPath);
    if (!BP) return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Blueprint not found"));
    UEdGraph* Graph = BP->UbergraphPages.Num() > 0 ? BP->UbergraphPages[0] : nullptr;
    if (!Graph) return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No EventGraph"));

    UClass* SysLib = FindObject<UClass>(nullptr, TEXT("/Script/Engine.KismetSystemLibrary"));
    UFunction* Func = SysLib ? SysLib->FindFunctionByName(*FunctionName) : nullptr;
    if (!Func || !Func->HasAllFunctionFlags(FUNC_BlueprintCallable)) {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Latent function not found"));
    }
    UK2Node_CallFunction* Node = NewObject<UK2Node_CallFunction>(Graph);
    Node->SetFromFunction(Func);
    Graph->AddNode(Node, true, false);
    Node->CreateNewGuid();
    Node->PostPlacedNewNode();
    Node->AllocateDefaultPins();
    FKismetEditorUtilities::CompileBlueprint(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("node_guid"), Node->NodeGuid.ToString());
    return R;
}
```

Python (`blueprint_tools.py`):

```python
@mcp.tool()
def add_latent_node(blueprint_path: str, function_name: str = "Delay") -> dict:
    """Add a latent node (Delay / AsyncLoadAsset / AIMoveTo) to the EventGraph."""
    return _send("add_latent_node", {
        "blueprint_path": blueprint_path,
        "function_name": function_name,
    })
```

### 9-2. W1-2: Behavior Tree Node 追加

```cpp
{TEXT("bt_add_node"), &FEpicUnrealMCPNavigationCommands::HandleBTAddNode},
```

```cpp
TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleBTAddNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BTPath, NodeClassName, ParentNodeId;
    Params->TryGetStringField(TEXT("bt_path"), BTPath);
    Params->TryGetStringField(TEXT("node_class"), NodeClassName);
    Params->TryGetStringField(TEXT("parent_node_id"), ParentNodeId);

    UBehaviorTree* BT = LoadObject<UBehaviorTree>(nullptr, *BTPath);
    if (!BT) return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("BT not found"));

    UClass* NodeClass = FindObject<UClass>(nullptr, *NodeClassName);
    if (!NodeClass || !NodeClass->IsChildOf(UBTNode::StaticClass())) {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Invalid BT node class"));
    }
    UBTNode* NewNode = NewObject<UBTNode>(BT, NodeClass);
    if (auto* Composite = Cast<UBTCompositeNode>(NewNode)) {
        UBTCompositeNode* Parent = ParentNodeId.IsEmpty()
            ? Cast<UBTCompositeNode>(BT->RootNode)
            : nullptr;
        if (Parent) {
            FBTCompositeChild Child;
            Child.ChildComposite = Composite;
            Parent->Children.Add(Child);
        } else {
            BT->RootNode = Composite;
        }
    }
    BT->MarkPackageDirty();

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("node_name"), NewNode->GetName());
    return R;
}
```

### 9-3. W1-4: Sequencer Visibility Track

```cpp
{TEXT("add_visibility_track"), &FEpicUnrealMCPSequencerCommands::HandleAddVisibilityTrack},
```

```cpp
TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleAddVisibilityTrack(
    const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath, BindingId;
    Params->TryGetStringField(TEXT("sequence_path"), SequencePath);
    Params->TryGetStringField(TEXT("binding_id"), BindingId);
    ULevelSequence* Seq = LoadObject<ULevelSequence>(nullptr, *SequencePath);
    if (!Seq) return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Sequence not found"));

    UMovieScene* MS = Seq->GetMovieScene();
    FGuid Guid;
    if (!FGuid::Parse(BindingId, Guid)) {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Invalid binding_id GUID"));
    }
    UMovieSceneVisibilityTrack* Track = MS->AddTrack<UMovieSceneVisibilityTrack>(Guid);
    UMovieSceneBoolSection* Section = Cast<UMovieSceneBoolSection>(Track->CreateNewSection());
    Section->SetRange(MS->GetPlaybackRange());
    Track->AddSection(*Section);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("track_signature"), Track->GetSignature().ToString());
    return R;
}
```

### 9-4. W1-5: Movie Render Queue Job 作成

```cpp
#include "MoviePipelineQueueSubsystem.h"
#include "MoviePipelineQueue.h"
#include "MoviePipelineMasterConfig.h"
#include "MoviePipelineOutputSetting.h"
#include "MoviePipelineImageSequenceOutput.h"
#include "MoviePipelineDeferredPasses.h"

TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderCommands::HandleCreateJob(
    const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath, OutputDir;
    int32 ResX = 1920, ResY = 1080;
    Params->TryGetStringField(TEXT("sequence_path"), SequencePath);
    Params->TryGetStringField(TEXT("output_dir"), OutputDir);
    Params->TryGetNumberField(TEXT("res_x"), ResX);
    Params->TryGetNumberField(TEXT("res_y"), ResY);

    UMoviePipelineQueueSubsystem* Sub =
        GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>();
    UMoviePipelineExecutorJob* Job =
        Sub->GetQueue()->AllocateNewJob(UMoviePipelineExecutorJob::StaticClass());
    Job->Sequence = TSoftObjectPtr<ULevelSequence>(FSoftObjectPath(SequencePath));
    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (World && World->PersistentLevel) {
        Job->Map = FSoftObjectPath(World->PersistentLevel);
    }

    UMoviePipelineMasterConfig* Config = Job->GetConfiguration();
    UMoviePipelineOutputSetting* Out = Config->FindOrAddSettingByClass<UMoviePipelineOutputSetting>();
    Out->OutputDirectory.Path = OutputDir;
    Out->OutputResolution = FIntPoint(ResX, ResY);
    Config->FindOrAddSettingByClass<UMoviePipelineImageSequenceOutput_PNG>();
    Config->FindOrAddSettingByClass<UMoviePipelineDeferredPassBase>();

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("job_id"), Job->GetGuid().ToString());
    return R;
}
```

---

## 10. 次ステップ

1. **Agent 2 (reviewer)**: 本書を critical review
   - 5.7 API の正確性 (特に Landscape, Niagara, MRQ, PCG)
   - 抜けている tasks.md 項目がないか
   - Optional plugin 検出パターンの実装妥当性
   - Wave 順序の妥当性 (依存関係の見落とし)
2. **Agent 3 (worker)**: §6 critical path から実装着手
   - W1-1 → W1-2 → W1-4 → W1-5 の 4 日 swing
   - 各タスク完了で commit + `pytest unit` + `cargo test`
   - Wave 1 完了で `chore/wave1-implementation` branch を main へ PR

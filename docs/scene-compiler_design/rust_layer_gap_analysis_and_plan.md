# Rust Scene Compiler — 残存ギャップ洗い出しと解決プラン

## 現在の状態サマリー

- **143 tests passing** — スケルトン実装は構造的に完了
- **9 compiler passes** 稼働中（Import → GraphBuild → InferAnchors → GeometryLowering → Normalize → Realize → ConstraintSolve → Validate → Diff）
- **12 validation rules** 実装済み
- **主要なギャップ**: 幾何深度、IR完全性、パイプライン機能、APIエンドポイント、テスト戦略

---

## フェーズ別ギャップ分析

### Phase 1: Geometry Hardening（1〜2週間）

| 項目 | 状態 | 詳細 |
|------|------|------|
| `geom/units.rs` | 完了 | Cm, Degrees, Radians |
| `geom/aabb.rs` | 完了 | Aabb3, intersects, contains_point, merge |
| `geom/segment.rs` | 完了 | Segment2/3, intersects, length, midpoint |
| `geom/polygon.rs` | 完了 | Polygon2 with geo::BooleanOps |
| `geom/intersection.rs` | 完了 | segment_intersection_2d |
| `geom/footprint.rs` | **浅い** | AABBベースのみ。設計では `geo::Polygon` ベースの `Footprint2` |
| `geom/spatial_index.rs` | **浅い** | 2D footprintのみ。3D volume index未実装 |
| `geom/obb.rs` | **未実装** | 設計必須: Obb3 for rotated walls/gates |
| `geom/vec.rs` | **未実装** | glamラッパー・ドメインVec3統合 |
| `geom/clearance.rs` | **未実装** | 設計必須: clearance query |
| `geom/triangulation.rs` | **未実装** | 設計推奨: earcutr/spade連携 |
| `robust` crate | **未導入** | Cargo.tomlに未記載 |
| `spade`, `earcutr` | **未導入** | 中期導入ライブラリ |

**完了条件ギャップ:**
- ❌ Z-fighting検出: 実装済みだがFootprint2がAABBベースなので不正確
- ❌ 同一layer overlap: AABBベースなので回転オブジェクトで誤検出
- ❌ `invalid sceneでapplyが止まる`: ValidatePassはdiagnosticsを集めるが、pipelineの`run()`でerror時に止めていない

---

### Phase 2: Compiler Pipeline Formalization（2〜4週間）

| 項目 | 状態 | 詳細 |
|------|------|------|
| `compiler/pipeline.rs` | **浅い** | `compile_preview`のみ。`compile/plan`, `compile/apply`未実装 |
| `compiler/context.rs` | **浅い** | `CompilerContext`に `semantic_scene`, `layout_ir`, `geometric_ir`, `sync_ir` がない |
| `compiler/passes/import.rs` | **浅い** | `SemanticScene` IRを生成していない |
| `compiler/passes/normalize.rs` | **浅い** | tag順序・rotation正規化のみ。単位統一が不完全 |
| `compiler/passes/graph_build.rs` | **浅い** | petgraphは使っているが、orphan/cyclic診断が不完全 |
| `compiler/passes/infer_anchors.rs` | **浅い** | orphan towerのみ。wall→tower endpoint、gate投影、bridge接続未実装 |
| `compiler/passes/lower_geometry.rs` | **浅い** | Footprint2生成のみ。OBB lowering、nav surface hint未実装 |
| `compiler/passes/realize.rs` | **浅い** | `blockout()` のみ。`asset_binding`, `detail`, `finalize` 未実装 |
| `compiler/passes/diff.rs` | **浅い** | カウントのみ。actual snapshot比較、instance set diff未実装 |
| `compiler/passes/validate.rs` | **浅い** | rule一覧は充実。`has_errors`で止める機構がpipelineにない |
| `ir/semantic.rs` | **未実装** | SemanticScene, SemanticEntity, SemanticKind enum |
| `ir/geometric.rs` | **未実装** | GeometricIr, VolumePrimitive, FootprintPrimitive |
| `ir/sync.rs` | **未実装** | SyncIr |
| `ir/source_map.rs` | **未実装** | entity_id ↔ generated part の追跡 |
| snapshot tests | **未実装** | `insta` crate未導入 |

**完了条件ギャップ:**
- ❌ `denormalize_layout` が pipeline 経由: `compile_preview`で呼ぶが、既存の`preview_layout`/`denormalize_layout_route`は旧経路のまま
- ❌ 各passのsnapshot test: 未実装
- ❌ diagnosticsにsource entity / generated part: Diagnostic builderに`entity_id`/`generated_part`フィールドはあるが、ほぼ未設定

---

### Phase 3: Castle Validator（2〜4週間）

| 項目 | 状態 | 詳細 |
|------|------|------|
| `no_nan_transform` | 完了 | NaN検出 |
| `no_zero_scale` | 完了 | scale<=0検出 |
| `no_duplicate_mcp_id` | 完了 | 重複検出 |
| `no_overlap` | **浅い** | AABBベース。設計では `geo::Polygon` ベースの正確なoverlap |
| `no_z_fighting` | **浅い** | AABB+Z差分。設計では surface-like + footprint intersection |
| `tower_wall_connectivity` | **浅い** | 距離ベース。設計では endpoint/corner接続 |
| `wall_self_intersection` | **浅い** | Polygon2 overlap使用。設計では segment intersection |
| `gate_opening_width` | 完了 | scale.x閾値 |
| `bridge_crosses_moat` | 完了 | footprint intersection |
| `bridge_endpoint_grounded` | 完了 | Z高さ範囲 |
| `keep_inside_boundary` | **浅い** | BBOX包含。設計では wall polygon 内側判定 |
| `moat_offset_validity` | 完了 | moat-structure overlap |
| **GroundContact** | **未実装** | 設計必須: tower/keepのZ=0接地検査 |
| **WallSpanValid** | **未実装** | 設計必須: wall segment length > 0, thickness >= min |
| **NavWalkability** | **未実装** | 設計必須: nav surface覆域検査 |
| **PatrolRouteFeasibility** | **未実装** | 設計推奨: patrol point到達可能性 |
| repair suggestion | **欠損** | 大半のruleで`suggestion`未設定 |

**完了条件ギャップ:**
- ❌ moat+bridge+gatehouseのinvalid case検出: 個別ruleはあるが統合E2Eがない
- ❌ repair suggestion: 3/12 ruleのみsuggestionあり
- ❌ E2E fixture増加: 未着手

---

### Phase 4: InstanceSet IR（3〜6週間）

| 項目 | 状態 | 詳細 |
|------|------|------|
| `ir/instance_set.rs` | **浅い** | `InstanceSet`, `InstanceSetCommand`完了。`group_into_instance_sets`は基本形のみ |
| `RenderItem` | 完了 | `Actor`, `InstanceSet` enum |
| `spawn_instance_set` (Rust→TCP) | 完了 | UnrealClientに実装済み |
| `update_instance_set` (Rust→TCP) | 完了 | UnrealClientに実装済み |
| C++側 ISM/HISM command | **未確認/未実装** | `spawn_instance_set`, `update_instance_set` C++ handler要確認 |
| sync planでのactor/instance set分離 | **未実装** | plannerは従来のactor単位のみ |
| cell_id付与 | **未実装** | `group_into_instance_sets`で`cell_id=None`固定 |
| repeated primitive grouping | **浅い** | mesh+material+kindのみ。LOD policy未考慮 |

**完了条件ギャップ:**
- ❌ crenellations/wall stones/floor tilesをInstanceSet化: grouping関数はあるが、detail generationが未実装のため実質未使用
- ❌ actor数削減: blockoutのみなので効果未発揮
- ❌ instance update/delete: C++側の対応要確認

---

### Phase 5: Constraint-assisted Layout（1〜2か月）

| 項目 | 状態 | 詳細 |
|------|------|------|
| `layout/constraint.rs` | **スケルトン** | enum定義のみ。実際の幾何検査なし |
| `ConstraintSolvePass` | **スケルトン** | 空のhard/softリストを評価するだけ |
| `evaluate_hard_constraints` | **ダミー** | tower_id毎に固定suggestionを返すだけ。幾何検査なし |
| `evaluate_soft_score` | **ダミー** | hardcoded center位置を使うのみ。実際のオブジェクト位置未参照 |
| constraint抽出 | **未実装** | SceneObject → Hard/Soft Constraint の変換がない |
| local search | **未実装** | 設計推奨 |
| candidate generation | **未実装** | repair suggestionからの修正候補生成 |

**完了条件ギャップ:**
- ❌ 「門は南側」「keepは中央寄り」などを制約として扱う: SoftConstraint enumはあるが、シーンからの抽出・評価が未実装
- ❌ 失敗時に修正候補を出す: ダミーのsuggestionのみ

---

### Phase 6: World-scale Deployment（長期）

| 項目 | 状態 | 詳細 |
|------|------|------|
| `ir/world_cell.rs` | **浅い** | `WorldCell`構造体、`partition_into_cells`は固定gridのみ |
| `sync/cell_aware.rs` | **スケルトン** | `CellAwareSyncPlan`, `DeferredCommand`, `split_by_cell_availability`は型だけ |
| `dirty_hash` | **未実装** | 常に空文字 |
| cell loading state連携 | **未実装** | Unreal WP cell状態の取得・反映 |
| partial update | **未実装** | cell単位の差分apply |
| deferred command実行 | **未実装** | 未ロードcellへの遅延command queue |

**完了条件ギャップ:**
- ❌ 巨大城・街・道路網をcell単位でapply: 構造のみ
- ❌ partial update: 未実装
- ❌ sync runのcell単位追跡: 未実装

---

### API / Routes

| エンドポイント | 状態 |
|---------------|------|
| `POST /layouts/{scene_id}/compile/preview` | 完了 |
| `POST /layouts/{scene_id}/validate` | **未実装** |
| `POST /layouts/{scene_id}/compile/plan` | **未実装** |
| `POST /layouts/{scene_id}/compile/apply` | **未実装** |

---

### テスト・品質

| 項目 | 状態 |
|------|------|
| Unit tests | 143個完了。geom/compiler/validation/ruleごとにあり |
| Snapshot tests (insta) | **未導入** |
| Property tests (proptest) | **未導入** |
| E2E fixture (castle) | **未着手** |
| Benchmark (criterion) | **未導入** |

---

## 実装プラン（優先順位順）

### Sprint A: 基盤強化（1週間）

**目標: Phase 1の完了条件を満たし、Pipelineの安全性を確保する**

1. **`geom/obb.rs` 新規作成**
   - `Obb3` struct: center, half_extents, rotation (Quat)
   - `from_scene_object` for rotated walls/gates
   - `intersects_obb`, `to_aabb`
   - 用途: wall/gatehouseの正確なoverlap検出

2. **`Footprint2` → `geo::Polygon` 移行準備**
   - 既存のAABB版 `Footprint2` を `Footprint2Aabb` にrename（後方互換）
   - 新 `Footprint2` struct: `geo::Polygon<f64> + source_entity_id + layer`
   - `from_scene_object` でOBB→Polygon projection
   - `Polygon2` を統合または明確に分離

3. **`compiler/pipeline.rs` に validation error 停止機構**
   - `run()` 内で `ValidatePass::has_errors()` をチェック
   - errorがあれば `CompileResult` を返すが、stageを `"failed_validation"` に
   - または `Result<CompileResult, AppError>` に変換
   - APIルートでerror時にapplyを拒否

4. **`no_overlap` / `no_z_fighting` の精度向上**
   - AABB overlap → `geo::Polygon` intersection（正確な2D polygon overlap）
   - z-fighting: surface-like + polygon intersects + Z差分 < epsilon

---

### Sprint B: IR完成とPipeline深化（2週間）

**目標: Phase 2の完了条件を満たす**

5. **`ir/semantic.rs` 新規作成**
   - `SemanticScene`, `SemanticEntity`, `SemanticKind` enum
   - `ImportPass` を `SemanticScene` を生成するように変更
   - `GraphBuildPass` は `SemanticScene` を入力に

6. **`ir/geometric.rs` 新規作成**
   - `GeometricIr`, `VolumePrimitive` enum (Aabb3, Obb3, ExtrudedFootprint)
   - `GeometryLoweringPass` は `GeometricIr` を生成
   - `compiler/context.rs` に `geometric_ir` フィールド追加

7. **`compiler/passes/realize.rs` 拡張**
   - `RealizePass::asset_binding()`, `::detail()`, `::finalize()`
   - `asset_binding`: `asset_ref` に blueprint/mesh path を設定
   - `detail`: crenellation生成（`layout/crenellations.rs` を統合）
   - `finalize`: LOD/collision policy確定

8. **`compiler/passes/diff.rs` 深化**
   - actual snapshotとの比較（optionalでactual actorsを受け取る）
   - `SyncOperation` 生成
   - instance set vs existing instance component の差分

9. **`compiler/passes/infer_anchors.rs` 拡張**
   - wall → tower endpoint 接続
   - gate位置をwall segment上に投影
   - bridge両端をroad/gate/terrainに接続

10. **Snapshot tests導入**
    - `insta` を Cargo.toml dev-dependencies に追加
    - `compiler/pipeline.rs` のテストをsnapshot化
    - fixture: `castle_minimal`, `castle_four_towers`

---

### Sprint C: Validator深化（2週間）

**目標: Phase 3の完了条件を満たす**

11. **新規 validation rule 作成**
    - `validation/rules/ground_contact.rs`: tower/keepのZ<=epsilon検査
    - `validation/rules/wall_span_valid.rs`: wall segment length > 0, thickness >= min_thickness
    - `validation/rules/nav_walkability.rs`: nav surface覆域（skeleton可）

12. **既存 rule の精度向上**
    - `tower_wall_connectivity`: 距離ベース → endpoint/corner接続ベース
    - `keep_inside_boundary`: BBOX → wall polygon 内側判定（ray casting）
    - `wall_self_intersection`: Polygon2 overlap → segment intersection cascade

13. **Repair suggestion 全rule統一**
    - `Diagnostic::with_suggestion()` を全ruleで設定
    - suggestion内容: 具体的なアクション（"Move tower to (x,y)", "Increase gate scale.x to 3.0"）

14. **E2E fixture作成**
    - `fixtures/castle_with_moat_bridge.json`
    - `fixtures/invalid_zfight.json`
    - `fixtures/invalid_overlap.json`
    - Python E2EまたはRust integration testで読み込み

---

### Sprint D: InstanceSet & Sync深化（2〜3週間）

**目標: Phase 4の主要機能を稼働させる**

15. **`group_into_instance_sets` 拡張**
    - cell_id付与: `world_cells` と紐付け
    - LOD policy考慮（distance-based LOD group）
    - `InstanceSet` の `custom_data` に LOD 情報

16. **Sync plannerでactor/instance set分離**
    - `plan_sync` で `RenderItem` に分類
    - Actor operation と InstanceSet operation を分けて `SyncPlan` に格納
    - `applier` で `spawn_instance_set` / `update_instance_set` を呼び分け

17. **C++側 ISM/HISM handler（連携）**
    - C++ `Private/Commands/` に `SpawnInstanceSetCommand`, `UpdateInstanceSetCommand` 追加
    - `InstancedStaticMeshComponent` / `HierarchicalInstancedStaticMeshComponent` 生成
    - これはC++層作業だが、Rust側のprotocol定義（command名、payload形式）を固定する

---

### Sprint E: Constraint Solver（3〜4週間）

**目標: Phase 5の「検査+repair suggestion」を本物にする**

18. **SceneObject → Constraint 抽出**
    - `layout/constraint.rs` に `extract_constraints(objects: &[SceneObject]) -> (Vec<HardConstraint>, Vec<SoftConstraint>)`
    - tower+wall位置から `TowerConnectedToWall` 生成
    - keep+wall polygonから `KeepInsideBoundary` 生成
    - bridge+moat footprintから `BridgeCrossesMoat` 生成
    - gate rotationから `GateFacing` 生成

19. **幾何検査による constraint evaluation**
    - `TowerConnectedToWall`: tower位置とwall endpoint/cornerの距離 < threshold
    - `KeepInsideBoundary`: keep centerがwall polygon内か（point-in-polygon）
    - `BridgeCrossesMoat`: bridge footprintとmoat footprintのintersection area > 0
    - `GateFacing`: gate yawとpreferred_yawの差分

20. **Local repair / candidate generation**
    - `RepairSuggestion` に修正後の想定値を含める（`suggested_transform: Option<Transform>`）
    - tower未接続 → 最近傍wall endpointへの移動候補
    - keep外側 → polygon centroidへの移動候補
    - gate非南向き → yaw=180.0への回転候補

21. **`ConstraintSolvePass` 統合**
    - 実際のSceneObjectからconstraint抽出
    - hard violation → Error diagnostic
    - soft score → Info diagnostic
    - repair suggestion → diagnosticに紐付け

---

### Sprint F: API完成とWorld Partition（2〜3週間）

**目標: Phase 6のskeletonを機能させ、APIを完成させる**

22. **新規APIエンドポイント**
    - `POST /layouts/{scene_id}/validate`: pipeline(validate only) → diagnostics返却
    - `POST /layouts/{scene_id}/compile/plan`: compile + actual snapshot → SyncPlan返却
    - `POST /layouts/{scene_id}/compile/apply`: compile + validate + plan + apply（一括）
    - `compile/apply` はvalidation errorで拒否、allow_delete明示必須

23. **`dirty_hash` 実装**
    - cell内オブジェクトのdesired_hashを連結してSHA256
    - `CompileResult` 生成時に計算
    - partial update: dirty_hash変化したcellのみapply対象

24. **`CellAwareSyncPlan` 機能化**
    - `split_by_cell_availability`: Unrealからcell loading状態を取得（要C++連携）
    - loaded cell → immediate command
    - unloaded cell → deferred command queue
    - deferred commandの永続化（DB or in-memory）

25. **`CompileResult` summary拡張**
    - `instance_sets: usize` 追加
    - `world_cells: usize` 追加
    - `stage` に `mode` (blockout/asset_binding/detail/finalize) を反映

---

### Sprint G: テスト・品質担保（並行）

26. **`insta` snapshot tests**
    - `tests/snapshots/` 作成
    - compiler pipeline各stageの出力をsnapshot化
    - PR時のregression検出

27. **`proptest` property tests**
    - `all generated mcp_id are unique`
    - `scale > 0` after normalize
    - `AABB min <= max`
    - `no validation panic on random inputs`

28. **Benchmark導入**
    - `criterion` で `compile_pipeline`, `validate_scene`, `plan_sync` をbench
    - 目標: 1,000 objects < 100ms

---

## 推奨実装順序（依存関係考慮）

```
Sprint A (基盤)
  ├─ geom/obb.rs
  ├─ Footprint2 polygon移行
  ├─ pipeline validation stop
  └─ no_overlap/no_z_fighting精度向上

Sprint B (IR・Pipeline)
  ├─ ir/semantic.rs
  ├─ ir/geometric.rs
  ├─ realize.rs 拡張 (blockout → asset_binding/detail/finalize)
  ├─ diff.rs 深化 (actual snapshot比較)
  ├─ infer_anchors.rs 拡張
  └─ snapshot tests (insta)

Sprint C (Validator)
  ├─ ground_contact.rs
  ├─ wall_span_valid.rs
  ├─ tower_wall_connectivity 精度向上
  ├─ keep_inside_boundary 精度向上
  ├─ repair suggestion統一
  └─ E2E fixture

Sprint D (InstanceSet)
  ├─ group_into_instance_sets + cell_id
  ├─ plannerでのactor/instance分離
  └─ C++ ISM/HISM handler連携

Sprint E (Constraint)
  ├─ extract_constraints
  ├─ 幾何検査evaluation
  ├─ local repair candidate
  └─ ConstraintSolvePass統合

Sprint F (API・WP)
  ├─ /validate, /compile/plan, /compile/apply
  ├─ dirty_hash
  ├─ CellAwareSyncPlan機能化
  └─ CompileResult summary拡張

Sprint G (品質)
  ├─ snapshot tests
  ├─ property tests
  └─ benchmarks
```

---

## ファイル別変更予定一覧

### 新規ファイル

```
src/geom/obb.rs
src/geom/vec.rs
src/geom/clearance.rs
src/geom/triangulation.rs
src/ir/semantic.rs
src/ir/geometric.rs
src/ir/sync.rs
src/ir/source_map.rs
src/validation/rules/ground_contact.rs
src/validation/rules/wall_span_valid.rs
src/validation/rules/nav_walkability.rs
src/compiler/passes/apply_plan.rs  (10th pass)
tests/snapshots/
tests/fixtures/
```

### 変更ファイル（主要）

```
Cargo.toml                    # insta, proptest, criterion, robust 追加
src/geom/mod.rs               # obb, vec, clearance, triangulation 追加
src/geom/footprint.rs         # PolygonベースFootprint2移行
src/ir/mod.rs                 # semantic, geometric, sync, source_map 追加
src/ir/instance_set.rs        # cell_id付与, LOD policy
src/ir/world_cell.rs          # dirty_hash計算
src/compiler/context.rs         # semantic_ir, geometric_ir 追加
src/compiler/pipeline.rs        # validation stop, compile/plan/apply
src/compiler/ir/mod.rs          # summaryにinstance_sets, world_cells
src/compiler/passes/import.rs   # SemanticScene生成
src/compiler/passes/infer_anchors.rs  # endpoint投影, bridge接続
src/compiler/passes/lower_geometry.rs   # GeometricIr生成
src/compiler/passes/realize.rs          # asset_binding/detail/finalize
src/compiler/passes/diff.rs           # actual snapshot比較
src/compiler/passes/solve_layout.rs     # 実constraint評価
src/compiler/passes/validate.rs         # error時のpipeline挙動
src/validation/rules/mod.rs             # 新rule追加
src/validation/rules/no_overlap.rs      # Polygonベース化
src/validation/rules/no_z_fighting.rs   # Polygonベース化
src/validation/rules/tower_wall_connectivity.rs  # endpointベース化
src/validation/rules/keep_inside_boundary.rs     # point-in-polygon化
src/validation/rules/wall_self_intersection.rs   # segment intersection化
src/layout/constraint.rs        # extract_constraints, 幾何評価
src/sync/planner.rs            # actor/instance set分離
src/sync/applier.rs            # instance_set command分離
src/sync/cell_aware.rs         # cell availability連携
src/api/routes.rs              # /validate, /compile/plan, /compile/apply
src/main.rs                    # routing追加
```

---

## 中長期での crate 分割準備

設計書の「長期構成」に向けて、以下の依存関係を整理しておく。

- `geom/*` → `scene-geom` crate（純粋幾何、stdのみ）
- `ir/*` → `scene-ir` crate（serde依存）
- `validation/*` → `scene-validator` crate（geom + ir 依存）
- `compiler/*` → `scene-compiler` crate（geom + ir + validation 依存）
- `scene-syncd` → HTTP/API/DB orchestration のみ

**現段階の準備:**
- `geom` モジュール内で `domain::SceneObject` への依存を減らし、primitive型のみにする
- `validation` で `SceneObject` を直接触るのはengine層に留め、ruleはprimitive幾何に依存
- `compiler` で `db::SurrealSceneRepository` へのasync依存をpipelineのprepare層に集中させる

---

## 成功基準チェックリスト

### 短期（Sprint A〜C終了時）

- [ ] `obb.rs` 実装・テスト完了
- [ ] `Footprint2` が `geo::Polygon` ベースで動作
- [ ] validation error時にpipelineが停止/警告
- [ ] Z-fightingが正確に検出される（回転wall含む）
- [ ] 同一layer overlapが正確に検出される
- [ ] `SemanticScene` IRがImportPassから出力される
- [ ] `GeometricIr` IRがGeometryLoweringPassから出力される
- [ ] `RealizePass` が blockout/asset_binding/detail/finalize を切り替え可能
- [ ] `DiffPlanningPass` が actual snapshot と比較できる
- [ ] GroundContact, WallSpanValid ruleが稼働
- [ ] 全ruleでrepair suggestionが出力される
- [ ] snapshot test（insta）が10件以上

### 中期（Sprint D〜E終了時）

- [ ] InstanceSet groupingがcell-aware
- [ ] Sync planでactor/instance setが分離される
- [ ] C++側でISM/HISM componentが生成される
- [ ] SceneObjectからHard/Soft Constraintが抽出される
- [ ] constraint evaluationが実際の幾何を検査する
- [ ] repair suggestionに具体的な修正値が含まれる
- [ ] `POST /layouts/{scene_id}/validate` が動作
- [ ] `POST /layouts/{scene_id}/compile/plan` が動作
- [ ] `POST /layouts/{scene_id}/compile/apply` が動作
- [ ] validation error時にapplyが拒否される

### 長期（Sprint F〜G終了時）

- [ ] `dirty_hash` がcell単位で計算される
- [ ] partial update（dirty cellのみapply）が動作
- [ ] unloaded cellへのdeferred commandがqueueされる
- [ ] cell load時にdeferred commandが実行される
- [ ] 1,000 objects compile < 100ms
- [ ] 10,000 objects validation < 500ms
- [ ] proptestでpanicなしを保証
- [ ] criterion benchmarkがCIで実行可能

---

## 結論

現在のコードは「構造的には全フェーズのスケルトンが揃っている」が、「機能的にはPhase 1〜2の60%、Phase 3の50%、Phase 4の40%、Phase 5の20%、Phase 6の15%」程度の完成度である。

特に以下が未達成の最重要項目である：

1. **Pipelineの安全性**: validation errorでapplyが止まらない
2. **幾何精度**: AABBベースのままなので回転オブジェクトで誤検出
3. **IR完全性**: SemanticIr, GeometricIrが存在しない
4. **Realize深度**: blockoutのみ、asset binding/detail/finalize未実装
5. **Constraint幾何**: ダミーsuggestionから実際の幾何検査へ
6. **API完全性**: validate/plan/applyエンドポイント未実装
7. **テスト戦略**: snapshot/property/benchmark未導入

上記のSprint A〜Gで洗い出した順序に従って実装を進めることで、設計書の「短期成功基準」→「中期成功基準」→「長期成功基準」へ段階的に到達できる。

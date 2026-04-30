# Rust層強化 設計書 v1.0

## 1. 目的

本設計書は、Unreal Engine MCP コードベースにおける Rust 層を、単なる「計算処理の高速化レイヤー」ではなく、**Deterministic Scene Compiler / Geometry Validator / Sync Planner** として定義し直し、今後の実装方針・責務境界・モジュール構成・検証戦略・ロードマップを固定するためのものである。

既存の構成は大きく次の3層として整理する。

- Python層: MCP/API gateway。LLMや外部ツールとの対話、入力受付、軽量な orchestration を担当する。
- Rust層: scene compiler / geometry validator / sync planner。semantic layout を確定的な scene object / engine delta に変換し、妥当性検査と差分計画を担当する。
- C++層: Unreal Editor executor / rendering executor。Actor spawn、transform更新、material更新、ISM/HISM適用、transaction、World Partition連携など Unreal 固有実行を担当する。

最終目標は、LLMやPythonが出した曖昧な「生成意図」を、Rustが検査可能・再現可能・差分適用可能な Scene IR に落とし込み、C++/Unreal 側へ安全に適用することである。

---

## 2. 設計の結論

Rust層は、今後以下の責務を持つ中核レイヤーとして固定する。

```text
Rust Layer = deterministic scene compiler
           + robust geometry kernel
           + validation engine
           + constraint-aware layout planner
           + desired/actual sync reconciler
           + Unreal-aware batch planner
```

つまり、Rust層は「Pythonで遅い座標計算をRustに移す場所」ではない。

Rust層は、次の変換を担う。

```text
Semantic Layout Graph
  → Normalized Layout IR
  → Geometric IR
  → Validated Scene IR
  → Realization IR
  → Sync Plan
  → Unreal Delta Commands
```

この方針により、城・街・橋・道・堀・城壁・塔・NavMesh・PatrolRoute などの大規模生成を、LLMの雰囲気出力ではなく、検証可能な compiler pipeline として扱えるようにする。

---

## 3. 非目標

本設計では、次を Rust 層の主目的にしない。

- Rustで完全な剛体物理エンジンを作ること
- Unreal Engine のレンダリングや Actor lifecycle を Rust が直接実行すること
- Python層を完全に廃止すること
- C++層を薄くしすぎて Unreal 固有処理をRustに押し込むこと
- すべての procedural generation を一気に汎用 solver 化すること

物理は重要だが、Rust層の主用途は「完全物理再現」ではなく、**validation-oriented simulation** である。橋が堀を跨いでいるか、塔が地面に接地しているか、壁が自己交差していないか、NavMesh的に歩行面が意味を持つか、という事前検査に寄せる。

---

## 4. 現状の前提

現在の Rust 層には、すでに以下の重要な土台がある。

- `scene-syncd` がHTTP API境界として存在する。
- `scene / object / group / snapshot / sync / entity / relation / asset / component / blueprint / realization / layout` 系のAPIがある。
- DBには `scene_object`, `scene_entity`, `scene_relation`, `scene_asset`, `scene_component`, `scene_blueprint`, `scene_realization`, `sync_run`, `sync_operation` などの状態がある。
- `denormalizer` が `SceneEntity + SceneRelation` から `SceneObject` を生成している。
- `kind_registry` により `keep / tower / curtain_wall / gatehouse / bridge / ground` などの semantic kind を primitive に落としている。
- `span` により、壁や橋などの from/to ベースの形状を扱い始めている。
- `planner` が desired state と Unreal actual snapshot を比較して `create / update_transform / update_visual / delete / noop / conflict` に分類している。
- `applier` が chunked apply、clone grouping、hash更新、sync_run / sync_operation記録を持っている。
- `desired_hash` は timestamp を除外し、tag順序も安定化している。

このため、ゼロから作り直す必要はない。既存の `scene-syncd` を中心に、geometry kernel と validation engine を厚くし、既存 denormalizer / realization / planner / applier を compiler pipeline として整理するのが最も自然である。

---

## 5. Rust層の正式責務

### 5.1 Semantic Layout Compiler

LLM/Pythonから渡された semantic entity / relation を、決定論的に SceneObject / SceneIR へ変換する。

担当する処理:

- kindごとの意味解釈
- entity / relation graph の解決
- anchor / span / endpoint の推定
- layout normalization
- semantic kind から geometric primitive への lowering
- generated part の source mapping
- stable mcp_id 生成
- deterministic object ordering

### 5.2 Geometry Kernel

城・街・道・壁・堀・橋を安定して扱うための幾何APIを提供する。

担当する処理:

- Vec2 / Vec3 / Transform / Quaternion / Affine transform
- AABB / OBB
- Segment2 / Segment3
- Polygon2 / Footprint2
- point-in-polygon
- segment intersection
- polygon validity
- polygon offset / inset
- distance / projection
- clearance query
- spatial index
- triangulation / constrained triangulation
- swept AABB / shape cast の下準備

### 5.3 Validation Engine

生成された SceneIR が Unreal に適用可能かを検査する。

担当する処理:

- NaN transform検査
- scale 0以下検査
- mcp_id重複検査
- same-layer overlap検査
- z-fighting検査
- ground contact検査
- tower-wall connectivity検査
- gate opening width検査
- bridge reachability検査
- moat crossing検査
- keep placement検査
- wall self-intersection検査
- nav walkability検査
- patrol route feasibility検査

### 5.4 Constraint-aware Layout Planner

semantic intent を満たす配置候補を生成・修正する。

担当する処理:

- hard constraint検査
- soft constraint評価
- repair suggestion生成
- local search / simulated annealing / penalty function による改善
- 将来的な SMT / LP solver 連携

### 5.5 Sync Planner

desired state と actual state の差分を計画し、Unrealへの変更を安全に分解する。

担当する処理:

- create / update_transform / update_visual / delete / noop / conflict 分類
- delete safety
- idempotency
- sync_run / sync_operation 履歴
- deterministic plan ordering
- batch / chunking
- apply failure時の診断
- actual snapshotとの差分説明

### 5.6 Unreal-aware Batch Planner

C++/Unreal 側の実行モデルを意識したコマンド設計を行う。

担当する処理:

- Actor単位applyとInstanceSet単位applyの分類
- ISM/HISM向け instance grouping
- World Partition cell単位のapply plan
- transaction / undo unit の単位設計
- unloaded cell向け deferred command
- asset binding stage / detail stage / finalize stage の反映

---

## 6. 推奨ディレクトリ構成

短期的には単一クレート `scene-syncd` の中にモジュールを追加する。中長期では crate 分割する。

### 6.1 短期構成

```text
rust/scene-syncd/src/
  api/
  db/
  domain/
  layout/
  sync/
  unreal/

  geom/
    mod.rs
    units.rs
    vec.rs
    transform.rs
    aabb.rs
    obb.rs
    segment.rs
    polygon.rs
    footprint.rs
    spatial_index.rs
    intersection.rs
    clearance.rs
    triangulation.rs

  compiler/
    mod.rs
    context.rs
    diagnostics.rs
    pipeline.rs
    passes/
      normalize.rs
      infer_anchors.rs
      lower_geometry.rs
      solve_layout.rs
      validate.rs
      realize.rs
      diff.rs

  validation/
    mod.rs
    engine.rs
    rules/
      no_nan_transform.rs
      no_duplicate_mcp_id.rs
      no_zero_scale.rs
      no_z_fighting.rs
      no_overlap.rs
      ground_contact.rs
      wall_connectivity.rs
      bridge_reachability.rs
      gate_opening.rs
      nav_walkability.rs

  ir/
    mod.rs
    semantic.rs
    geometric.rs
    render.rs
    sync.rs
    source_map.rs
```

### 6.2 長期構成

```text
rust/
  scene-domain/
  scene-geom/
  scene-ir/
  scene-compiler/
  scene-validator/
  scene-syncd/
  scene-cli/
```

長期分割では、`scene-syncd` はHTTP/API/DB orchestrationに寄せ、幾何・IR・compiler・validatorを独立クレート化する。

---

## 7. IR設計

### 7.1 Semantic IR

LLM/Pythonから来る意味論的な構造。

```rust
pub struct SemanticScene {
    pub scene_id: SceneId,
    pub entities: Vec<SemanticEntity>,
    pub relations: Vec<SemanticRelation>,
    pub metadata: SceneMetadata,
}

pub struct SemanticEntity {
    pub entity_id: EntityId,
    pub kind: SemanticKind,
    pub name: String,
    pub properties: serde_json::Value,
    pub tags: Vec<String>,
    pub metadata: serde_json::Value,
}

pub enum SemanticKind {
    Keep,
    Tower,
    CurtainWall,
    Gatehouse,
    Bridge,
    Moat,
    Ground,
    Road,
    District,
    PatrolRoute,
    Unknown(String),
}
```

既存の `SceneEntity` をそのまま使ってもよいが、内部処理用には typed IR を用意する。

### 7.2 Layout IR

anchor / span / region / graph解決済みの中間表現。

```rust
pub struct LayoutIr {
    pub scene_id: SceneId,
    pub nodes: Vec<LayoutNode>,
    pub edges: Vec<LayoutEdge>,
    pub anchors: Vec<Anchor>,
    pub diagnostics: Vec<Diagnostic>,
}

pub struct LayoutNode {
    pub entity_id: EntityId,
    pub kind: SemanticKind,
    pub anchor: Option<AnchorRef>,
    pub span: Option<Span2>,
    pub footprint: Option<Footprint2>,
    pub layer: SceneLayer,
}
```

### 7.3 Geometric IR

幾何検査に使う表現。

```rust
pub struct GeometricIr {
    pub volumes: Vec<VolumePrimitive>,
    pub footprints: Vec<FootprintPrimitive>,
    pub connectors: Vec<Connector>,
    pub clearance_zones: Vec<ClearanceZone>,
    pub nav_surfaces: Vec<NavSurfaceHint>,
}

pub enum VolumePrimitive {
    Aabb(Aabb3),
    Obb(Obb3),
    ExtrudedFootprint { footprint: Footprint2, height: Cm },
}
```

### 7.4 Render IR

Unreal実行に近い表現。

```rust
pub enum RenderItem {
    Actor(SceneObject),
    InstanceSet(InstanceSet),
}

pub struct InstanceSet {
    pub set_id: String,
    pub mesh: AssetRef,
    pub material: Option<MaterialRef>,
    pub transforms: Vec<Transform>,
    pub custom_data: serde_json::Value,
    pub tags: Vec<String>,
}
```

### 7.5 Sync IR

Unrealに適用する差分計画。

```rust
pub struct SyncIr {
    pub scene_id: SceneId,
    pub operations: Vec<SyncOperation>,
    pub warnings: Vec<Diagnostic>,
    pub summary: SyncPlanSummary,
}
```

既存の `SyncPlan` / `SyncOperation` を拡張して使う。

---

## 8. Compiler Pipeline

Rust層の中心は pass pipeline として固定する。

```text
1. Import Pass
2. Normalize Pass
3. Graph Build Pass
4. Anchor / Span Inference Pass
5. Geometry Lowering Pass
6. Constraint Solve Pass
7. Validation Pass
8. Realization Pass
9. Diff Planning Pass
10. Apply Planning Pass
```

### 8.1 Import Pass

入力:

- `SceneEntity`
- `SceneRelation`
- `SceneAsset`
- `SceneBlueprint`
- `SceneRealization`

出力:

- `SemanticScene`

役割:

- DBから取得した構造をcompiler用にまとめる。
- deleted entity を除外または tombstone として扱う。
- unknown kind を warning / error 化する。

### 8.2 Normalize Pass

役割:

- 単位を Unreal cm に統一する。
- rotation表現を正規化する。
- tagを安定順にする。
- entity_id / mcp_id を正規化する。
- default properties を補完する。

出力は決定論的でなければならない。

### 8.3 Graph Build Pass

役割:

- `petgraph` 等を用いて entity/relation を graph 化する。
- wall → tower、bridge → moat、gate → wall などの接続関係を解決する。
- orphan entity を検出する。
- cyclic dependency を診断する。

### 8.4 Anchor / Span Inference Pass

役割:

- explicit `from/to` があれば span を作る。
- relation から endpoint を推定する。
- tower間に curtain wall を張る。
- gate位置を wall segment 上に投影する。
- bridgeの両端を road / gate / terrain に接続する。

既存の `span.rs` / `entity_resolver.rs` をこの pass に移す。

### 8.5 Geometry Lowering Pass

役割:

- semantic layout を AABB / OBB / Footprint / Segment / Polygon に変換する。
- wall thickness / height / length を反映する。
- moat offset / road offset / clearance zone を生成する。
- nav surface hint を作る。

### 8.6 Constraint Solve Pass

短期では「検査 + repair suggestion」に留める。中長期で solver を入れる。

扱う制約:

- tower は wall endpoint または corner に接続する。
- gatehouse は curtain wall 上に置く。
- bridge は moat を跨ぐ。
- keep は wall boundary 内側に置く。
- road は gatehouse から keep へ接続する。
- 同一layerの主要volumeは重ならない。
- Nav walkable surface は必要範囲を覆う。

### 8.7 Validation Pass

生成物を Unreal に送る前に検査する。

severity:

- `error`: apply禁止
- `warning`: apply可能だが修正推奨
- `info`: 診断情報

### 8.8 Realization Pass

既存の `blockout / asset_binding / detail / finalize` を formalize する。

stage:

- `blockout`: BasicShapes中心。高速preview。
- `asset_binding`: SceneAsset / SceneBlueprint に紐付ける。
- `detail`: crenellation、decoration、floor tile、road curb などを生成。
- `finalize`: instance grouping、LOD policy、collision policy を確定。

### 8.9 Diff Planning Pass

既存 planner を拡張する。

- desired object vs actual actor snapshot
- instance set vs existing instance component
- deletion safety
- conflict reason
- unchanged reason
- deterministic operation ordering

### 8.10 Apply Planning Pass

C++/Unreal側への命令単位に落とす。

- Actor command
- Batch actor command
- InstanceSet command
- Material update command
- Transaction group
- World partition cell command

---

## 9. Geometry Kernel 設計

### 9.1 Units

裸の `f64` を減らす。

```rust
#[derive(Clone, Copy, Debug, PartialEq, PartialOrd)]
pub struct Cm(pub f64);

#[derive(Clone, Copy, Debug, PartialEq, PartialOrd)]
pub struct Degrees(pub f64);

#[derive(Clone, Copy, Debug, PartialEq, PartialOrd)]
pub struct Radians(pub f64);
```

Unreal向けの座標は cm を標準にする。

### 9.2 Vector / Transform

短期:

- 既存 `Vec3 / Rotator / Transform` を維持
- 内部計算で `glam` を導入

中期:

- engine-facing transform は `glam`
- solver / exact geometry 側は `geo` / `spade` / `robust` に寄せる

### 9.3 AABB / OBB

```rust
pub struct Aabb3 {
    pub min: Vec3,
    pub max: Vec3,
}

pub struct Obb3 {
    pub center: Vec3,
    pub half_extents: Vec3,
    pub rotation: Quat,
}
```

用途:

- broad-phase overlap
- clearance query
- z-fighting candidate detection
- ground contact check

### 9.4 Footprint2

```rust
pub struct Footprint2 {
    pub polygon: geo::Polygon<f64>,
    pub source_entity_id: EntityId,
    pub layer: SceneLayer,
}
```

用途:

- wall / moat / road / district の内外判定
- overlap検査
- offset / inset
- keep inside wall検査

### 9.5 Spatial Index

`rstar` を使い、全ペア比較を避ける。

```rust
pub struct SpatialSceneIndex {
    pub volumes: RTree<IndexedAabb>,
    pub footprints: RTree<IndexedEnvelope2>,
}
```

用途:

- overlap candidate取得
- clearance candidate取得
- nearest anchor探索
- gate / bridge / road 接続探索

---

## 10. Validation Engine 設計

### 10.1 Diagnostic

```rust
pub enum Severity {
    Error,
    Warning,
    Info,
}

pub struct Diagnostic {
    pub severity: Severity,
    pub code: String,
    pub message: String,
    pub entity_id: Option<EntityId>,
    pub mcp_id: Option<String>,
    pub generated_part: Option<String>,
    pub suggestion: Option<String>,
    pub source: Option<SourceSpan>,
}
```

### 10.2 ValidationRule

```rust
pub trait ValidationRule {
    fn code(&self) -> &'static str;
    fn validate(&self, ctx: &ValidationContext) -> Vec<Diagnostic>;
}
```

### 10.3 初期ルール

最初に入れるべき rule:

```text
NoDuplicateMcpId
NoNaNTransform
NoZeroOrNegativeScale
NoSameLayerZFight
NoSameLayerOverlap
GroundContact
WallSpanValid
TowerWallConnectivity
GateOpeningWidth
BridgeCrossesMoat
BridgeEndpointGrounded
KeepInsideBoundary
```

### 10.4 Z-fighting検査

対象:

- 同一layer
- ほぼ同一Z
- footprintが重なる
- plane/cube/ground/water surface など薄いprimitive

判定:

```text
abs(z1 - z2) < epsilon_z
AND footprint_intersects(a, b)
AND both_surface_like(a, b)
```

修正提案:

- layer offset を増やす
- ground / water / road のZを分離
- thickness を持つ volume に変換

### 10.5 Bridge検査

橋は以下を満たす。

- span length > min_bridge_length
- 両端が地面または接続可能surfaceにある
- 中央部が moat / river / gap を跨ぐ
- bridge footprint と moat footprint が交差する
- bridge endpoint は moat 内に落ちない

### 10.6 Wall / Tower検査

- tower は wall endpoint / corner に近接する。
- curtain wall は self-intersection しない。
- wall segment は gatehouse opening と矛盾しない。
- crenellation は wall top に配置される。
- wall thickness は最小値以上。

---

## 11. Procedural Generation 設計

### 11.1 生成方式の優先順位

1. Rule-based generation
2. Graph-based generation
3. Constraint-assisted generation
4. Grammar-based generation
5. WFC / tile-based generation
6. Solver-backed optimization

最初から万能generatorを作らない。まず城生成に必要な deterministic rules を固め、validator と repair suggestion を強くする。

### 11.2 Castle Generator v1

入力:

```json
{
  "kind": "castle",
  "style": "medieval_european",
  "footprint": "rectangular",
  "size": {"x": 12000, "y": 9000},
  "features": ["keep", "curtain_wall", "four_towers", "gatehouse", "moat", "bridge"]
}
```

生成:

- ground
- outer wall polygon
- tower anchors
- curtain wall spans
- gatehouse
- moat offset polygon
- bridge span
- keep at weighted center
- road from gatehouse to keep
- patrol anchors

### 11.3 City / Town Generator v2

追加要素:

- district graph
- road graph
- parcel subdivision
- market square
- gate-connected main road
- river / bridge network
- visibility / patrol route

---

## 12. Sync / DB 設計

### 12.1 Source of Truth

`scene-syncd` を唯一の source-of-truth API boundary とする。

禁止:

- scenectl がDBへ直接書く
- Python MCPが直接DB更新する
- C++がdesired stateを勝手に書き換える

許可:

- Python → scene-syncd API
- scenectl → scene-syncd API
- Rust scene-syncd → DB
- Rust scene-syncd → Unreal Bridge

### 12.2 Desired / Actual / Plan

```text
Desired State: DB上のSceneObject / SceneEntity / SceneRelation
Actual State: Unreal上のActor / Component / InstanceSet snapshot
Plan: DesiredとActualの差分
Apply: PlanをUnrealへ適用
Observe: UnrealからActualを再取得
Reconcile: 必要なら再計画
```

### 12.3 Deletion Policy

delete は必ず安全策を持つ。

- `allow_delete=false` では delete operation をskip
- managed_by_mcp tag がないものは削除不可
- tombstone を残す
- sync_operation に理由を記録
- dry-run / plan-only で削除対象を表示

### 12.4 Conflict Policy

conflict 例:

- desired_hash と actual metadata hash が違う
- Unreal actorが手動変更されている
- mcp_id重複
- actor missing but DB says synced
- actor exists but desired deleted

対応:

- default: warning + skip
- force: desired wins
- preserve: actual wins, desired更新はしない
- adopt: actualをdesiredとして取り込む

---

## 13. Unreal Executor 連携

### 13.1 Actor Apply

Actor単位で扱うもの:

- keep
- tower
- gatehouse
- bridge main body
- unique blueprint actor
- interactive object

### 13.2 InstanceSet Apply

InstanceSet化するもの:

- crenellations
- wall stones
- floor tiles
- road curbs
- fences
- windows
- barrels / crates
- repeated props

Rust側は次を生成する。

```rust
pub struct InstanceSetCommand {
    pub set_id: String,
    pub mesh: AssetRef,
    pub material: Option<MaterialRef>,
    pub transforms: Vec<Transform>,
    pub cell: Option<WorldCellId>,
}
```

C++側はこれを ISM/HISM component に変換する。

### 13.3 Transaction

Rust側のapply planは transaction group を指定できるようにする。

```rust
pub struct UnrealTransactionGroup {
    pub transaction_id: String,
    pub label: String,
    pub commands: Vec<UnrealCommand>,
}
```

例:

- `Apply Castle Blockout`
- `Update North Wall`
- `Realize Castle Assets`

### 13.4 World Partition

長期では、Rust planner が cell-aware になる。

```rust
pub struct WorldCell {
    pub cell_id: String,
    pub bounds: Aabb3,
    pub object_ids: Vec<String>,
    pub dirty_hash: String,
}
```

利点:

- 巨大都市生成でapply対象を分割できる。
- 未ロードcellへのcommandを遅延できる。
- syncの単位を小さくできる。

---

## 14. ライブラリ選定

### 14.1 初期導入

```toml
[dependencies]
glam = "0.30"
geo = "0.32"
rstar = "0.12"
petgraph = "0.8"
robust = "1"
```

用途:

- `glam`: game / graphics向け transform 計算
- `geo`: 2D polygon、boolean、buffer、contains、intersection
- `rstar`: spatial index
- `petgraph`: semantic graph / road graph / patrol graph
- `robust`: 壊れやすい幾何判定の基盤

### 14.2 中期導入

```toml
spade = "2"
earcutr = "0.5"
parry3d = "0.25"
```

用途:

- `spade`: Delaunay / constrained Delaunay / Voronoi
- `earcutr`: polygon triangulation
- `parry3d`: distance / intersection / shape casting

### 14.3 テスト・ベンチ

```toml
[dev-dependencies]
insta = "1"
proptest = "1"
criterion = "0.5"
```

用途:

- `insta`: golden snapshot
- `proptest`: geometry invariant test
- `criterion`: performance benchmark

---

## 15. API設計

### 15.1 Preview Compile

```http
POST /layouts/{scene_id}/compile/preview
```

目的:

- applyせずに compiler pipeline を実行する。
- SceneObject / diagnostics / validation result を返す。

レスポンス:

```json
{
  "scene_id": "castle_001",
  "stage": "preview",
  "objects": [],
  "instance_sets": [],
  "diagnostics": [],
  "summary": {
    "errors": 0,
    "warnings": 2,
    "objects": 42,
    "instance_sets": 4
  }
}
```

### 15.2 Validate Layout

```http
POST /layouts/{scene_id}/validate
```

目的:

- DB上の semantic layout を検証する。
- Unrealには適用しない。

### 15.3 Compile and Plan

```http
POST /layouts/{scene_id}/compile/plan
```

目的:

- semantic layoutをcompileし、Unreal actual snapshotとの差分planを出す。

### 15.4 Compile and Apply

```http
POST /layouts/{scene_id}/compile/apply
```

目的:

- compile → validate → plan → apply を一括実行する。

安全条件:

- validation error があれば apply禁止
- `allow_delete` 明示必須
- `mode = blockout | asset_binding | detail | finalize`

---

## 16. テスト戦略

### 16.1 Unit Tests

対象:

- `Span`
- `Aabb3`
- `Obb3`
- `Footprint2`
- `segment_intersection`
- `point_in_polygon`
- `offset_polygon`
- `compute_transform`
- `compute_desired_hash`

### 16.2 Snapshot Tests

対象:

- SemanticScene → LayoutIR
- LayoutIR → GeometricIR
- GeometricIR → SceneObject
- SceneObject → SyncPlan

fixture:

```text
fixtures/
  castle_minimal.json
  castle_four_towers.json
  castle_with_moat_bridge.json
  fortress_multi_wall.json
  town_gate_road.json
  invalid_zfight.json
  invalid_overlap.json
```

### 16.3 Property Tests

不変条件:

```text
same input + same seed => same output
all generated mcp_id are unique
no NaN transform
scale > 0
hash excludes timestamps
hash stable under tag reorder
wall segment length > 0
span midpoint lies between endpoints
AABB min <= max
no validation panic on random inputs
```

### 16.4 E2E Tests

既存の castle E2E を拡張する。

- blockout castle apply
- moat + bridge apply
- asset binding apply
- detail generation apply
- delete dry-run
- conflict detection
- NavMesh volume + patrol route validation
- snapshot restore

---

## 17. 性能設計

### 17.1 Benchmark対象

```text
denormalize_layout
compile_pipeline
validate_scene
build_spatial_index
plan_sync
apply_scene_delta_payload_build
instance_grouping
```

### 17.2 目標値

短期目標:

- 1,000 objects compile < 100ms
- 10,000 objects validation < 500ms
- 10,000 objects plan_sync < 500ms

中期目標:

- 100,000 repeated primitives を InstanceSet に圧縮
- actor数を 1/10 以下に削減
- sync plan は deterministic ordering を維持

### 17.3 Hotspot対策

- R-treeで全ペア検査を避ける。
- JSON cloneを減らす。
- object lookupをHashMap化する。
- DB更新はbatch化する。
- instance groupingをhash keyで行う。

---

## 18. 実行ロードマップ

### Phase 0: 設計固定

成果物:

- 本設計書
- ADR: Rust層を deterministic scene compiler と定義
- ADR: geometry kernel を追加
- ADR: validation error は apply を止める

### Phase 1: Geometry Hardening

期間目安: 1〜2週間

実装:

- `geom/units.rs`
- `geom/aabb.rs`
- `geom/segment.rs`
- `geom/footprint.rs`
- `geom/intersection.rs`
- `geom/spatial_index.rs`
- `validation/diagnostics.rs`
- `validation/rules/no_nan_transform.rs`
- `validation/rules/no_zero_scale.rs`
- `validation/rules/no_z_fighting.rs`
- `validation/rules/no_overlap.rs`

完了条件:

- layout previewでdiagnosticsが返る。
- Z-fightingを検出できる。
- 同一layer overlapを検出できる。
- invalid sceneでapplyが止まる。

### Phase 2: Compiler Pipeline Formalization

期間目安: 2〜4週間

実装:

- `compiler/pipeline.rs`
- `compiler/context.rs`
- `compiler/passes/normalize.rs`
- `compiler/passes/infer_anchors.rs`
- `compiler/passes/lower_geometry.rs`
- `compiler/passes/validate.rs`
- `compiler/passes/realize.rs`
- `compiler/passes/diff.rs`

完了条件:

- `denormalize_layout` が pipeline 経由になる。
- 各passのsnapshot testがある。
- diagnosticsにsource entity / generated part が入る。

### Phase 3: Castle Validator

期間目安: 2〜4週間

実装:

- wall self-intersection
- tower-wall connectivity
- gate opening width
- keep inside boundary
- moat offset validity
- bridge crosses moat
- bridge endpoint grounded

完了条件:

- moat + bridge + gatehouse のinvalid caseを検出できる。
- repair suggestionが返る。
- E2E fixtureが増えている。

### Phase 4: InstanceSet IR

期間目安: 3〜6週間

実装:

- `RenderItem::InstanceSet`
- `InstanceSetCommand`
- repeated primitive grouping
- C++側 ISM/HISM apply command
- sync planで actor / instance set を分離

完了条件:

- crenellations / wall stones / floor tiles をInstanceSet化できる。
- actor数が大幅に減る。
- instance update / delete ができる。

### Phase 5: Constraint-assisted Layout

期間目安: 1〜2か月

実装:

- `Constraint` model
- hard constraint check
- soft score function
- local repair
- candidate generation
- optional solver integration

完了条件:

- 「門は南側」「keepは中央寄り」「橋は堀を跨ぐ」などを制約として扱える。
- 失敗時に修正候補を出せる。

### Phase 6: World-scale Deployment

期間目安: 長期

実装:

- WorldCell IR
- cell-aware sync plan
- deferred commands for unloaded cells
- World Partition metadata
- large city fixture

完了条件:

- 巨大城・街・道路網をcell単位でapplyできる。
- partial updateができる。
- sync runがcell単位で追跡できる。

---

## 19. 最初に実装する最小PR案

### PR 1: geometry units + AABB

追加:

```text
src/geom/mod.rs
src/geom/units.rs
src/geom/aabb.rs
src/geom/footprint.rs
```

内容:

- `Cm`, `Degrees`, `Radians`
- `Aabb3`
- `Aabb3::intersects`
- `Aabb3::contains_point`
- `Aabb3::from_scene_object_basic`

### PR 2: diagnostics + basic validation

追加:

```text
src/validation/mod.rs
src/validation/diagnostic.rs
src/validation/engine.rs
src/validation/rules/no_nan_transform.rs
src/validation/rules/no_zero_scale.rs
```

内容:

- `Diagnostic`
- `Severity`
- `ValidationRule`
- `ValidationEngine`
- preview routeでdiagnostics返却

### PR 3: z-fighting / overlap検査

追加:

```text
src/validation/rules/no_z_fighting.rs
src/validation/rules/no_overlap.rs
src/geom/spatial_index.rs
```

内容:

- layer / footprint / z epsilon に基づくZ-fighting検出
- R-treeによる候補絞り込み

### PR 4: compiler pipeline skeleton

追加:

```text
src/compiler/mod.rs
src/compiler/pipeline.rs
src/compiler/context.rs
src/compiler/passes/normalize.rs
src/compiler/passes/validate.rs
```

内容:

- 既存 `denormalize_layout` を pipeline の中に包む
- 将来pass追加できる形にする

---

## 20. 採用する設計判断

### ADR-001: Rust層は計算層ではなく Scene Compiler とする

理由:

- 既存コードがすでに semantic layout denormalizer、desired/actual planner、applier、realization を持っている。
- 今後の伸びしろは単純計算速度ではなく、幾何・検証・差分計画・決定論にある。

### ADR-002: 物理エンジン化ではなく Validation-oriented Simulation を採用する

理由:

- Unrealが実行時物理を担当できる。
- Rust側には事前検査、配置妥当性、静的安定性、接続性の検査が向いている。

### ADR-003: Geometry Kernel を独立モジュールにする

理由:

- layout / span / transform / builder に散った幾何処理を集約する。
- castle / town / road / moat / bridge 全体で再利用する。

### ADR-004: Validation error は apply を止める

理由:

- invalid scene をUnrealへ流すと、後段で原因特定が難しくなる。
- LLM連携では diagnostics を返すことで自己修正ループに使える。

### ADR-005: Repeated primitives は InstanceSet IR に落とす

理由:

- 大量Actor生成はUnreal側の負荷が大きい。
- crenellation、床板、石、窓などはISM/HISMに向いている。

---

## 21. 成功基準

短期成功:

- Rust層でZ-fightingとoverlapを検出できる。
- layout previewがdiagnosticsを返せる。
- same inputからsame outputが保証される。
- invalid sceneがapply前に止まる。

中期成功:

- Semantic Layout Graphをpass pipelineで処理できる。
- moat / bridge / wall / tower / gatehouse の接続性を検査できる。
- golden testsでscene compiler出力を固定できる。
- sync planにreason / diagnosticsが入る。

長期成功:

- 城下町・道路網・巨大城塞をcell/instance awareに生成できる。
- Rust層が semantic graph compiler + geometry validator + sync planner として安定する。
- C++層はUnreal executorとして薄く、しかし強く保てる。
- Python層はMCP gatewayとして軽く保てる。

---

## 22. 最終設計まとめ

このコードベースのRust層は、次のように固める。

```text
Python MCP Layer
  = 入力受付 / LLM orchestration / API gateway

Rust Scene Compiler Layer
  = semantic graph解釈
  + geometry生成
  + validation
  + constraint planning
  + desired/actual reconciliation
  + Unreal-aware batch planning

C++ Unreal Executor Layer
  = Actor / Component / ISM / HISM / Transaction / World Partition 実行
```

Rust層の最重要追加は以下である。

```text
1. Geometry Kernel
2. Validation Engine
3. Compiler Pipeline
4. Constraint-aware Layout Planner
5. InstanceSet IR
6. World Partition-aware Sync Plan
```

最初の実装は、派手なprocedural generationではなく、`geom` と `validation` から始める。

理由は単純で、生成の品質は「どれだけ作れるか」ではなく「壊れた生成物をどれだけ早く検出できるか」で決まるためである。

Rust層は、LLMが出した夢をUnrealで破綻しない製図へ変換する層である。


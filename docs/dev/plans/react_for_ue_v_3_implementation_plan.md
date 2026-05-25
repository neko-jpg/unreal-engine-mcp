# React for Unreal Engine 実装計画 v3.0

## 結論

添付の v2.0 計画はかなり良いです。特に「既存の scene-syncd / SurrealDB / sync planner / C++ bridge を壊さず、上に積む」という方針は正しいです。

ただし、zip の実コードベースを見たうえで、さらに一段未来を見るなら、v2.0 は次の 3 点を修正した方が強いです。

1. **Python の Domain Expert を“実行者”にしすぎない。**  
   Python は自然言語解釈・設計意図・パッチ生成まで。永続状態、差分、同期、冪等性、undo は Rust / scene-syncd 側を authority にする。

2. **`scene_object` に component フィールドを足すより、既存の `scene_component` を本命にする。**  
   実コードには `scene_component` テーブル、`/components/upsert`、`/components/list`、`/components/delete` が既に存在します。将来の React 的モデルでは Actor は DOM ノード、Component は props/effects に近いので、component を scene_object に押し込むのは後で苦しくなります。

3. **新規 C++ コマンド追加を最小化する。**  
   material / lighting / atmosphere / audio / Niagara は既にかなり揃っています。まず足すべきは C++ ではなく、既存コマンドを安全に束ねる `DesignPatch -> ComponentDesiredState -> Sync/Apply` の層です。

この v3.0 の設計思想は次です。

> 自然言語から直接 UE コマンドを叩くのではなく、React のように「望ましいシーン状態」を作り、差分を計画し、検証し、同期する。

---

## 1. コードベースを踏まえた現状認識

### 1.1 既に強い部分

コードベースにはすでに以下が存在します。

| 領域 | 実装状況 | コメント |
|---|---:|---|
| Python MCP tools | 683 tools | `@mcp.tool()` が 52 ファイルに分散。かなり巨大。 |
| C++ bridge | 43 handler routes | `EpicUnrealMCPBridge.cpp` で route 登録済み。 |
| TCP transport | 既存 | Python `UnrealConnection` -> UE port `55771`。 |
| Rust scene-syncd | 既存 | HTTP `:8787`。SurrealDB と sync planner/applier を保持。 |
| SurrealDB scene state | 既存 | scene / group / object / snapshot / entity / relation / component / asset / blueprint / realization。 |
| diff planner | 既存 | desired object vs actual Unreal actor の差分。 |
| batch apply | 既存 | `apply_scene_delta`、clone grouping、chunking。 |
| snapshot / restore | 既存 | DB desired state の snapshot/restore。 |
| semantic layout | 既存 | entity / relation / denormalize / preview / generate layout objects。 |
| material tools | 既存 | material instance, scalar/vector/texture parameter, batch update あり。 |
| lighting/atmosphere tools | 既存 | light intensity/color/temp, fog, sky atmosphere, volumetric fog あり。 |
| audio / Niagara | 既存 | ambient sound, audio component, Niagara component/user parameter あり。 |
| screenshot | 既存 | C++ `take_screenshot` と Python `take_screenshot_tool` あり。 |
| tests | 既存 | unit / contract / e2e がかなりある。 |

### 1.2 まだ無い部分

一方で、次はまだ存在しません。

| 欠落 | 重要度 | 補足 |
|---|---:|---|
| `Python/server/intent/` | 高 | 自然言語を構造化する層が無い。 |
| `Python/server/experts/` | 高 | mood / domain ごとの設計変換器が無い。 |
| `Python/server/dialog_tools.py` | 高 | `scene_edit` などの高レベル対話 API が無い。 |
| `Python/server/vision/` | 中 | screenshot はあるが vision feedback loop は無い。 |
| component-level diff/apply | 高 | `scene_component` はあるが sync planner/applier の中心にはまだなっていない。 |
| visual/material/lighting の永続 desired state | 高 | 直接 UE command で変えても、DB authority と完全には一致しない。 |
| patch plan / explain / review model | 高 | AI が何を変えるかを人間がレビューしにくい。 |

### 1.3 v2.0 計画で修正したいポイント

| v2.0 の項目 | v3.0 での判断 |
|---|---|
| `scene_object` に `component_type`, `props_json` 追加 | 非推奨。既存の `scene_component` を拡張する。 |
| `set_material_parameters` C++ 新規追加 | 原則不要。既存 `batch_update_material_parameters` / scalar / vector / texture を使う。Rust wrapper と PatchCompiler が足りない。 |
| `set_atmosphere_properties` C++ 新規追加 | 原則不要。既存 `set_height_fog_properties`, `set_sky_atmosphere_properties`, `set_volumetric_fog` を facade 化する。 |
| `take_actor_screenshot` C++ 新規追加 | MVP では不要。既存 `viewport_action focus_actor` + `take_screenshot` で代替。必要になったら actor bounds/camera framing を追加。 |
| Vision KPI に SSIM | mood 変更には不向き。参照画像マッチには SSIM、雰囲気評価には VLM rubric + luminance/fog/contrast 指標を使う。 |
| `scene_restore(name)` | 既存 restore は snapshot_id 前提。name で復元したいなら name -> latest snapshot_id resolver を実装する。 |

---

## 2. v3.0 アーキテクチャ

### 2.1 全体像

```text
User / AI Agent
  |
  v
Python MCP: scene_edit / scene_refine / scene_preview
  |
  v
SceneContextPack
  - objects
  - entities
  - components
  - assets
  - snapshots
  - recent operations
  |
  v
IntentResolver
  - action
  - target selector
  - mood/style
  - constraints
  - risk level
  |
  v
StrategyPlanner
  - which experts?
  - what order?
  - dry-run or apply?
  |
  v
Domain Experts
  - LightingExpert
  - MaterialExpert
  - AtmosphereExpert
  - AudioExpert
  - VFXExpert
  - LayoutExpert later
  - CinematicExpert later
  |
  v
DesignPatch
  - entity patches
  - object patches
  - component patches
  - asset patches
  - direct command patches, temporary only
  - validation probes
  |
  v
PatchCompiler
  |
  +--> scene-syncd desired state upsert
  |      - scene_object
  |      - scene_entity
  |      - scene_component
  |      - scene_asset
  |
  +--> preview plan
  |
  v
scene-syncd
  - validation
  - diff planning
  - sync apply
  - operation record
  - snapshot / restore
  |
  v
Unreal C++ Bridge
  - atomic UE operations only
```

### 2.2 役割分担

| 層 | 責務 | やらせないこと |
|---|---|---|
| Python Intent layer | 自然言語解釈、曖昧性解決、DesignPatch 生成 | authoritative state を持たない。直接 UE を乱打しない。 |
| Python Experts | domain-specific な設計提案 | DB と UE の同期責任を持たない。 |
| Rust scene-syncd | 永続状態、差分、検証、冪等適用、履歴 | LLM 判断を持たない。 |
| C++ Bridge | UE 内の原子的操作 | 高レベル意図解釈を持たない。 |
| UE Editor | actual state | desired state の真実にはしない。 |

---

## 3. 中核モデル: `SpecGraphDelta` ではなく `DesignPatch`

v2.0 の `SpecGraphDelta` は良い出発点ですが、将来性を考えると名前と粒度を広げた方がいいです。

`SpecGraphDelta` だと「SpecGraph に差分を当てる」印象が強く、material / fog / Niagara / audio / post-process / camera / validation / preview まで包みにくいです。

v3.0 では `DesignPatch` を中心にします。

```python
@dataclass
class DesignPatch:
    patch_id: str
    scene_id: str
    intent: Intent
    summary: str
    risk_level: Literal["safe", "review", "destructive"]
    object_patches: list[ObjectPatch] = field(default_factory=list)
    entity_patches: list[EntityPatch] = field(default_factory=list)
    component_patches: list[ComponentPatch] = field(default_factory=list)
    asset_patches: list[AssetPatch] = field(default_factory=list)
    validation_probes: list[ValidationProbe] = field(default_factory=list)
    direct_commands: list[DirectCommandPatch] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
```

### 3.1 Patch 種別

| Patch | 目的 | 永続先 |
|---|---|---|
| `ObjectPatch` | Actor の create/update/delete | `scene_object` |
| `EntityPatch` | semantic entity の追加・変更 | `scene_entity` |
| `ComponentPatch` | light/material/audio/vfx/fog/nav/collision/AI など | `scene_component` |
| `AssetPatch` | material instance, Niagara system, sound cue など | `scene_asset` / UE asset command |
| `ValidationProbe` | apply 前後の検証 | Rust validation / UE validation tools |
| `DirectCommandPatch` | まだ DB モデル化していない一時的 UE command | `scene_operation` に記録し、将来 component 化する |

### 3.2 なぜ DesignPatch が重要か

今後、ユーザーの指示はこうなります。

- 「不気味にして」
- 「大阪城っぽく、でもゲームで軽い感じで」
- 「この画像に近づけて」
- 「VR でも 90fps 出る範囲で豪華に」
- 「前の案の暗さだけ残して、霧は戻して」

これらは単なる Actor 差分ではありません。設計意図、制約、対象、検証、説明可能性が必要です。

`DesignPatch` は、将来的に以下へ拡張できます。

- multi-agent review
- user approval workflow
- style preset marketplace
- reusable mood pack
- procedural asset generation
- live autosync
- collaborative editing
- reference image guided editing
- budget-aware rendering optimization

---

## 4. React for UE としての対応関係

このプロジェクトを本当に「React for UE」として伸ばすなら、React の比喩をかなり真面目に設計へ落とすべきです。

| React | Unreal 版 |
|---|---|
| component | `scene_entity` + `scene_component` |
| props | component `properties` |
| key | `entity_id` / `mcp_id` |
| virtual DOM | desired scene state in SurrealDB |
| reconciler | scene-syncd sync planner |
| commit phase | scene-syncd applier -> C++ bridge |
| effects | audio / VFX / lighting / material / post-process commands |
| state snapshot | `scene_snapshot` |
| hydration | `scene_import_from_unreal` / actual observation |
| error boundary | validation + conflict handling |
| suspense/transition | preview/draft proxy/streaming sync |

この見方を採用すると、ベストな方向は明確です。

**UE command wrapper を増やすプロジェクトではなく、Unreal scene reconciler を作るプロジェクトにする。**

---

## 5. 推奨ファイル構成

### 5.1 Python 追加

```text
Python/server/
├── dialog_tools.py
├── intent/
│   ├── __init__.py
│   ├── intent_types.py
│   ├── intent_resolver.py
│   ├── target_resolver.py
│   ├── scene_context.py
│   └── scene_summarizer.py
├── planning/
│   ├── __init__.py
│   ├── design_patch.py
│   ├── patch_compiler.py
│   ├── patch_executor.py
│   ├── capability_registry.py
│   └── safety.py
├── experts/
│   ├── __init__.py
│   ├── base_expert.py
│   ├── mood_profiles.py
│   ├── lighting_expert.py
│   ├── material_expert.py
│   ├── atmosphere_expert.py
│   ├── audio_expert.py
│   ├── vfx_expert.py
│   └── expert_router.py
└── vision/
    ├── __init__.py
    ├── screenshot.py
    ├── visual_metrics.py
    └── vision_analyzer.py
```

### 5.2 Rust 追加・変更

```text
rust/scene-syncd/src/
├── sync/
│   ├── component_planner.rs       # NEW
│   ├── component_applier.rs       # NEW
│   └── planner.rs                 # extend: object + component summary
├── api/
│   └── semantic_routes.rs         # existing; extend component endpoints if needed
├── unreal/
│   └── client.rs                  # add wrappers for material/light/fog/audio/vfx commands
└── db/
    └── surreal.rs                 # extend scene_component fields
```

### 5.3 C++ 追加は最小

最初から新 C++ command を増やすのではなく、以下だけを候補にします。

| C++ command | 必要性 | 判断 |
|---|---:|---|
| `apply_material_to_actor_by_mcp_id` | 中 | actor_name 解決を省ける。必須ではない。 |
| `set_mesh_material_parameters_by_mcp_id` | 中 | 既存 material instance 操作で足りるなら不要。 |
| `get_actor_bounds_by_mcp_id` | 高 | camera framing / actor screenshot / layout reasoning に有用。 |
| `take_actor_screenshot` | 低〜中 | `focus_actor` + screenshot で足りない時だけ。 |
| generic `set_atmosphere_properties` | 低 | 既存 specific commands を束ねればよい。 |

---

## 6. 実装フェーズ v3.0

### Phase A: Capability Matrix と設計土台

**期間:** 2 日

目的は「どの domain expert がどの既存 command / DB route を使えるか」を機械可読にすることです。

#### 実装

- `Python/server/planning/capability_registry.py`
- `Python/server/planning/design_patch.py`
- `Python/server/planning/safety.py`
- `Python/server/__init__.py` に `dialog_tools` import 追加

#### CapabilityRegistry 例

```python
CAPABILITIES = {
    "material.batch_update_parameters": {
        "transport": "direct_ue",
        "command": "batch_update_material_parameters",
        "durable_model": "scene_component:material",
        "risk": "safe",
    },
    "lighting.set_intensity": {
        "transport": "direct_ue_or_component_apply",
        "command": "set_light_intensity",
        "durable_model": "scene_component:light",
        "risk": "safe",
    },
    "atmosphere.set_fog": {
        "transport": "direct_ue_or_component_apply",
        "command": "set_height_fog_properties",
        "durable_model": "scene_component:atmosphere",
        "risk": "safe",
    },
}
```

#### 成果物

- 既存 683 tools を domain / transport / durability で分類した JSON/CSV
- `DesignPatch` dataclass
- `PatchSafetyReport`
- unit tests

#### 完了条件

- 既存 command の重複実装を避ける判断表ができる
- expert が direct command 名を直書きしなくなる

---

### Phase B: SceneContextPack / Scene Summarizer / Target Resolver

**期間:** 3 日

`scene_edit("make this cave creepy")` の前に、AI には対象シーンの圧縮文脈が必要です。

#### 実装

- `intent/scene_context.py`
- `intent/scene_summarizer.py`
- `intent/target_resolver.py`

#### SceneContextPack

```python
@dataclass
class SceneContextPack:
    scene_id: str
    object_count: int
    entity_count: int
    component_count: int
    objects_by_kind: dict[str, list[SceneObjectBrief]]
    entities_by_kind: dict[str, list[EntityBrief]]
    components_by_type: dict[str, list[ComponentBrief]]
    assets_by_kind: dict[str, list[AssetBrief]]
    snapshots: list[SnapshotBrief]
    recent_operations: list[OperationBrief]
    warnings: list[str]
```

#### Target Resolver

自然言語の対象指定を、安定した selector に変換します。

```text
"the cave"        -> tag/layout/entity based selection
"main tower"      -> entity kind/name fuzzy selector
"all wall torches" -> component_type=light + tags=torch + spatial relation=wall
"it"              -> last edited target from recent operations
```

#### 完了条件

- 200 actors / components でも短い context を作れる
- `scene_describe(query="lights")` が object/entity/component を横断して要約する
- target が曖昧な場合、危険な apply ではなく review mode になる

---

### Phase C: Intent Resolver v1

**期間:** 3 日

LLM を使うとしても、最初から LLM 依存にしません。基本は rule + schema + optional LLM slot filling です。

#### Intent 型

```python
@dataclass
class Intent:
    raw_text: str
    scene_id: str
    action: Literal["create", "modify", "refine", "restore", "describe", "compare"]
    domains: list[str]
    target_selector: TargetSelector
    mood: str | None
    style: str | None
    intensity: Literal["low", "medium", "high"]
    constraints: dict[str, Any]
    negative_constraints: list[str]
    requires_review: bool
```

#### 重要な方針

- `creepy` など mood は単語対応ではなく `MoodProfile` に変換する。
- LLM は `domains`, `target`, `constraints` の補完に使う。
- 実際の数値変換は deterministic profile が行う。

#### 完了条件

- 50 intent テストで 90% 以上
- `make it darker` が直前 target を参照できる
- 空シーンでは create mode に落ちる
- `delete/remove` 系は review/destructive 扱いになる

---

### Phase D: MoodProfile と Domain Experts v1

**期間:** 5 日

v2.0 の expert は正しいですが、ハードコードを避けて、mood profile を共有する形にします。

#### MoodProfile

```python
@dataclass
class MoodProfile:
    name: str
    lighting: dict[str, Any]
    material: dict[str, Any]
    atmosphere: dict[str, Any]
    audio: dict[str, Any]
    vfx: dict[str, Any]
    cinematic: dict[str, Any] = field(default_factory=dict)
    performance_budget: dict[str, Any] = field(default_factory=dict)
```

#### creepy profile 例

```python
CREEPY = MoodProfile(
    name="creepy",
    lighting={
        "global_intensity_scale": 0.35,
        "temperature": 4200,
        "color_bias": [0.45, 0.55, 0.75],
        "shadow": "strong",
        "flicker": True,
    },
    material={
        "base_color_bias": [0.22, 0.22, 0.25],
        "roughness": 0.9,
        "metallic": 0.0,
        "wetness": 0.35,
    },
    atmosphere={
        "fog_density_scale": 2.0,
        "fog_color": [0.12, 0.14, 0.18],
        "volumetric": True,
    },
    audio={
        "ambient": ["drip", "low_wind"],
        "volume": 0.35,
    },
    vfx={
        "dust": True,
        "embers": "low",
    },
)
```

#### Expert の共通 interface

```python
class BaseDomainExpert(ABC):
    domain: str

    @abstractmethod
    def propose(
        self,
        intent: Intent,
        context: SceneContextPack,
        profile: MoodProfile | None,
    ) -> list[PatchOperation]:
        ...
```

#### Expert 別方針

| Expert | 最初にやること | 既存資産 |
|---|---|---|
| LightingExpert | 既存ライトの強度/色/温度変更、必要なら torch light 追加 | `lighting_tools.py`, `LightConfigSpec` |
| MaterialExpert | material instance 作成/parameter batch update/apply | `material_tools.py`, `material_graph_tools.py` |
| AtmosphereExpert | fog / sky / volumetric 設定 | `lighting_tools.py` の atmosphere 系 |
| AudioExpert | ambient sound / attenuation | `audio_tools.py` |
| VFXExpert | Niagara component / dust / embers | `niagara_tools.py` |

#### 完了条件

- `make this cave creepy` が 10〜20 patch ops を生成
- patch は dry-run で人間が読める
- direct command は capability registry 経由
- すべて idempotent operation_id を持つ

---

### Phase E: PatchCompiler と durable component state

**期間:** 5 日

ここが v3.0 の最重要フェーズです。

v2.0 では expert が SpecGraphDelta を作って scene-syncd に渡す流れでした。v3.0 では、Expert が作る patch を DB desired state に変換します。

#### scene_component 拡張

既存 `scene_component` に以下を追加します。

```text
desired_hash: string
last_applied_hash: option<string>
sync_status: string default "pending"
deleted: bool default false
revision: int default 1
```

さらに query 用 index を追加します。

```text
scene_component_scene_type ON scene_component COLUMNS scene, component_type
scene_component_sync_status ON scene_component COLUMNS scene, sync_status
```

#### component_type 設計

```text
light
material
atmosphere
audio
vfx
post_process
camera
nav
collision
ai
render_budget
style_profile
```

#### ComponentPatch 例

```json
{
  "scene_id": "cave_test",
  "entity_id": "actor:cave_wall_01",
  "component_type": "material",
  "name": "creepy_stone_surface",
  "properties": {
    "actor_mcp_id": "cave_wall_01",
    "material_slot": 0,
    "instance_path": "/Game/MCP/Materials/MI_CreepyStone",
    "parameters": [
      {"name": "BaseColor", "type": "vector", "value": [0.18, 0.18, 0.22, 1.0]},
      {"name": "Roughness", "type": "scalar", "value": 0.92}
    ]
  }
}
```

#### Rust component planner

Object planner と同じように、component desired state も差分化します。

```text
Desired scene_component vs applied_hash
  -> CreateComponentEffect
  -> UpdateComponentEffect
  -> DeleteComponentEffect
  -> Noop
  -> Conflict
```

#### Rust component applier

component_type ごとに UE command に落とします。

| component_type | UE command |
|---|---|
| material | `create_material_instance`, `batch_update_material_parameters`, `apply_material_to_actor` |
| light | `set_light_intensity`, `set_light_color`, `set_light_temperature`, etc. |
| atmosphere | `set_height_fog_properties`, `set_sky_atmosphere_properties`, `set_volumetric_fog` |
| audio | `spawn_ambient_sound`, `add_audio_component`, `set_sound_attenuation` |
| vfx | `add_niagara_component`, `set_niagara_user_parameter`, `set_niagara_color`, etc. |

#### MVP 妥協案

Rust component applier を一気に全部作ると重い場合、最初は Python `PatchExecutor` が direct command を実行してもよいです。ただし、その場合でも必ず以下を守ります。

1. `scene_component` に desired state を保存する
2. `scene_operation` 相当のログを残す
3. operation_id を冪等にする
4. 将来 Rust applier に移せる payload にする

---

### Phase F: Dialog API v1

**期間:** 3 日

公開 MCP tool は少なく、太くします。683 tools が既にあるので、さらに細かい tool を増やすより、AI agent が迷わない高レベル API が必要です。

#### 推奨 public tools

| Tool | 役割 |
|---|---|
| `scene_edit` | 自然言語 intent -> patch plan -> optional apply |
| `scene_refine` | 直前 patch / preview を踏まえた追加修正 |
| `scene_preview` | screenshot + scene summary + patch status |
| `scene_describe` | scene context query |
| `scene_snapshot_create` | 既存 wrapper でよい |
| `scene_restore` | snapshot name/id resolver + restore + optional sync |
| `scene_explain_plan` | patch plan を人間向けに説明 |

v2.0 の「6つの API」でも成立しますが、`scene_explain_plan` は将来かなり効きます。破壊的変更や高コスト変更の前に「何を変えるつもりか」を明示できるからです。

#### `scene_edit` signature

```python
@mcp.tool()
def scene_edit(
    intent: str,
    scene_id: str = "main",
    mode: str = "dry_run",  # dry_run | apply_safe | apply_all
    create_snapshot: bool = True,
    max_operations: int = 100,
    target: Optional[str] = None,
    style_profile: Optional[str] = None,
) -> dict:
    ...
```

#### Response

```json
{
  "success": true,
  "mode": "dry_run",
  "patch_id": "patch_...",
  "summary": "Cave mood changed toward creepy: darker lights, denser fog, rougher stone material.",
  "risk_level": "review",
  "operation_count": 14,
  "requires_approval": false,
  "snapshot_id": "scene_snapshot:...",
  "plan": {...},
  "warnings": []
}
```

---

### Phase G: Vision feedback v1

**期間:** 4 日

Vision は最初から自動収束にしすぎない方がいいです。特に「不気味」のような主観的ゴールに SSIM は合いません。

#### 指標を 2 系統に分ける

| 用途 | 指標 |
|---|---|
| 参照画像に近づける | SSIM / CLIP similarity / composition comparison |
| mood を評価する | VLM rubric + luminance / contrast / fog density proxy / color temperature |

#### VisualRubric

```python
@dataclass
class VisualRubric:
    goal: str
    criteria: list[str]
    measurable_hints: dict[str, Any]
```

#### creepy cave rubric 例

```text
- Cave should appear dim but navigable
- Main silhouette should be readable
- Fog should add depth, not obscure all geometry
- Materials should look cold/rough/wet
- VFX should be subtle, not noisy
```

#### 実装

- `vision/screenshot.py`: `take_screenshot_tool` wrapper
- `vision/visual_metrics.py`: luminance / contrast / basic color metrics
- `vision/vision_analyzer.py`: VLM に screenshot + rubric を渡す
- `scene_preview`: screenshot path + summary + visual score
- `scene_refine`: feedback -> intent -> delta patch

#### 完了条件

- `scene_preview` が screenshot path と scene summary を返す
- `scene_refine("make it darker")` が前回 target/mood を継承する
- 参照画像モードと mood モードで評価指標を分ける

---

### Phase H: E2E と hardening

**期間:** 5 日

#### 必須 E2E

1. 不気味な洞窟
2. 大阪城
3. material-only update
4. lighting-only update
5. atmosphere-only update
6. direct command fallback
7. snapshot restore by name
8. 100 actor batch edit
9. repeated refine 100回
10. dry_run -> explain -> apply -> preview

#### 1000回ストレステストについて

v2.0 の 1000回微調整は良い KPI ですが、単純に scale を 1000回変えるだけだと、実用上の意味がやや薄いです。

v3.0 では 3 種類に分けます。

| テスト | 目的 |
|---|---|
| 1000 object transform edits | object diff/undo の確認 |
| 1000 component parameter edits | material/light/fog の component diff 確認 |
| 100 refine loop with snapshots | user-facing iterative workflow の確認 |

#### 合格ライン

| KPI | 目標 |
|---|---:|
| dry_run response | LLM 以外で < 2s |
| 100 actor transform sync | < 500ms target。ただし環境依存なので CI では relaxed threshold |
| component update idempotency | 同一 patch 2回目は Noop |
| restore success | 100% |
| duplicate mcp_id safety | conflict に落ちる |
| expert patch validity | 95% 以上 |
| scene summary | 200 actors/components で 2000 tokens 相当以下 |

---

## 7. 実装順序の最適解

### Week 1: 土台

- CapabilityRegistry
- DesignPatch dataclasses
- SceneContextPack
- SceneSummarizer
- TargetResolver
- dialog_tools skeleton
- `server/__init__.py` import
- FakeUnrealConnection stateful extension

### Week 2: Intent + Experts

- IntentResolver rule-first
- MoodProfile
- LightingExpert
- MaterialExpert
- AtmosphereExpert
- AudioExpert
- VFXExpert
- `scene_edit(mode="dry_run")`

### Week 3: Apply path

- PatchCompiler -> scene_object/entity/component/assets
- snapshot before apply
- direct command fallback executor
- Rust UnrealClient wrappers for missing existing commands
- component desired_hash/sync_status schema extension
- initial component planner/applier for material + light

### Week 4: Preview / Refine / Vision

- scene_preview
- screenshot wrapper
- VisualMetrics
- VisionAnalyzer optional
- scene_refine context memory
- scene_explain_plan

### Week 5: E2E / performance / docs

- cave scenario
- Osaka castle scenario
- repeated refine tests
- component idempotency tests
- docs
- demo script

### Week 6: production hardening

- migrate direct command fallback into Rust component_applier
- stronger operation ledger
- telemetry
- cache scene summaries
- refine target resolution
- add actor bounds/camera framing C++ only if still needed

---

## 8. “不気味な洞窟”の理想フロー

```text
scene_edit(
  scene_id="cave_test",
  intent="洞窟を不気味にして",
  mode="dry_run"
)
```

1. `SceneContextPack` が洞窟の壁・床・天井・既存ライト・素材を要約
2. `IntentResolver` が `mood=creepy`, `domains=[lighting, material, atmosphere, audio, vfx]` を返す
3. `TargetResolver` が洞窟 entity / actor group を選ぶ
4. 各 Expert が PatchOperation を提案
5. `DesignPatch` が生成される
6. `scene_explain_plan` が人間に説明
7. apply 時に snapshot 作成
8. PatchCompiler が `scene_component` と `scene_object` に desired state を保存
9. scene-syncd が差分を計画
10. Rust/Python executor が UE command を適用
11. `scene_preview` が screenshot + visual score を返す
12. `scene_refine("もっと暗く")` は前回 patch と target を継承して追加 patch を作る

### 生成される patch の例

```text
Lighting:
- Existing PointLight intensity x0.35
- Temperature 4200K
- Color blue/cyan bias
- Add flickering torch light near cave entrance

Atmosphere:
- ExponentialHeightFog density x2.0
- Volumetric fog enabled
- Fog color dark blue-gray

Material:
- Create/apply MI_CreepyStone
- BaseColor dark gray-blue
- Roughness 0.9
- Wetness scalar 0.35 if material supports it

Audio:
- Spawn low-volume dripping ambient sound
- Add attenuation radius

VFX:
- Add dust Niagara component
- Low spawn rate
```

---

## 9. 将来の伸ばし方

### 9.1 Style Pack / Mood Pack 化

`creepy`, `heroic`, `cyberpunk`, `ghibli-like` のような mood はコードにベタ書きせず、profile として分離します。

```text
Python/server/experts/profiles/
├── creepy.yaml
├── heroic.yaml
├── moonlit.yaml
├── osaka_castle.yaml
└── cinematic_warm.yaml
```

これにより、将来的に user/project ごとの style preset が持てます。

### 9.2 Patch Marketplace / Reusable Recipe

「不気味な洞窟化」は scene 非依存の recipe にできます。

```text
Recipe: creepy_environment_v1
Inputs:
- target space
- existing lights
- material candidates
- performance budget
Outputs:
- DesignPatch
```

### 9.3 Budget-aware Experts

Unreal では美しさだけでなく performance が大事です。

Expert は最初から budget を見るべきです。

```text
mode=prototype: BasicShapes, cheap lights, no heavy Niagara
mode=editor_preview: visually clear, medium cost
mode=game_ready: LOD/collision/nav/render budget respected
mode=cinematic: high quality, expensive acceptable
```

既存 `RealizationPolicy` とかなり相性が良いです。

### 9.4 Multi-agent future

将来、LightingAgent / MaterialAgent / PerformanceAgent / ArtDirectorAgent のように分ける場合も、`DesignPatch` を共通言語にすれば破綻しません。

各 agent は patch を提案するだけ。最終的な merge / conflict / apply は scene-syncd が見る。

### 9.5 Live autosync

将来的には SurrealDB live query と sync worker で、desired state が変わったら自動 apply できます。

ただし MVP では手動 `scene_sync` / `scene_edit(apply_safe)` にしておくべきです。自動化は便利ですが、UE Editor では暴発が怖いです。

---

## 10. リスクと対策

| リスク | 対策 |
|---|---|
| Direct UE command と DB desired state がズレる | すべて DesignPatch と scene_component に記録。direct command は fallback 扱い。 |
| Expert が勝手にやりすぎる | risk_level / max_operations / review mode / explain_plan。 |
| LLM が不安定 | deterministic MoodProfile を中心にし、LLM は slot filling。 |
| component applier が肥大化する | capability registry と component_type handler で分離。 |
| Vision が主観的 | SSIM 依存を避け、rubric + measurable metrics に分ける。 |
| tool 数がさらに増え AI が迷う | public dialog tools は少数に絞る。内部 module を増やす。 |
| snapshot restore が name/id で混乱 | `scene_restore` は name resolver を持ち、実際の restore は snapshot_id で実行。 |
| C++ 追加で保守が重くなる | 既存 command で足りる限り Python/Rust wrapper に留める。 |

---

## 11. 最優先で着手すべき PR 分割

### PR 1: DesignPatch + CapabilityRegistry

- `planning/design_patch.py`
- `planning/capability_registry.py`
- unit tests
- 既存 command 棚卸し JSON

### PR 2: SceneContextPack + scene_describe

- `intent/scene_context.py`
- `intent/scene_summarizer.py`
- `dialog_tools.py` に `scene_describe`

### PR 3: IntentResolver + TargetResolver

- `intent/intent_types.py`
- `intent/intent_resolver.py`
- `intent/target_resolver.py`
- 50 intent fixture

### PR 4: Expert skeleton + creepy profile

- `experts/base_expert.py`
- `experts/mood_profiles.py`
- 5 experts skeleton
- dry-run only

### PR 5: scene_edit dry_run

- `dialog_tools.scene_edit`
- `scene_explain_plan`
- patch safety report

### PR 6: apply_safe MVP

- snapshot before apply
- PatchCompiler -> object/entity/component upsert
- direct command fallback executor
- material/light/atmosphere first

### PR 7: component sync hardening

- Rust `scene_component` desired fields
- `component_planner.rs`
- `component_applier.rs`
- Rust UnrealClient wrappers

### PR 8: preview/refine/vision

- screenshot wrapper
- scene_preview
- scene_refine
- visual metrics
- optional VLM analyzer

### PR 9: E2E demos

- cave
- Osaka castle
- repeated refine
- snapshot restore

---

## 12. 最終提案

採用すべき方針は次です。

1. v2.0 の方向性は採用する。
2. ただし `SpecGraphDelta` 中心ではなく `DesignPatch` 中心に進化させる。
3. `scene_object` に component props を足さず、既存 `scene_component` を拡張する。
4. C++ 新規実装は最小化し、まず既存 material / lighting / atmosphere / audio / Niagara command を capability registry で束ねる。
5. Python Expert は UE を直接変更する主体ではなく、patch proposal generator にする。
6. Rust scene-syncd を React reconciler の本体として育てる。
7. Vision は SSIM だけでなく、rubric / visual metrics / VLM feedback に分ける。
8. まず dry-run / explain / snapshot / apply_safe の UX を固める。

この方針なら、短期では「自然言語でシーンを良い感じに変える」機能を早く出せます。中期では undo / review / repeated refinement に強くなります。長期では、本当に React 的な Unreal scene reconciler へ伸ばせます。

一言でいうと、ベストな未来はこれです。

> “AI が UE command を叩く” から、“AI が desired scene を設計し、scene-syncd が安全に reconcile する” へ移行する。

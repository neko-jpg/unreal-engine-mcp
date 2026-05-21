# 残作業 実装計画書 (A-2 / A-3 / B-2 / B-4 / 中長期 1〜5)

最終更新: 2026-05-18
担当: implementation planning
対象 Engine: **Unreal Engine 5.7** (UE 5.7.0 公式リリース)
前提リビジョン: `b925ec3` + 未コミット 30 files (rust/scene-syncd 配下)

---

## 0. 事前ブロッカー修正 (本ターンで実施済み)

| ファイル | 修正 | 検証 |
|---|---|---|
| `rust/scene-syncd/src/compiler/passes/diff.rs` | `#[cfg(test)] use crate::domain::{SceneObject, Transform};` を復活 | `cargo test` 332 passed |
| `rust/scene-syncd/src/ir/sync.rs` | 同上 | `cargo test` 18 passed (integration) |

**事象**: 前ターンで `Transform`/`Rotator`/`Vec3` import を削った際、`Transform::default()` の参照が残っていて `cargo test --no-run` が E0433 でコンパイル不能。`cargo build`(非 test) は通るため見落としていた。`.github/workflows/rust-checks.yml` の `cargo test` で次回 push が必ず失敗するレベルのリグレッション。

**ロールバック**: なし (元の動作に戻すだけの 2 行ずつ追加)。

---

## 1. A-2 Live E2E (UE Editor 起動を伴う 13 case smoke)

### 1.1 ゴール
`scripts/live_e2e_smoke.py` の **13 case を全 pass**、レポートを `artifacts/live_e2e_<ts>.json` に保存し、A-3 commit 群の "Live verified" 根拠として添付。

### 1.2 依存と前提
- UE 5.7 Editor が起動可能 (Win64 / Development / `FlopperamUnrealMCP 5.7/FlopperamUnrealMCP.uproject`)
- `tools/surrealdb/surreal.exe` または PATH 上の `surreal` v1.5+
- ポート空き: 55557 (Unreal bridge), 8787 (scene-syncd), 8000 (SurrealDB)

### 1.3 実行手順
```powershell
# 1) SurrealDB + scene-syncd を起動 (バックグラウンド)
python scripts\launch-dev-stack.py --surreal --scene-syncd --no-editor --no-mcp

# 2) Unreal Editor を別ウィンドウで起動 (起動完了まで待機 ~30s)
& 'C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe' `
  'C:\development\unreal-engine-mcp\FlopperamUnrealMCP 5.7\FlopperamUnrealMCP.uproject'

# 3) Editor 起動後、MCP bridge が :55557 で listening になったことを確認
Test-NetConnection 127.0.0.1 -Port 55557

# 4) 13 case smoke を一括実行
python scripts\live_e2e_smoke.py

# 5) レポート確認
Get-Content (Get-ChildItem artifacts\live_e2e_*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1) `
  | ConvertFrom-Json | Select-Object -ExpandProperty summary
```

### 1.4 case 別期待値と既知の落とし穴
| case | 期待 | 落とし穴 |
|---|---|---|
| `ping` | `type=pong` または `success=true` | none |
| `spawn_actor` / `set_actor_transform_by_mcp_id` / `delete_actor_by_mcp_id` | 全て `success=true` | actor 名衝突回避は uuid hex で担保済み |
| `scene_create` → `scene_upsert_actor` → `scene_plan_sync` → `scene_sync` | `scene_id` の state 引き継ぎを 1 run 内で実施 | SurrealDB 起動順、`scene_id` が `smoke_scene_<hex>` で生成される |
| `create_draft_proxy` / `spawn_instance_set` | HISM Component が 1 actor 内に生成 | `/Engine/BasicShapes/Cube.Cube` の参照解決 |
| `scene_create_wfc_grid_unreal` | 4x4 grid, seed=42 で deterministic | Rust 側 procedural job が同期完了 |
| `compile_all_blueprints` | `max_compiles=200`, error 0 | 既存 BP が空の場合は 0 件 pass で OK |
| `run_map_check` | `success=true`, warnings は許容 | `MapCheckLog` が "All checks passed" でなくても OK |

### 1.5 失敗時の切り分け
1. `scene-syncd` 落ち → `cargo run -p scene-syncd --release` を foreground 起動して stack trace
2. Unreal bridge 無反応 → Output Log で `UnrealMCP: TCP listener bound on 55557` を grep
3. SurrealDB 未起動 → `curl http://127.0.0.1:8000/health` で `{"status":"OK"}` 確認

### 1.6 成功基準
- `[summary] {passed: 13, failed: 0, skipped: 0, total: 13}`
- `artifacts/live_e2e_<ts>.json` を A-3 PR の証跡として添付

---

## 2. A-3 Commit 分割 (31 files / +806 -6470 を 7 commit へ)

### 2.1 ゴール
レビュア負荷を下げ、各 commit が **独立してビルド + テスト pass** する状態を作る。`git bisect` 可能にする。

### 2.2 commit 順 (依存関係順)
| # | 主旨 | 主要ファイル | 想定 LOC |
|---|---|---|---|
| 1 | C++ handler split (Phase 2/3 の完結) | `Plugins/UnrealMCP/Source/UnrealMCP/{Private,Public}/Commands/EpicUnrealMCP{Actor,Instance,Physics,Validation,Router,Navigation,Procedural}Commands.{cpp,h}` + `EpicUnrealMCPBridge.{h,cpp}` + `EpicUnrealMCPCommonUtils.*` + `EpicUnrealMCPEditorCommands.*` | -3500 / +1200 |
| 2 | Python scene tools split | `Python/server/scene_{crud,job,layout,nav_ai,procedural,sync,validate,tools_common}_tools.py`, `scene_tools.py` 縮小, `__init__.py` | -2000 / +800 |
| 3 | Rust API route split | `rust/scene-syncd/src/api/{mod,common,layout,pie,procedural,scene,semantic,sync}_routes.rs`, `routes.rs` 削除, `main.rs` 修正 | -800 / +900 |
| 4 | Procedural generation 拡張 + A-5 mojibake | `rust/scene-syncd/src/procedural/*.rs`, `Python/server/scene_procedural_tools.py`, `Python/tests/{unit,e2e}/...procedural...`, `test_p7_tools.py`, **本ターンの Transform import 復活 2 行** | +200 / -50 |
| 5 | Cesium integration (Optional plugin) + A-5 mojibake | `Plugins/.../EpicUnrealMCPCesiumCommands.*`, `Python/server/cesium_tools.py` | +600 / -10 |
| 6 | Project layout / sync 自動化 / uplugin 5.7 | `scripts/sync-unrealmcp-plugin.ps1`, `.gitignore` (`FlopperamUnrealMCP/Plugins/`), `Plugins/UnrealMCP/UnrealMCP.uplugin` (`PlatformAllowList`), `FlopperamUnrealMCP/FlopperamUnrealMCP.uproject` | +50 / -10 |
| 7 | Docs (UE 5.7 主軸化) | `README.md`, `docs/engine-version-split.md`, `docs/architecture/`, `docs/build-environment.md`, `docs/handoff-A1-to-B3.md`, **本書 `docs/implementation-plan-remaining.md`** | +500 / -200 |

### 2.3 操作手順 (各 commit 共通)
```powershell
# 0) 安全策: 作業全体をブランチ化
git checkout -b chore/split-commits-7

# 1) 対象ファイルだけ staged に
git add <files for commit N>

# 2) コミット
git commit -m "<subject per commit>"

# 3) ビルド + テスト verify (全 commit で必須)
$env:TEMP='C:\tmp\pytest'; $env:TMP='C:\tmp\pytest'; $env:PYTEST_DEBUG_TEMPROOT='C:\tmp\pytest'
python -m pytest Python\tests\unit -q -p no:cacheprovider
cd rust\scene-syncd; cargo test --quiet; cd ..\..
powershell -ExecutionPolicy Bypass -File .\scripts\sync-unrealmcp-plugin.ps1 -Verify

# 4) main の最新が来ていたら rebase
git fetch origin; git rebase origin/main
```

### 2.4 ロールバック
`git reset --soft origin/main` で 7 commit を 1 つに戻せる。push 前に `git log --oneline origin/main..HEAD` で 7 行であることを確認してから `git push origin chore/split-commits-7`。

### 2.5 成功基準
- 7 commit, 各 commit で `cargo test` / `pytest unit` 緑
- PR description に A-2 のレポート JSON を添付

### 2.6 既知の罠
- commit 4 は **本ターンで修正した Transform import 2 行を同梱しないと `cargo test` が落ちる**。手順 2 の `git add` 時に diff.rs / sync.rs を必ず含める。
- commit 1 の C++ 解体は LOC が大きく `git mv` 検出を有効化したい: `git config diff.renames true` を一時的に設定。

---

## 3. B-2 Rust clippy 段階削減 (5 layer PR)

### 3.1 ゴール
`cargo clippy --workspace --all-targets -- -D warnings` を **CI で deny** に切り替え、現在 24〜34 件の警告を 0 にする。`.github/workflows/rust-checks.yml` 行 17 は既に `cargo clippy --all-targets --all-features` を呼ぶが `-D warnings` がないため警告を見逃している。

### 3.2 警告カテゴリ集計 (実測)
| カテゴリ | 件数 | 代表箇所 |
|---|---|---|
| `too_many_arguments` | 9 (5+3+1) | `src/db/surreal.rs` `create_generator_run`, `upsert_entity`, `upsert_relation`, `upsert_asset`, `upsert_blueprint` |
| `manual_clamp` | 3 | `src/layout/crenellations.rs:37`, 他 2 箇所 |
| `needless_range_loop` | 3 | `src/geom/transform.rs:55` (`corners`), `src/?` (`r_lat`, `r_lon`) |
| `large_enum_variant` | 2 | `src/ir/render.rs:8` (`RenderItem`), `src/procedural/generator.rs:278` (`ProceduralResultVariant`) |
| `should_implement_trait` | 2 | `src/ir/semantic.rs:113` (`SemanticKind::from_str`), 他 1 |
| `field_reassign_with_default` | 1 | `src/api/procedural_routes.rs:681` (`GenerationLimits`) |
| `empty_line_after_doc_comments` | 1 | `src/unreal/ism_protocol.rs:4` |
| `manual_is_multiple_of` | 1 | (検出位置は次の PR で grep) |
| `very_complex_type` | 1 | (同上) |
| `comparison_to_zero` | 1 | (同上) |
| `items_after_test_module` | 1 | (同上) |

### 3.3 5 layer PR 計画

#### L1: 自動修正のみ (リスク最小)
`cargo clippy --workspace --all-targets --fix --allow-dirty --allow-staged` で潰せるもの:
- `empty_line_after_doc_comments`
- `field_reassign_with_default`
- `manual_clamp`
- `needless_range_loop` (一部)
- `manual_is_multiple_of`

**手順**:
```powershell
cd rust\scene-syncd
cargo clippy --workspace --all-targets --fix --allow-dirty
cargo fmt
cargo test --quiet
```
**成功基準**: 警告 -10〜13 件 / `cargo test` 緑 / diff レビュー後 PR

#### L2: 手動軽微修正
- `needless_range_loop` で `--fix` が断念したもの → `enumerate()` 手書き
- `comparison_to_zero` (例: `x == 0` → `x.is_zero()` または明示的にコメント)
- `items_after_test_module` → `#[cfg(test)] mod tests` を最下部に移動

**成功基準**: 警告 -5 件

#### L3: API 整形 (`from_str` → `FromStr` 実装)
- `src/ir/semantic.rs:113` `SemanticKind::from_str` を `impl FromStr for SemanticKind { type Err = ...; }` 実装に置換
- 呼び出し側 (`SemanticKind::from_str("keep")` → `"keep".parse::<SemanticKind>()`) を grep 修正
- 他 1 箇所も同様

**リスク**: 公開 API 変更。`#[allow(clippy::should_implement_trait)]` で見送る選択肢もあるが、計画では実装側を推奨。
**成功基準**: 警告 -2 件 / Python 側 unit/contract が緑

#### L4: 構造体引数の collapse (`too_many_arguments` x9)
9 関数のシグネチャを引数構造体に置換:
- `pub struct CreateGeneratorRunArgs<'a> { scene_id: &'a str, kind: &'a str, ... }` を `src/db/surreal.rs` に追加
- 5 つの `upsert_*` を `UpsertEntityArgs` 等に変更
- 呼び出し元 (`api/*_routes.rs`, `procedural/jobs.rs` 等) を一括書き換え

**リスク**: ヒット数最多 (9 関数 × 約 30 呼び出し点)。**1 関数 1 commit** に細分推奨。
**成功基準**: 警告 -9 件 / `cargo test` 緑 / `scene_create`, `scene_sync` の e2e 緑

#### L5: enum サイズ削減 + CI 切替
- `RenderItem::Actor(Box<SceneObject>)` 化
- `ProceduralResultVariant::Mesh { payload: Box<ProceduralMeshPayload<'static>> }` 化
- 呼び出し元 `as_ref()` / `&*` 調整
- 完了後 `.github/workflows/rust-checks.yml` 行 17 を `cargo clippy --all-targets --all-features -- -D warnings` に変更

**成功基準**: 警告 0 件 / CI が `-D warnings` で緑 / リリースビルドサイズ変化 ±5% 以内

### 3.4 ロールバック (各 L)
PR 単位で revert 可能。L4 は 1 関数 1 commit のため部分 revert も可。

---

## 4. B-4 Cesium Live (Cesium for Unreal v2.18+ インストール環境)

### 4.1 ゴール
`Cesium for Unreal` plugin がインストールされた環境で 4 関数を実機検証。`ion_access_token` がログ・レスポンスに**漏れない**ことを grep verify。

### 4.2 前提
- Cesium for Unreal v2.18+ (UE 5.7 対応版) が `FlopperamUnrealMCP 5.7/Plugins/CesiumForUnreal/` に展開済み
- `Cesium ion` アカウント発行のアクセストークン (環境変数 `CESIUM_ION_TOKEN` 経由)
- `cesium_check_plugin` が `installed=true, enabled=true, with_cesium_runtime=true` を返す

### 4.3 追加 case (scripts/live_e2e_smoke.py に追記想定)
```python
def case_cesium_check_plugin(state):
    out = _unreal_send("cesium_check_plugin", {})
    assert out.get("success") is True, out
    assert out.get("data", {}).get("installed") is True, out
    return {"unreal_result": out}

def case_cesium_setup_georeference(state):
    out = _unreal_send("cesium_setup_georeference", {
        "origin_latitude": 35.6586, "origin_longitude": 139.7454, "origin_height": 0,
    })
    assert out.get("success") is True, out
    return {"unreal_result": out}

def case_cesium_add_tileset_world_terrain(state):
    import os
    token = os.environ.get("CESIUM_ION_TOKEN", "")
    assert token, "set CESIUM_ION_TOKEN"
    out = _unreal_send("cesium_add_tileset", {
        "actor_name": "CesiumWorldTerrain_Smoke",
        "ion_asset_id": 96188, "ion_access_token": token,
    })
    assert out.get("success") is True, out
    return {"unreal_result": out}

def case_cesium_place_actor_geolocation(state):
    spawn = _unreal_send("spawn_actor", {
        "name": "cesium_pin", "type": "StaticMeshActor",
        "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        "mcp_id": "cesium_pin_smoke",
    })
    out = _unreal_send("cesium_place_actor_at_geolocation", {
        "actor_mcp_id": "cesium_pin_smoke",
        "latitude": 35.6586, "longitude": 139.7454, "height": 100.0,
    })
    assert out.get("success") is True, out
    return {"unreal_result": out}
```

### 4.4 Token 漏洩 grep verify
```powershell
$token = $env:CESIUM_ION_TOKEN
$report = Get-ChildItem artifacts\live_e2e_*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Select-String -Path $report.FullName -Pattern $token
# 期待: 0 マッチ (出力がないこと)

# Editor log 側も検査
$ueLog = "C:\development\unreal-engine-mcp\FlopperamUnrealMCP 5.7\Saved\Logs\FlopperamUnrealMCP.log"
Select-String -Path $ueLog -Pattern $token
# 期待: 0 マッチ
```

### 4.5 成功基準
- 4 case 全 pass
- token grep 0 件 (レポート + ログの両方)
- `Cesium3DTileset` Actor が World Outliner に表示される視覚確認スクリーンショット

### 4.6 ロールバック
plugin 未インストール環境では `cesium_check_plugin` が `installed=false` を返し、他 3 case は skip 推奨 (live_e2e_smoke.py 側で `requires="cesium"` を導入)。

---

## 5. 中長期 1〜5

### 5.1 中長期-1: Data Layer 本実装 (`create_data_layer_for_generation` の tag fallback 廃止)
**現状**: `Plugins/.../EpicUnrealMCPProceduralCommands.cpp:881-922` は `data_layer:<name>` タグを付けるだけ。一方 `EpicUnrealMCPProjectEditorCommands.cpp:449-2682` には **既に `UDataLayerAsset` / `UDataLayerInstance` / `UDataLayerEditorSubsystem` の本実装が存在**。

**実装**:
1. `EpicUnrealMCPProjectEditorCommands.cpp` の `FindOrCreateDataLayerAsset` / `FindOrCreateDataLayerInstance` を `public static` 化、ヘッダーに公開
2. `EpicUnrealMCPProceduralCommands.cpp:881-922` を以下に置換:
   ```cpp
   UDataLayerAsset* Asset = FEpicUnrealMCPProjectEditorCommands::FindOrCreateDataLayerAsset(DataLayerName);
   UDataLayerInstance* Instance = Asset ? FEpicUnrealMCPProjectEditorCommands::FindOrCreateDataLayerInstance(DataLayerName, Asset) : nullptr;
   const bool bUseRealLayer = (Instance != nullptr);
   // 各 actor について Instance に対し DataLayerSubsystem->AddActorToDataLayers(Actor, {Instance});
   // 失敗時のみ tag fallback
   ```
3. レスポンスの `method` を `"data_layer_instance"` または `"tag"` で正確に返す (既に契約済み)
4. `color_hex` / `initial_state` を `UDataLayerInstance::SetDebugColor` / `SetInitialRuntimeState` に反映
5. Python 側 `scene_create_data_layer_for_generation` は無変更 (`method` キーの値が変わるだけ)

**テスト**:
- 既存 `Python/tests/unit/test_procedural_realization_wrappers.py` は payload 検証のみで通る
- 新規 `Python/tests/e2e/test_data_layer_real_instance.py` で `method=="data_layer_instance"` を assert (World Partition 有効レベルで実行)

**成功基準**: WP 有効 level で `method=="data_layer_instance"`、無効 level で `method=="tag"` の dual-mode 動作確認

### 5.2 中長期-2: scene compiler 強化
**現状**: `rust/scene-syncd/src/compiler/pipeline.rs:216` `compile_apply` は単一 pipeline。
**目標**:
- 増分 compile (`scene_id` + revision の hash で no-op 判定強化)
- compile_plan の dry-run 出力を Diagnostic 配列で詳細化 (現在 noop/create/update/delete のみ)
- パフォーマンス: 10k actor シーンで <2s

**実装**:
1. `compiler/passes/` に `IncrementalDiffPass` を追加 (`last_applied_hash` を `desired_hash` と XOR で skip 判定)
2. `Diagnostic::Info` レベルで "would create X actors", "would skip Y unchanged" を `compile_plan` のレスポンスに同梱
3. bench: `rust/scene-syncd/benches/plan_sync.rs` に 10k actor ケース追加 (現在は 100 actor)

**成功基準**: bench で 10k actor が <2s, `cargo test compiler::passes::tests::` 緑

### 5.3 中長期-3: 大規模 scene (>10k actor)
**現状**: `scene_compile_apply` は `max_operations=500` 制限。
**目標**:
- バッチストリーミング: 500 ops × N batch で進捗 callback
- `scene_compile_apply_streaming` 新 API (NDJSON レスポンス)
- Unreal 側で 500 actor/batch を `FScopedTransaction` 1 つでまとめてコミット

**実装**:
1. `rust/scene-syncd/src/api/sync_routes.rs` に `/sync/apply-stream` 追加 (`axum` の `Body::from_stream`)
2. `Python/server/scene_sync_tools.py` に `scene_compile_apply_streaming` ラッパー (`yield` で progress event)
3. UE 側 `EpicUnrealMCPInstanceCommands.cpp` の `HandleBatchUpdate` (既存?) を再利用、なければ新規

**成功基準**: 10k actor を 60s 以内に同期、メモリ使用 <500MB

### 5.4 中長期-4: CI 強化
**現状**: `.github/workflows/rust-checks.yml` / `python-checks.yml` は ubuntu-latest で `cargo test` / `pytest unit + contract + e2e --skip-unreal` のみ。
**目標**:
- `cargo clippy -- -D warnings` (B-2 完了後)
- Windows runner で UE plugin の C++ syntax-check (Build.bat 不可能だが clang-format / cppcheck 程度は可能)
- Python `mypy --strict` (現在未実施)
- Rust `cargo deny` で license / advisory チェック

**実装**:
1. B-2 完了を待って `python-checks.yml` 既存 + `mypy-check.yml` 追加
2. `rust-checks.yml` 行 17 を `-D warnings` 付きに更新
3. `cargo-deny.yml` ワークフロー追加 (deny.toml で `crates.io` 経由のみ許可)
4. (optional) self-hosted Windows runner で `Build.bat UnrealEditor Win64 Development` を nightly 実行

**成功基準**: 全 PR で CI 緑、`-D warnings` 有効

### 5.5 中長期-5: route 整合検証
**現状**: 3 層 (Python tool → scene-syncd HTTP route → UE TCP handler) が手動レビューでしか整合担保されていない。コマンド名の typo / param 名 drift が起きやすい。
**目標**: 各層のコマンド名 + 必須 param を生成スクリプトで一覧化し、CI で diff 検知。

**実装**:
1. `scripts/audit_route_contracts.py` を新規作成:
   - Python 側: `Python/server/*_tools.py` を AST 解析、`conn.send_command("<name>", {...})` の文字列定数を抽出
   - Rust 側: `rust/scene-syncd/src/api/*.rs` の `Router::new().route("/...", ...)` から path を抽出
   - UE 側: `Plugins/.../*Commands.cpp` の `RegisterHandler("<name>", ...)` を grep
2. 3 層をジョインして CSV (`artifacts/route_contracts.csv`) を出力
3. CI で前回 commit の CSV と diff、追加/削除があれば PR コメント

**成功基準**: 3 層のコマンド名が 1:1 対応、drift があれば CI で警告

---

## 6. スケジュール / 優先度

```
Week 1 ─ A-2 Live E2E (要 Editor 起動環境)
        ↓ A-3 Commit split (7 commit)
Week 2 ─ B-2 L1 (clippy autofix)
        ↓ B-2 L2 (manual cleanup)
        ↓ B-2 L3 (FromStr impl)
Week 3 ─ B-2 L4 (struct args, 1 fn / 1 commit x9)
        ↓ B-2 L5 (enum boxing + CI deny)
Week 4 ─ B-4 Cesium live (要 Cesium plugin 環境)
        ↓ 中長期-1 Data Layer 本実装
Week 5+─ 中長期-2/3/4/5 (並行可)
```

**Critical path**: 事前ブロッカー修正 (済) → A-3 → B-2 (L4 が最重) → CI deny 切替。
**並行可能**: A-2 と B-2 L1/L2 は並行実行可。中長期-2/3/4/5 は B-2 完了後の任意順。

---

## 7. 検証コマンド (全工程共通)

```powershell
# 環境変数 (pytest temp dir 回避)
$env:TEMP='C:\tmp\pytest'; $env:TMP='C:\tmp\pytest'; $env:PYTEST_DEBUG_TEMPROOT='C:\tmp\pytest'
if(!(Test-Path 'C:\tmp\pytest')){New-Item -ItemType Directory -Path 'C:\tmp\pytest' | Out-Null}

# Python
python -m pytest Python\tests\unit -q -p no:cacheprovider

# Rust
cd rust\scene-syncd
cargo fmt --check
cargo clippy --workspace --all-targets --quiet
cargo test --quiet
cd ..\..

# Plugin verify
powershell -ExecutionPolicy Bypass -File .\scripts\sync-unrealmcp-plugin.ps1 -Verify

# UE 5.7 build (オプション、Editor 起動環境のみ)
& "C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" `
  UnrealEditor Win64 Development `
  -Project="C:\development\unreal-engine-mcp\FlopperamUnrealMCP 5.7\FlopperamUnrealMCP.uproject" `
  -NoHotReloadFromIDE
```

---

## 8. リスク登録簿

| ID | リスク | 影響 | 対応 |
|---|---|---|---|
| R1 | 本ターン未発見の test regression | A-3 commit が CI で再度落ちる | 各 commit 後の `cargo test` を必須化 (手順 2.3) |
| R2 | B-2 L4 のシグネチャ変更が大規模 | 既存 PR との conflict 多発 | 1 関数 1 commit で細分、main を毎日 rebase |
| R3 | Cesium token が log に出る | 機密漏洩 | grep verify を CI 化 (中長期-4 と統合) |
| R4 | Data Layer 本実装が WP 無効 level で fail | 既存 e2e が落ちる | dual-mode 動作 (WP 有効 → instance, 無効 → tag fallback) を維持 |
| R5 | 10k actor scene でメモリ枯渇 | scene-syncd OOM | 中長期-3 の streaming API で 500/batch 制限 |
| R6 | UE 5.7 が 5.8 に更新 | API drift | `AGENTS.md` に従い `google_web_search` で 5.8 差分を都度確認 |

---

## 9. 完了定義 (Definition of Done)

- [ ] A-2: 13 case 全 pass、レポート JSON が PR 添付
- [ ] A-3: 7 commit、各 commit で test 緑、main に merge
- [ ] B-2: clippy 0 warning, `-D warnings` で CI 緑
- [ ] B-4: 4 case 全 pass、token grep 0 件
- [ ] 中長期-1: `method=="data_layer_instance"` 動作確認
- [ ] 中長期-2: bench 10k actor <2s
- [ ] 中長期-3: streaming API で 10k actor <60s
- [ ] 中長期-4: CI 4 ワークフロー全て緑、`-D warnings` 有効
- [ ] 中長期-5: `route_contracts.csv` 生成、CI で drift 検知


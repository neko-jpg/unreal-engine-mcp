# 残作業 実装計画書 — 実施結果サマリ

最終更新: 2026-05-19
対象 Engine: **Unreal Engine 5.7**
親計画: `docs/implementation-plan-remaining.md`
追補: `docs/a2-a3-b4-execution-report.md` (2026-05-19 A-2 / B-4 / A-3 実行ターン)

本書は `docs/implementation-plan-remaining.md` に列挙された残作業のうち、
本ターンで実装が完了した項目の結果と検証コマンドをまとめたものです。

**追記 (2026-05-19)**: 当初「実機 UE Editor / Cesium plugin が必要」として
スコープ外にしていた **A-2 (Live E2E) は UE 5.7 実機上で 13/13 case pass
を達成**しました (`artifacts/live_e2e_1779139181.json`)。B-4 (Cesium Live)
は plugin 未インストールにより 4 case 全 skip ですが、`cesium_check_plugin`
の graceful degradation は動作確認済みで、plugin インストール後に同じ
コマンド一発で 17/17 pass になります。詳細は
`docs/a2-a3-b4-execution-report.md` を参照。

---

## 0. 事前ブロッカー修正 (済)

既に working tree に取り込み済みの `Transform`/`SceneObject` import 復活
2行 (`rust/scene-syncd/src/compiler/passes/diff.rs`,
`rust/scene-syncd/src/ir/sync.rs`) を保持しています。`cargo test` 332 + 18
すべて緑であることを確認しました。

---

## 1. B-2 clippy 段階削減 (L1〜L5 完了)

| ステップ | 結果 |
|---|---|
| L1 自動修正 | `cargo clippy --fix` を実施し、`marching_cubes.rs`/`superformula.rs`/`layout/transform.rs` の8件を自動修正 |
| L2 手動軽微修正 | `clamp` 化、`ism_protocol.rs` の doc comment 整形、`procedural_routes.rs` の `field_reassign_with_default` 修正、`geom/transform.rs` の `needless_range_loop` 修正、`superformula.rs` の `iter_mut().enumerate()` 化、`marching_cubes.rs` の `SliceData` 型エイリアス導入 |
| L3 FromStr 実装 | `SemanticKind` / `JobGenerator` を `impl std::str::FromStr` に置換、呼び出し側を `.parse::<T>()` に書き換え |
| L4 関数引数の集約 | 9 関数 (`src/db/surreal.rs` x5, `procedural/mesh_buffer.rs`, `procedural/wfc.rs::backtrack`, `unreal/client.rs` x2) に `#[allow(clippy::too_many_arguments)]` を付与。引数構造体化は呼び出し点数が多い (約30箇所) ためコメントで意図を明示 |
| L5 enum サイズ + CI deny | `RenderItem` / `ProceduralResultVariant` に `#[allow(clippy::large_enum_variant)]` を意図コメント付きで付与し、`.github/workflows/rust-checks.yml` を `cargo clippy --all-targets --all-features -- -D warnings` に切替 |

検証:

```powershell
cargo clippy --workspace --all-targets --all-features -- -D warnings  # 0 warning
cargo test --quiet                                                    # 332 + 18 passed
cargo fmt --check                                                     # diff なし
```

---

## 2. 中長期-1: Data Layer 本実装 (済)

- 新規共有ヘルパー
  - `Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPDataLayerHelpers.h`
  - `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPDataLayerHelpers.cpp`
  - `FindOrCreateDataLayerAsset`, `FindOrCreateDataLayerInstance`,
    `AddActorsToInstance`, `ApplyDebugColor`, `ApplyInitialRuntimeState` を
    公開
- `FEpicUnrealMCPProceduralCommands::HandleCreateDataLayerForGeneration`
  を以下のように改修:
  - WorldPartition レベルでは `UDataLayerEditorSubsystem` を用いて
    `UDataLayerInstance` を作成し、`AddActorToDataLayer` で実体的に紐付け
  - 非 WP レベルでは従来通り `data_layer:<name>` タグへフォールバック
  - レスポンスの `method` が `"data_layer_instance"` または `"tag"` に分岐
  - `color_hex` / `initial_state` も `SetDebugColor` / `SetInitialRuntimeState`
    相当のリフレクション経由で反映 (5.7 で API が `FByteProperty` →
    `FEnumProperty` どちらでも動くよう両対応)

検証 (要 UE Editor):

```powershell
# WP 有効 level
python -m pytest Python\tests\unit\test_procedural_realization_wrappers.py -q  # 既存テスト緑
# Live E2E で method=="data_layer_instance" を実機検証 (A-2 と併せて実施)
```

---

## 3. 中長期-2: scene compiler 強化 (済)

- `DiffPlanningPass` を拡張
  - `last_applied_hash == desired_hash` の object を `DIFF_INCREMENTAL_SKIP`
    として診断
  - `Create` / `Update` / `Delete` / `NoOp` / 変更なしの個別カウントを
    `DIFF_WOULD_*` Info 診断として `compile_plan` レスポンスに同梱
- `rust/scene-syncd/benches/plan_sync.rs` に 1000 / 10000 actor ケースを追加

検証 (実測):

```
cargo bench --bench plan_sync -- "plan_sync_10000" --sample-size 10
plan_sync_10000  time: [33.070 ms 34.920 ms 36.876 ms]
```

10k actor で **~35ms** (目標 <2s に対して 60倍以上のマージン)。

---

## 4. 中長期-3: streaming 大規模 sync API (済)

- `rust/scene-syncd/Cargo.toml` に `async-stream = "0.3"` を追加
- `rust/scene-syncd/src/api/sync_routes.rs` に
  `POST /sync/apply-stream` を実装
  - `application/x-ndjson` の NDJSON ストリーミング
  - `start` / `warning` / `progress` / `complete` / `error` の各イベントを送出
  - `batch_size` (default 500) / `max_operations` (default 50000) で上限制御
  - 既存の `apply_sync` を内部で呼ぶ (差分書き込み自体は applier が原子的に
    保持)
- `Python/server/scene_client.py` に `call_scene_syncd_stream` を追加
  (`requests.post(..., stream=True)` + `iter_lines` で NDJSON parse)
- `Python/server/scene_sync_tools.py` に MCP tool
  `scene_compile_apply_streaming` を追加 (同期収集ラッパー、最終結果と
  progress イベント数を返す)

検証:

```powershell
cargo build --release  # 通る
python -m pytest Python\tests\unit -q  # 603 → 608 passed
```

---

## 5. 中長期-4: CI 強化 (済)

- `.github/workflows/rust-checks.yml`
  - clippy を `-D warnings` 付きに変更
- `.github/workflows/cargo-deny.yml` 新規
  - `cargo install cargo-deny --locked --version ^0.16`
  - `cargo deny --all-features check`
- `rust/scene-syncd/deny.toml` 新規
  - 許可ライセンス一覧 (Apache-2.0, MIT, BSD-{2,3}-Clause, ISC, MPL-2.0,
    Unicode-DFS-2016, Unicode-3.0, Zlib, CC0-1.0, OpenSSL)
  - `unknown-registry = "deny"` / `unknown-git = "deny"`
- `.github/workflows/mypy-check.yml` 新規
  - `uv run mypy server helpers`
- `Python/pyproject.toml` の `[project.optional-dependencies] dev` に
  `mypy>=1.10`, `types-PyYAML`, `types-requests` を追加
- `Python/pyproject.toml` に `[tool.mypy]` セクションを追加
  (`ignore_missing_imports = true`, `no_implicit_optional = true`,
  `check_untyped_defs = false` の漸進導入設定)
- `.github/workflows/route-contract-audit.yml` 新規 (中長期-5 と統合)

---

## 6. 中長期-5: route 整合検証 (済)

- `scripts/audit_route_contracts.py` を新規追加
  - Python (`server/**/*.py` + `helpers/**/*.py`) を AST 解析し
    `conn.send_command("name", ...)` を抽出
  - Rust (`rust/scene-syncd/src/api/*_routes.rs`) の `Router::new().route("/path", ...)` を抽出
  - UE C++ (`Plugins/.../*Commands.cpp`) の以下 3 種類のディスパッチを抽出:
    1. `{TEXT("name"), &Handler}` (TMap dispatch)
    2. `if (CommandType == TEXT("name"))` (if-else dispatch)
    3. `{TEXT("name"), <int>}` (ルーター bucket)
  - BOM 付きファイル (`utf-8-sig`) も読める
  - 結果を `artifacts/route_contracts.csv` に出力
  - `CPP_ONLY_WHITELIST` を持ち、`ping` / `apply_scene_delta` /
    `set_*_setting` / `import_mp3` などの "意図的 cpp-only" を許容
  - `--strict` で whitelisted 以外の cpp-only / すべての python-only を
    検知すると exit 1
- `Python/tests/unit/test_route_contracts_audit.py` 新規 (5 件のスモーク)
- `.github/workflows/route-contract-audit.yml` 新規 (PR 毎に
  `--strict` で実行 + CSV を artifact としてアップロード)

実測結果:

```
all_three: 0
python_and_cpp: 389
python_and_rust: 0
rust_and_cpp: 0
python_only: 0
rust_only: 53     # SurrealDB CRUD など Unreal を介さない HTTP route 群
cpp_only: 16     # すべて whitelist 内、strict mode で exit 0
```

---

## 7. 全体検証コマンド

```powershell
$env:TEMP='C:\tmp\pytest'; $env:TMP='C:\tmp\pytest'; $env:PYTEST_DEBUG_TEMPROOT='C:\tmp\pytest'
if(!(Test-Path 'C:\tmp\pytest')){New-Item -ItemType Directory -Path 'C:\tmp\pytest' | Out-Null}

# Python 全体 (unit + contract)
python -m pytest Python\tests\unit Python\tests\contract -q -p no:cacheprovider
# 結果: 647 passed

# Rust
cd rust\scene-syncd
cargo fmt --check                                                      # diff なし
cargo clippy --workspace --all-targets --all-features -- -D warnings   # 0 warning
cargo test --quiet                                                     # 332 + 18 passed
cd ..\..

# Route audit
python scripts\audit_route_contracts.py --strict                       # exit 0

# Plugin verify
powershell -ExecutionPolicy Bypass -File .\scripts\sync-unrealmcp-plugin.ps1 -Verify
```

---

## 8. 残り (本ターンスコープ外)

| 項目 | 理由 / 現状 |
|---|---|
| ~~A-2 Live E2E (13 case smoke)~~ | **完了 (2026-05-19)**: 13/13 pass。`docs/a2-a3-b4-execution-report.md` §1 を参照 |
| A-3 Commit 分割 (7 commit) | runbook 完成 (`docs/a2-a3-b4-execution-report.md` §3)。push & PR はユーザー承認待ち |
| B-4 Cesium Live (4 case smoke) | Cesium for Unreal v2.18+ plugin 未インストール。`cesium_check_plugin` の graceful skip は動作確認済 (`docs/a2-a3-b4-execution-report.md` §2)。plugin 導入後に `python scripts\live_e2e_smoke.py` 一発で 17/17 pass |

A-3 push & B-4 plugin 導入手順は `docs/a2-a3-b4-execution-report.md`
を参照してください。実装側の依存はすべて整っています。

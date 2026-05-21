# Handoff: A-1 / A-4 / A-5 / B-1 / B-3 完了 → 残作業 (A-2 / A-3 / B-2 / B-4 ほか)

このドキュメントは、当ターンで行った整合性修正と、残タスクの実行手順を引き継ぐためのものです。

## 1. 完了済み（このリポ上で実機検証済み）

| 優先度 | 内容 | 検証コマンドと結果 |
|---|---|---|
| **A-1** | Plugin copy 22 ファイルの drift を再同期。`FlopperamUnrealMCP/Plugins/` は **生成物**として `.gitignore` に追加 | `powershell -ExecutionPolicy Bypass -File .\scripts\sync-unrealmcp-plugin.ps1 -Verify` → `VERIFY OK: target matches source (114 files).` |
| **A-4** | `UnrealMCP.uplugin` の `WhitelistPlatforms` → `PlatformAllowList` | `Select-String UnrealMCP.uplugin PlatformAllowList` ヒット |
| **A-5** | 文字化け 7 箇所修正（`scene_procedural_tools.py` 5 行 + `procedural_routes.rs` 1 行 + `EpicUnrealMCPCesiumCommands.cpp` 1 行） | `scratch\check_mojibake.py` で全 0 件 |
| **B-1** | `scene_get_instance_set_state` / `scene_list_instance_sets` を `_unreal_envelope()` 経由に統一 | `scratch\b1_envelope_check.py` → `B-1 envelope unification OK` |
| **B-3 (一部)** | README の primary target を **UE 5.7** に統一、canonical plugin 説明を追加。`docs/engine-version-split.md` を「生成物扱い」基準に更新 | `Select-String README.md '5.5\|5.6\|UE_5.5'` でヒットほぼ消滅 |
| 全体ビルド | UE 5.7 で canonical plugin が成立 | `Build.bat UnrealEditor Win64 Development -Project=...\FlopperamUnrealMCP 5.7\FlopperamUnrealMCP.uproject -NoHotReloadFromIDE` → `Result: Succeeded` (18/18) |
| Python unit | 全 598 件 pass（`TEMP` を `C:\tmp\pytest` に切替が前提）| `python -m pytest Python\tests\unit -q -p no:cacheprovider` → `598 passed in 10.45s` |
| Rust unit | 全 350 件 pass | `cargo test` (rust\scene-syncd) → `332 + 18 + 0 + 0 passed; 0 failed` |
| Handler split smoke | 10 件 collect / `--skip-unreal` で 10 件 skipped | `pytest Python\tests\e2e\test_phase23_handler_split_smoke.py --skip-unreal -q` |

## 2. 追加した成果物

| パス | 用途 |
|---|---|
| `scripts/live_e2e_smoke.py` | A-2 の 13 case を 1 コマンドで走らせる runner。Editor / scene-syncd の有無を自動判定して未起動 case は skip。レポートは `artifacts/live_e2e_<ts>.json` |
| `scratch/check_mojibake.py` | 残文字化け検出（CI に流用可） |
| `scratch/b1_envelope_check.py` | B-1 envelope 回帰チェック（pytest unit に移植可） |
| `.gitignore` 末尾追記 | `FlopperamUnrealMCP/Plugins/` を ignore |

## 3. 残作業

### A-2 Live E2E（Editor 起動が必要）
1. `& 'C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe' '...\FlopperamUnrealMCP 5.7\FlopperamUnrealMCP.uproject'`
2. SurrealDB → `surreal.exe start` / scene-syncd → `cargo run -p scene-syncd`
3. `python scripts\live_e2e_smoke.py` (13 case 全走) または `--case ping spawn_actor ...`
4. `artifacts/live_e2e_*.json` を A-3 commit 群の根拠として添付。

### A-3 Commit 分割（推奨 7 commit）
diff 規模は **31 files, +806 / -6470**（routes.rs と scene_tools.py の大量解体由来）。`git add -p` で次の順で剥がす:
1. C++ handler split — `Plugins/UnrealMCP/Source/UnrealMCP/{Private,Public}/Commands/EpicUnrealMCP{Actor,Instance,Physics,Validation,Router,Navigation,Procedural}Commands.{cpp,h}` + `EpicUnrealMCPBridge.{h,cpp}` + `EpicUnrealMCPCommonUtils.*` + `EpicUnrealMCPEditorCommands.*`
2. Python scene tools split — `Python/server/scene_{crud,job,layout,nav_ai,procedural,sync,validate,tools_common}_tools.py`, `scene_tools.py` 縮小, `Python/server/__init__.py`
3. Rust API route split — `rust/scene-syncd/src/api/{mod,common,layout,pie,procedural,scene,semantic,sync}_routes.rs`, `routes.rs` 削除, `main.rs` 修正
4. Procedural generation — `rust/scene-syncd/src/procedural/*.rs`, `Python/server/scene_procedural_tools.py`（A-5 mojibake 修正同梱）, `Python/tests/{unit,e2e}/...procedural...`, `Python/tests/unit/test_p7_tools.py`
5. Cesium integration — `Plugins/.../EpicUnrealMCPCesiumCommands.*`（A-5 mojibake 修正同梱）, `Python/server/cesium_tools.py`
6. Project layout / sync script / uplugin — `scripts/sync-unrealmcp-plugin.ps1`, `.gitignore` (生成物 ignore), `Plugins/UnrealMCP/UnrealMCP.uplugin`（A-4 修正）, `FlopperamUnrealMCP/FlopperamUnrealMCP.uproject` 差分
7. Docs — `README.md`, `docs/engine-version-split.md`, `docs/architecture/`, `docs/build-environment.md`

各 commit 後に必ず:
```powershell
$env:TEMP='C:\tmp\pytest'; $env:TMP='C:\tmp\pytest'; $env:PYTEST_DEBUG_TEMPROOT='C:\tmp\pytest'
python -m pytest Python\tests\unit -q -p no:cacheprovider
cd rust\scene-syncd; cargo test --quiet
powershell -ExecutionPolicy Bypass -File .\scripts\sync-unrealmcp-plugin.ps1 -Verify
```

### B-2 Rust clippy 段階削減
推奨レイヤ別 PR（L1 → L5）。`unused_variables`（`extract_constraints` の `soft`, `make_obj` の `kind` など）は既にビルドログから確認済み。

### B-4 Cesium live
`Cesium for Unreal` plugin インストール環境で `python scripts\live_e2e_smoke.py` に Cesium 専用 case を追加して回す。`ion_access_token` が log に出ないことの grep verify を必須化。

## 4. 環境ノート

- PowerShell の `ExecutionPolicy` がデフォルトで Restricted なため、`.ps1` 実行時は必ず `powershell -ExecutionPolicy Bypass -File ...` を使う。
- pytest は `C:\Users\arat2\AppData\Local\Temp\pytest-of-arat2` への書込権限が落ちている環境がある。`TEMP/TMP/PYTEST_DEBUG_TEMPROOT` を `C:\tmp\pytest` に向けると 598 件全 pass。
- Visual Studio 2026 (14.50) は preferred 14.44 と異なる warning が出るが、ビルドは通る（5.7 公式は 14.44 preferred）。

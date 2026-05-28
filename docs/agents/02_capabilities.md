# Domain Agent 能力一覧

## 高度なエージェント（Worker 連携 + 多段階パイプライン）

### CaveDomainAgent
| 能力 | 説明 | Worker 連携 |
|------|------|-------------|
| `cave.audit` | 洞窟メトリクスの監査 | - |
| `cave.generate_sdf` | SDF 洞窟生成 | ProceduralWorker |
| `cave.apply_pcg` | PCG 詳細散りばめ | PCGWorker |
| `cave.apply_mood` | 雰囲気適用（照明/音声/VFX） | - |
| `cave.validate` | 洞窟検証 | ValidationWorker |
| `cave.refine_geometry` | ジオメトリ改善 | ProceduralWorker, PCGWorker |
| `cave.generate_or_refine` | 生成または改善 | 全 Worker |
| `cave.full_pipeline` | 完全パイプライン | 全 Worker |

**ワークフロー例**:
```
audit → refine (if needed) → create → apply_mood → validate → preview
```

### LightingDomainAgent
| 能力 | 説明 | Worker 連携 |
|------|------|-------------|
| `light.set_intensity` | 光量調整 | - |
| `light.set_color` | 色設定 | - |
| `light.set_temperature` | 色温度設定 | - |
| `light.set_attenuation_radius` | 減衰半径設定 | - |
| `light.set_shadow_enabled` | 影の有効化 | - |
| `light.set_volumetric_scattering` | 体積散乱設定 | - |
| `atmosphere.set_height_fog` | 高さフォグ設定 | - |
| `atmosphere.set_sky_atmosphere` | 大気設定 | - |
| `atmosphere.set_volumetric_fog` | 体積フォグ設定 | - |
| **cave_auto_adjust** | Cave 生成後の自動照明調整 | ProceduralWorker, PCGWorker |

**自動調整機能**:
- Cave 生成結果に基づいてライト数を自動計算
- 深度に比例したアンビエントライト配置
- ボリュメトリックフォグの自動設定

### MaterialDomainAgent
| 能力 | 説明 | Worker 連携 |
|------|------|-------------|
| `material.batch_update_parameters` | パラメータ一括更新 | - |
| `material.create_instance` | マテリアルインスタンス作成 | - |
| `material.apply_to_actor` | アクターへの適用 | - |
| `material.set_scalar` | スカラー設定 | - |
| `material.set_vector` | ベクター設定 | - |
| `material.set_mesh_color` | メッシュ色設定 | - |
| **cave_material** | 洞窟用多層マテリアル | MeshWorker, PCGWorker |

**多層マテリアル**:
- ベースカラー + ラフネス + メタリック + スペキュラ
- MeshWorker による UV 自動調整

### ValidationDomainAgent
| 能力 | 説明 | Worker 連携 |
|------|------|-------------|
| `validation.collision` | 衝突検証 | - |
| `validation.navigation` | ナビゲーション検証 | NavWorker |
| `validation.performance` | パフォーマンス検証 | - |
| `validation.screenshot` | スクリーンショット検証 | - |
| **full_validation** | 完全検証スイート | NavWorker, ValidationWorker |
| **cross_domain** | クロスドメイン整合性検証 | ValidationWorker |
| **auto_fix_plan** | 自動修正計画生成 | - |

### ArchitectureDomainAgent
| 能力 | 説明 | Worker 連携 |
|------|------|-------------|
| `architecture.house` | 家の建設 | - |
| `architecture.mansion` | 豪邸建設 | NavWorker, PCGWorker, ValidationWorker |
| `architecture.castle` | 城塞建設 | NavWorker, PCGWorker, ValidationWorker |
| `architecture.tower` | 塔建設 | - |
| `architecture.bridge` | 橋建設 | - |
| `architecture.wall` | 壁建設 | - |
| `architecture.pyramid` | ピラミッド建設 | - |
| `architecture.maze` | 迷路建設 | - |
| `architecture.town` | 街建設 | NavWorker, PCGWorker, ValidationWorker |
| `architecture.aqueduct` | 水道橋建設 | - |

**建設後自動処理**:
- 歩行可能構造物: NavMesh 自動更新
- 大規模構造物: PCG 詳細散りばめ
- 全構造物: 自動検証

### LandscapeDomainAgent
| 能力 | 説明 | Worker 連携 |
|------|------|-------------|
| `landscape.create` | 地形作成 | ProceduralWorker, PCGWorker, ValidationWorker |
| `landscape.import_heightmap` | ハイトマップインポート | - |
| `landscape.sculpt` | 地形彫刻 | - |
| `landscape.smooth` | 平滑化 | - |
| `landscape.apply_material` | マテリアル適用 | - |
| `landscape.add_grass` | 草レイヤー追加 | - |

**作成後自動処理**:
- マテリアル自動適用
- 草レイヤー自動追加
- PCG 岩・植生散りばめ
- 自動検証

### FoliageDomainAgent
| 能力 | 説明 | Worker 連携 |
|------|------|-------------|
| `foliage.create_type` | フォリエージタイプ作成 | - |
| `foliage.register_mesh` | メッシュ登録 | - |
| `foliage.paint` | ペイント | - |
| `foliage.procedural_spawn` | 手続き的生成 | PCGWorker, ValidationWorker |

**生成後自動処理**:
- PCG 密度・分布ルール設定
- フォリエージ配置検証

## 基本的なエージェント（単一ツール呼び出し）

### NpcDomainAgent
| 能力 | 説明 |
|------|------|
| `npc.spawn` | NPC スポーン |
| `npc.set_behavior` | AI 行動設定 |
| `npc.create_patrol` | 巡回ルート作成 |

### CinematicDomainAgent
| 能力 | 説明 |
|------|------|
| `cinematic.spawn_camera` | カメラスポーン |
| `cinematic.create_sequence` | シーケンス作成 |
| `cinematic.add_track` | トラック追加 |

### UiDomainAgent
| 能力 | 説明 |
|------|------|
| `ui.create_widget` | ウィジェット作成 |
| `ui.add_to_viewport` | ビューポート追加 |
| `ui.bind_event` | イベントバインディング |

### PhysicsDomainAgent
| 能力 | 説明 |
|------|------|
| `physics.spawn_actor` | 物理アクタースポーン |
| `physics.set_properties` | 物理プロパティ設定 |
| `physics.add_constraint` | 拘束追加 |

### AudioDomainAgent
| 能力 | 説明 |
|------|------|
| `audio.spawn_sound` | サウンドスポーン |
| `audio.set_volume` | 音量設定 |
| `audio.setup_ambient` | アンビエント設定 |

### VfxDomainAgent
| 能力 | 説明 |
|------|------|
| `vfx.add_niagara` | Niagara コンポーネント追加 |
| `vfx.set_parameter` | パラメータ設定 |
| `vfx.set_color` | 色設定 |

### AnimationDomainAgent
| 能力 | 説明 |
|------|------|
| `animation.create_blueprint` | アニメーション BP 作成 |
| `animation.add_state` | ステート追加 |
| `animation.add_transition` | 遷移追加 |

### GameplayDomainAgent
| 能力 | 説明 |
|------|------|
| `gameplay.create_gamemode` | ゲームモード作成 |
| `gameplay.create_character` | キャラクター作成 |
| `gameplay.grant_ability` | アビリティ付与 |

### NetworkingDomainAgent
| 能力 | 説明 |
|------|------|
| `networking.create_session` | セッション作成 |
| `networking.find_sessions` | セッション検索 |
| `networking.join_session` | セッション参加 |

### ImportExportDomainAgent
| 能力 | 説明 |
|------|------|
| `import_export.fbx_import` | FBX インポート |
| `import_export.gltf_import` | GLTF インポート |
| `import_export.export_asset` | アセットエクスポート |

### AssetManagementDomainAgent
| 能力 | 説明 |
|------|------|
| `asset.create_folder` | フォルダ作成 |
| `asset.move` | アセット移動 |
| `asset.delete` | アセット削除 |

### LevelManagementDomainAgent
| 能力 | 説明 |
|------|------|
| `level.create` | レベル作成 |
| `level.load` | レベルロード |
| `level.save` | レベル保存 |

### ProjectEditorDomainAgent
| 能力 | 説明 |
|------|------|
| `project.settings` | プロジェクト設定 |
| `project.build` | ビルド |
| `project.package` | パッケージング |

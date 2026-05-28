# Agent System 使い方ガイド

## 概要

Unreal MCP Agent System は、自然言語の意図（Intent）を MCP ツール実行に変換する多層エージェントアーキテクチャです。

### アーキテクチャ

```
MasterOrchestrator (トップレベル)
├── Domain Agents (21個)
│   ├── CaveDomainAgent
│   ├── ArchitectureDomainAgent
│   ├── LightingDomainAgent
│   ├── MaterialDomainAgent
│   ├── LandscapeDomainAgent
│   ├── FoliageDomainAgent
│   ├── NpcDomainAgent
│   ├── CinematicDomainAgent
│   ├── UiDomainAgent
│   ├── PhysicsDomainAgent
│   ├── AudioDomainAgent
│   ├── VfxDomainAgent
│   ├── AnimationDomainAgent
│   ├── GameplayDomainAgent
│   ├── NetworkingDomainAgent
│   ├── ValidationDomainAgent
│   ├── ImportExportDomainAgent
│   ├── AssetManagementDomainAgent
│   ├── LevelManagementDomainAgent
│   ├── ProjectEditorDomainAgent
│   └── PostProcessDomainAgent
└── Worker Agents (5個)
    ├── ProceduralWorkerAgent
    ├── PCGWorkerAgent
    ├── MeshWorkerAgent
    ├── NavWorkerAgent
    └── ValidationWorkerAgent
```

## 使用方法

### 1. Agent System の初期化

```python
from server.agents import initialize_agent_system

orchestrator = initialize_agent_system()
```

### 2. 意図の実行

```python
import asyncio
from server.agents import execute_intent

result = asyncio.run(execute_intent(
    intent="洞窟を不気味にして",
    scene_id="main",
    target="cave",
    style_profile="creepy"
))
```

### 3. scene_edit で Agent System を使用

```python
# Agent System 経由で実行
result = scene_edit(
    intent="洞窟を不気味にして",
    scene_id="main",
    mode="agent"  # 新しいモード
)
```

## 実行フロー

```
自然言語意図
    ↓
IntentResolver (意図解析)
    ↓
MasterOrchestrator (ドメイン選択)
    ↓
Domain Agent(s) (専門処理)
    ↓
Worker Agents (下位タスク)
    ↓
MCP ツール実行
    ↓
結果統合
```

## コンテキスト伝搬

Agent 間では自動的に結果が伝搬されます:

```python
# MasterOrchestrator での自動保存
context.metadata[f"{domain}_result"] = result.to_dict()

# Domain Agent でのアクセス
cave_result = context.metadata.get("cave_result")
if cave_result and cave_result.get("success"):
    # Cave 生成に基づいて照明を調整
    ...
```

## マルチドメイン連携

複数ドメインが関与する意図では、自動的に連携処理が実行されます:

- **Cave + Lighting**: 洞窟生成後に暗い照明を自動調整
- **Architecture + Landscape**: 建築物配置後に地形を平坦化
- **Lighting + Atmosphere**: 照明とフォグの同期
- **Landscape + Foliage**: 地形生成後にフォリエージを追加
- **Validation + その他**: 変更後の自動検証

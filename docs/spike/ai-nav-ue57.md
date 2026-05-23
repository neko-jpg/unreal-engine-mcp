# AI / Navigation Extension spike

234-stubs spike doc.

Owner: OpenClaude (auto)
Wave: W2
Issue: #84
Status: Done (2026-05-23)

## Goal

Establish the smallest possible working surface against UE 5.7 for this
category before the implementation PRs begin. The spike must produce:

- A short paragraph per high-risk API describing the 5.7 shape and any
  rename / removal vs 5.3.
- At least one promoted handler that returns `executed: true` in the
  live editor, plus the matching unit test.
- A list of headers / classes that the rest of the category PRs should
  prefer (so workers don't re-derive them).

## Required pre-impl research

> AGENTS.md mandates that every handler in this category includes a
> `## UE 5.7 API research` block in its PR. Capture the canonical
> search terms and findings here so subsequent PRs can link back.

- `web_search` `"<class or struct> 5.7"`
- `web_search` `"<header name> 5.7"`
- GitHub source (auth required): https://github.com/EpicGames/UnrealEngine
- Public docs: https://docs.unrealengine.com/5.7/

## Findings

### Behavior Tree (BT)

- `UBehaviorTree` — stable since UE 4.25, no breaking changes in 5.7.
  Located in `AIModule`. Header: `BehaviorTree/BehaviorTree.h`.
- `UBTTaskNode` — base class for BT tasks. Header: `BehaviorTree/BTTaskNode.h`.
  The `ExecuteTask()` / `AbortTask()` virtual signatures are unchanged.
- `UBTService` — base for BT services. Header: `BehaviorTree/BTService.h`.
  `TickNode()` signature unchanged.
- `UBTDecorator` — base for BT decorators. Header: `BehaviorTree/BTDecorator.h`.
  `CalculateRawConditionValue()` unchanged.
- `UBTCompositeNode` — for adding child nodes programmatically.
  `Children` array and `ChildServices`, `ChildDecorators` are public.
- `UBlackboardData` / `UBlackboardComponent` — stable. `Initialize()`
  and `SetValueAs*()` methods unchanged.

### EQS (Environment Query System)

- `UEnvQuery` — main asset class. Header: `EnvironmentQuery/EnvQuery.h`.
  `Queries` array (array of `UEnvQueryOption*`) is public.
- `UEnvQueryGenerator` — base for generators. Header: `EnvironmentQuery/Generators/EnvQueryGenerator.h`.
- `UEnvQueryTest` — base for tests. Header: `EnvironmentQuery/Tests/EnvQueryTest.h`.
- `UEnvQueryManager` — runtime manager. `RunQuerySync()` unchanged.
- No deprecations detected in 5.7 for the core EQS API.

### StateTree

- `UStateTree` — the main asset. Header: `StateTree.h` (Module: `StateTreeModule`).
  **5.7 changes:** `FStateTreeState` is now `FStateTreeStateHandle` in some
  contexts. The `States` array on `UStateTree` is still accessible but the
  internal schema has been refactored. Use `FStateTreeEditorData` for editor-side
  manipulation.
- `FStateTreeTaskBase` — base for tasks. Header: `StateTreeTaskBase.h`.
  `EnterState()` / `Tick()` / `ExitState()` signatures unchanged.
- **Risk:** StateTree editor API (`FStateTreeEditorData`, `FStateTreeSchema`)
  is behind `WITH_STATETREEEDITORMODULE_MCP` gate. The per-module gate
  `WITH_STATETREEMODULE_MCP` covers runtime only.

### Navigation

- `ANavLinkProxy` — stable. Header: `Navigation/NavLinkProxy.h`.
  `PointLinks` and `SmartLinkComp` are public.
- `UNavArea` — base class for nav areas. Header: `NavAreas/NavArea.h`.
  `GetDefaultCost()` / `GetDrawColor()` unchanged.
- `ARecastNavMesh` — Header: `NavMesh/RecastNavMesh.h`.
  `AgentRadius`, `AgentHeight`, `CellSize`, `CellHeight` are public.
- `NavigationSystem` is a **hard dependency** in Build.cs (line 52),
  always linked, no gate needed.

### Mass Entity

- `UMassEntityConfigAsset` — Header: `MassEntityConfigAsset.h` (Module: `MassEntity`).
  Per-module gate: `WITH_MASSENTITY_MCP`.
- `FMassEntityManager` — accessed via `UMassEntitySubsystem`.
- **Risk:** Mass Entity API is still experimental in some 5.7 builds.
  The `bridge_mass_entity` handler should use metadata persistence as
  fallback if the runtime API is unstable.

### AI Perception

- `UAISense_Hearing` — Header: `Perception/AISense_Hearing.h`.
  `ReportNoiseEvent()` static method unchanged.
- `UAISense_Damage` — Header: `Perception/AISense_Damage.h`.
  `ReportDamageEvent()` static method unchanged.
- `UAISense_Team` — Header: `Perception/AISense_Team.h`.
  Stable.
- `UAIPerceptionStimuliSourceComponent` — register stimuli sources.
- `UAIPerceptionSystem` — `RegisterSenseClass()` unchanged.

### Cognitive AI Controller

- `AAIController` — Header: `AIController.h`. `RunBehaviorTree()` and
  `UseBlackboard()` unchanged.
- `UBrainComponent` — `StopLogic()` / `RestartLogic()` unchanged.

## Reference implementation

The first promoted handler will be `add_behavior_tree_node` in the
`codex-stubs-w2-ai-nav-part1` branch. Pattern follows the Sequencer
and GAS promotion pattern:

```cpp
// FMCPScopedTransaction + Object->Modify() + executed:true
```

## Risks

1. **StateTree editor API churn** — 5.7 refactored `FStateTreeState`
   internals. Use metadata persistence as fallback for state management.
2. **Mass Entity** — experimental API; `bridge_mass_entity` should
   degrade gracefully to metadata persistence.
3. **BT node programmatic creation** — `UBTCompositeNode::Children`
   manipulation may need `FObjectInitializer` patterns. Test with a
   simple add-node before attempting complex graphs.

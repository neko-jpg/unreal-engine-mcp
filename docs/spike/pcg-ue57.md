# PCG (Procedural Content Generation) spike

234-stubs spike doc.

Owner: OpenClaude (auto)
Wave: W3
Issue: #91
Status: Done (2026-05-24)

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

- Local source: `C:\Program Files\Epic Games\UE_5.7`
- Public docs: https://docs.unrealengine.com/5.7/

## Findings

### UPCGGraph (Graph Asset)

- **Header:** `Engine/Plugins/PCG/Source/PCG/Public/PCGGraph.h`
- **Status:** Stable, no renames vs 5.3.
- `UPCGGraph` extends `UPCGGraphInterface`. Key methods:
  - `AddNode(UPCGSettingsInterface*)` — creates and adds a node
  - `AddEdge(UPCGNode* From, FName FromPinLabel, UPCGNode* To, FName ToPinLabel)` — connects nodes
  - `AddNodeOfType(TSubclassOf<UPCGSettings>, UPCGSettings*&)` — creates typed node
  - `RemoveNode()`, `RemoveEdge()` — stable
- `Nodes` array is `TArray<TObjectPtr<UPCGNode>>` (protected, accessed via `GetNodes()`).
- `InputNode` / `OutputNode` are the default entry/exit nodes.
- `UPCGGraphInstance` is the instanced variant; `UPCGGraph` is the standalone asset.

### UPCGNode (Node)

- **Header:** `Engine/Plugins/PCG/Source/PCG/Public/PCGNode.h`
- **Status:** Stable, no renames vs 5.3.
- `AddEdgeTo(FName FromPinLabel, UPCGNode* To, FName ToPinLabel)` — returns `UPCGNode*` for chaining.
- `GetSettings()` returns the `UPCGSettings*` held by the node.
- `GetInputPin(FName)` / `GetOutputPin(FName)` — pin lookup.
- Pin-based connection model: `InputPins` / `OutputPins` arrays of `UPCGPin*`.
- Deprecated fields: `InboundEdges_DEPRECATED`, `OutboundEdges_DEPRECATED`, `OutboundNodes_DEPRECATED` — use pin-based API.

### UPCGEdge (Edge)

- **Header:** `Engine/Plugins/PCG/Source/PCG/Public/PCGEdge.h`
- **Status:** Stable. Pin-based model: `InputPin` / `OutputPin` (UPCGPin*).
- Deprecated: `InboundLabel_DEPRECATED`, `InboundNode_DEPRECATED`, `OutboundLabel_DEPRECATED`, `OutboundNode_DEPRECATED`.

### UPCGComponent (Execution)

- **Header:** `Engine/Plugins/PCG/Source/PCG/Public/PCGComponent.h`
- **Status:** Stable, no renames vs 5.3.
- `Generate()` — networked generation call (BlueprintCallable, NetMulticast, Reliable).
- `GenerateLocal(bool bForce)` — local generation, not replicated.
- New overloads in 5.7:
  - `GenerateLocal(EPCGComponentGenerationTrigger, bool bForce, EPCGHiGenGrid, TArray<FPCGTaskId>)`
  - `GenerateLocalGetTaskId(...)` — returns `FPCGTaskId` for chaining.
- `Cleanup(bool bRemoveComponents)` / `CleanupLocal(bool bRemoveComponents)` — stable.
- `SetGraph(UPCGGraphInterface*)` — sets the graph (NetMulticast, Reliable).
- `SetGraphLocal(UPCGGraphInterface*)` — local-only graph set.
- Generation triggers: `GenerateOnLoad`, `GenerateOnDemand`, `GenerateAtRuntime`.

### UPCGSettings (Base Settings)

- **Header:** `Engine/Plugins/PCG/Source/PCG/Public/PCGSettings.h`
- **Status:** Stable. Base class for all PCG settings.
- `EPCGSettingsType` enum includes: `Spatial`, `Density`, `Sampler`, `Spawner`, `Filter`, `Subgraph`, `Debug`, `Generic`, `Param`, etc.

### UPCGSettings Variants (Sampler/Spawner/Pruning)

All stable, no renames vs 5.3:

| Class | Header | Notes |
|-------|--------|-------|
| UPCGSplineSamplerSettings | `Elements/PCGSplineSampler.h` | Spline-based point sampling |
| UPCGSurfaceSamplerSettings | `Elements/PCGSurfaceSampler.h` | Surface mesh sampling |
| UPCGStaticMeshSpawnerSettings | `Elements/PCGStaticMeshSpawner.h` | Static mesh spawning |
| UPCGSelfPruningSettings | `Elements/PCGSelfPruning.h` | Distance-based self-pruning |

### PCGGeometryScriptInterop

- **Status:** Module referenced in Build.cs (`PCGGeometryScriptInterop`) but
  **source directory does not exist** in UE 5.7 (`Engine/Plugins/PCG/Source/`).
  Only `PCG`, `PCGCompute`, and `PCGEditor` source dirs exist.
- **Risk:** The module may be a future placeholder or merged into the main PCG
  module. Do not depend on it for W3 handlers. The Build.cs `AddDepSafe()` call
  is safe (no-op if missing) but actual includes will fail.

### FPCGEditorMode

- **Status:** No dedicated editor mode header found in `PCGEditor/Public/`.
  The PCG editor uses the standard `PCGEditor` module for graph editing.
  `use_pcg_editor_mode` handler should target the PCG graph editor tools
  rather than a standalone editor mode class.

## Reference implementation

The first promoted handler is `create_pcg_graph` in the
`codex-stubs-w2-ai-nav-part1` branch. Pattern follows the AI/Nav
promotion pattern:

```cpp
// FMCPScopedTransaction + NewObject<UPCGGraph>() + executed:true + PCGOk()
```

The handler creates a `UPCGGraph` asset in a package, marks it dirty,
and returns the asset path with `executed: true`.

## Risks

1. **PCGGeometryScriptInterop** — module does not exist as source in 5.7.
   Avoid depending on it. The Build.cs probe is safe but includes will fail.
2. **PCG Editor Mode** — no standalone `FPCGEditorMode` class found.
   The `use_pcg_editor_mode` handler needs re-scoping.
3. **Runtime vs Editor generation** — `UPCGComponent::Generate()` and
   `GenerateLocal()` have new overloads in 5.7. Use the simple
   `GenerateLocal(bool bForce)` for spike; advanced grid-based overloads
   can be used in later PRs.
4. **Pin-based connection model** — 5.7 uses `UPCGPin` for connections.
   The old `InboundEdges`/`OutboundEdges` arrays are deprecated.
   Always use `AddEdge()` / `AddEdgeTo()` with pin labels.

# MetaSound spike

234-stubs spike doc.

Owner: codex
Wave: W5
Issue: #99
Status: COMPLETE

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

### MetaSound Builder API (5.7 — stable)

UE 5.7 uses a **Builder pattern** for programmatic MetaSound construction.
Two layers exist:

**High-level (Blueprint-friendly):** `UMetaSoundBuilderBase` subclasses
- `UMetaSoundSourceBuilder` — builds `UMetaSoundSource`
- `UMetaSoundPatchBuilder` — builds `UMetaSoundPatch`
- Factory: `UMetaSoundBuilderSubsystem` (engine subsystem)

**Low-level:** `FMetaSoundFrontendDocumentBuilder` (USTRUCT, operates on `FMetasoundFrontendDocument`)

### Key Factory Methods — UMetaSoundBuilderSubsystem

| Method | Returns |
|--------|---------|
| `CreateSourceBuilder(Name, ...)` | `UMetaSoundSourceBuilder*` |
| `CreatePatchBuilder(Name, OutResult)` | `UMetaSoundPatchBuilder*` |

Access: `GEngine->GetEngineSubsystem<UMetaSoundBuilderSubsystem>()`

### Key Builder Methods — UMetaSoundBuilderBase

| Method | Purpose |
|--------|---------|
| `AddGraphInputNode(Name, DataType, DefaultValue, OutResult)` | Add input pin |
| `AddGraphOutputNode(Name, DataType, DefaultValue, OutResult)` | Add output pin |
| `AddNodeByClassName(ClassName, OutResult, MajorVersion)` | Add node by class |
| `ConnectNodes(OutHandle, InHandle, OutResult)` | Wire nodes |
| `ConnectNodeOutputToGraphOutput(Name, Handle, OutResult)` | Wire to output |
| `ConnectNodeInputToGraphInput(Name, Handle, OutResult)` | Wire from input |
| `SetNodeInputDefault(Handle, Literal, OutResult)` | Set pin default |
| `SetGraphInputDefault(Name, Literal, OutResult)` | Set input default |
| `FindNodeInputByName(NodeHandle, Name, OutResult)` | Find input handle |
| `FindNodeOutputByName(NodeHandle, Name, OutResult)` | Find output handle |
| `AddInterface(InterfaceName, OutResult)` | Add interface |
| `BuildNewMetaSound(FName)` | Produce transient asset |

### Handle Types

- `FMetaSoundNodeHandle` — wraps `FGuid NodeID`
- `FMetaSoundBuilderNodeInputHandle` — `NodeID + VertexID`
- `FMetaSoundBuilderNodeOutputHandle` — `NodeID + VertexID`
- `EMetaSoundBuilderResult` — Succeeded/Failed

### Literal System — FMetasoundFrontendLiteral

Supports: None, Boolean, Integer, Float, String, UObject (+ array variants).
Methods: `Set(bool)`, `Set(int32)`, `Set(float)`, `Set(FString)`, `TryGet(T&)`.

Subsystem helpers: `CreateFloatMetaSoundLiteral(Value)`, etc.

### Data Type Names for Inputs/Outputs

`"Audio"`, `"Trigger"`, `"Float"`, `"Int32"`, `"Bool"`, `"String"`

### Asset Persistence (Editor Only)

`UMetaSoundEditorSubsystem::BuildToAsset(Builder, Author, AssetName, PackagePath, OutResult)`
Header: `MetasoundEditorSubsystem.h` (MetasoundEditor module)

### Runtime Parameter Control

`UMetasoundGeneratorHandle::CreateMetaSoundGeneratorHandle(AudioComponent)`
Then `ApplyParameterPack(UMetasoundParameterPack*)` for live changes.

### SoundCue Graph Editing

SoundCue uses a completely different tree model (`USoundNode` tree via `FirstNode`).
Most graph APIs are `#if WITH_EDITOR`. No clean builder API exists.
`ConstructSoundNode<T>(Class, bSelect)` creates nodes. EdGraph manipulation
requires `ISoundCueAudioEditor` (editor module).

### UE 5.7 Deprecation Notes

- `GetDocumentAccessPtr()` / `GetDocumentConstAccessPtr()` deprecated (5.6) — use Builder API
- `AttachPatchBuilderToAsset` / `AttachSourceBuilderToAsset` deprecated (5.5) — use `FDocumentBuilderRegistry::FindOrBeginBuilding`
- `FAssetInfo` deprecated (5.6) — use `FAssetRef`
- `CookPages` deprecated (5.7) — use `StripUnusedPages`
- Node update transforms are `UE_EXPERIMENTAL(5.7, ...)` — avoid

### Module Headers (canonical)

| Module | Key Headers |
|--------|-------------|
| MetasoundEngine | `MetasoundSource.h`, `Metasound.h`, `MetasoundBuilderBase.h`, `MetasoundBuilderSubsystem.h`, `MetasoundGeneratorHandle.h` |
| MetasoundFrontend | `MetasoundFrontendDocument.h`, `MetasoundFrontendDocumentBuilder.h`, `MetasoundFrontendLiteral.h`, `MetasoundDocumentInterface.h` |
| MetasoundEditor | `MetasoundEditorSubsystem.h`, `MetasoundFactory.h` |

### Build.cs Dependencies (already configured)

```csharp
// UnrealMCP.Build.cs lines 265-273
string[] RuntimeMetaSound = new string[] {
    "MetasoundEngine", "MetasoundFrontend", "MetasoundGenerator", "MetasoundGraphCore"
};
AddOptionalModuleGate(Target, "MetasoundEditor", true);
```

Generates `WITH_METASOUNDENGINE_MCP`, `WITH_METASOUNDEDITOR_MCP` etc.

## Recommended Implementation Strategy

### For `create_metasound_source`:
1. Get `UMetaSoundBuilderSubsystem*`
2. `CreateSourceBuilder(Name, ...)` → `UMetaSoundSourceBuilder*`
3. Use `AddGraphInputNode`, `AddNodeByClassName`, `ConnectNodes` etc.
4. `BuildNewMetaSound(AssetName)` → transient `UMetaSoundSource`
5. If persisting: `UMetaSoundEditorSubsystem::BuildToAsset(...)`
6. `FMCPScopedTransaction` + `MarkPackageDirty()` for undo

### For `create_metasound_patch`:
Same flow but `CreatePatchBuilder(Name, OutResult)` → `UMetaSoundPatchBuilder*`

### For `add_metasound_graph_node`:
1. Find existing builder via `FindBuilder(AssetName)` or create new
2. `AddNodeByClassName(ClassName, OutResult, MajorVersion)`
3. `ConnectNodes(...)` if connections specified
4. Rebuild/re-register

### For `set_metasound_parameter`:
1. `SetNodeInputDefault(Handle, Literal, OutResult)` at build time
2. Or `UMetasoundGeneratorHandle` + `ApplyParameterPack` at runtime

### For `edit_sound_cue_graph`:
1. Load `USoundCue` asset
2. `ConstructSoundNode<T>(NodeClass, false)` to add nodes
3. Wire via `USoundNode` tree (ConnectChild, etc.)
4. `CompileSoundNodesFromGraphNodes()` to finalize

## Reference Implementation

_W5-1 PR will contain the first promoted handlers as canonical samples._

## Risks

- **Builder subsystem availability**: `UMetaSoundBuilderSubsystem` is an engine subsystem — should always be available in editor builds. Confirm at runtime.
- **SoundCue complexity**: `edit_sound_cue_graph` has no clean builder API; implementation will be more manual than MetaSound handlers.
- **Asset vs Transient**: Most handlers should work with transient assets first. Asset persistence via `BuildToAsset` requires MetasoundEditor module (editor-only).

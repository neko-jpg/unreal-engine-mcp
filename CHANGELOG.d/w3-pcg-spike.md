# Changelog: W3 PCG spike

## feat(234-stubs W3 #91): PCG spike — UE 5.7 API research + promote create_pcg_graph

### Summary

- Completed UE 5.7 API research for PCG module (20 stubs target)
- Promoted `create_pcg_graph` handler from stub to executed envelope
- Added PCGOk/PCGErr helper functions matching AiNav pattern
- Added `#if WITH_PCG_MCP` compile gate for PCG module dependency
- Created unit test `test_w3_pcg_spike_executed_envelope.py`

### API Research

- **UPCGGraph**: Stable. Header `PCGGraph.h`. `AddNode()`, `AddEdge()`, `Nodes` array unchanged.
- **UPCGNode**: Stable. Header `PCGNode.h`. `AddEdgeTo()` signature unchanged.
- **UPCGEdge**: Stable. Header `PCGEdge.h`. Pin-based model (`InputPin`/`OutputPin`).
- **UPCGComponent**: Stable. Header `PCGComponent.h`. `Generate()`, `GenerateLocal()` unchanged. New grid-based overloads in 5.7.
- **PCGGeometryScriptInterop**: Module referenced in Build.cs but source directory does NOT exist in 5.7. Risk for future handlers.
- **Settings variants**: `PCGSplineSampler`, `PCGSurfaceSampler`, `PCGStaticMeshSpawner`, `PCGSelfPruning` all stable.

### Files changed

- `docs/spike/pcg-ue57.md` — Full API research findings
- `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPPCGCommands.cpp` — Promoted `create_pcg_graph`
- `Python/tests/unit/test_w3_pcg_spike_executed_envelope.py` — Unit test
- `CHANGELOG.d/w3-pcg-spike.md` — This file

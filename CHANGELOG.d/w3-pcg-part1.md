# Changelog: W3 PCG part1

## feat(234-stubs W3 #91): promote 8 PCG handlers to executed envelope (part1)

### Summary

- Promoted 8 PCG handlers from stub to executed envelope (part1 of 2)
- Handlers promoted:
  - `add_pcg_component` — UPCGComponent on actor
  - `create_pcg_volume` — APCGVolume
  - `add_pcg_node` — UPCGNode + UPCGSettings
  - `connect_pcg_nodes` — UPCGNode::AddEdgeTo()
  - `set_pcg_graph_parameter` — UPCGGraph::Parameters
  - `configure_pcg_spline_sampler` — UPCGSettings_SplineSampler
  - `configure_pcg_surface_sampler` — UPCGSettings_SurfaceSampler
  - `configure_pcg_static_mesh_spawner` — UPCGSettings_StaticMeshSpawner
- Added UE 5.7 PCG headers: PCGComponent.h, PCGVolume.h, PCGNode.h, PCGSettings.h, PCGEdge.h, sampler/spawner settings
- Added FindActorInEditorWorld() and ResolveGraph() static helpers (matching GAS/AiNav pattern)
- Created unit test `test_w3_pcg_part1_executed_envelope.py` (8 test cases)

### Files changed

- `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPPCGCommands.cpp` — Promoted 8 handlers
- `Python/tests/unit/test_w3_pcg_part1_executed_envelope.py` — Unit test
- `CHANGELOG.d/w3-pcg-part1.md` — This file

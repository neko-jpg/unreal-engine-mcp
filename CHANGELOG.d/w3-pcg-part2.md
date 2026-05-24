# 234-stubs W3 #91: PCG part2 — promote 11 queued handlers to executed envelope

Promotes the remaining 11 queued PCG handlers in `EpicUnrealMCPPCGCommands.cpp`
from `{queued: true}` to the canonical `{success: true, data: {executed: true, ...}}` envelope.

Handlers promoted:
- `configure_pcg_rule` — Add filter/rule node to PCG graph
- `create_pcg_biome_graph` — Create PCG biome graph asset
- `operate_pcg_point_data` — Configure point data operations
- `operate_pcg_attribute` — Configure attribute operations
- `execute_pcg_graph` — Trigger PCG generation via UPCGComponent::Generate()
- `regenerate_pcg_graph` — Cleanup + regenerate PCG graph
- `set_pcg_runtime_generation` — Toggle runtime generation trigger
- `use_pcg_editor_mode` — Set PCG editor mode preference
- `create_pcg_tool` — Create PCG tool graph asset
- `set_pcg_debug_display` — Toggle PCG debug display
- `configure_pcg_self_pruning` — Configure self-pruning radius

C++ changes:
- All 11 handlers wrapped in `#if WITH_PCG_MCP` / `#if WITH_EDITOR`
- FMCPScopedTransaction + Modify() + MarkPackageDirty() for undo support
- Metadata-based config for settings-only operations
- PCGComponent API (Generate/CleanupLocal) for execution handlers

Python changes:
- Updated docstrings from "queued" to descriptive text in `pcg_tools.py`

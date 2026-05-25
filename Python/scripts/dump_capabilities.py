"""Dump the capability registry to docs/dev/capabilities.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parent.parent.parent
PY_ROOT = HERE.parent.parent
OUT_PATH = REPO_ROOT / "docs" / "dev" / "capabilities.json"

sys.path.insert(0, str(PY_ROOT))

PATTERN = re.compile(r"@mcp\.tool\(\)\s*\ndef\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")


def _collect_python_tools():
    server_dir = PY_ROOT / "server"
    tools = []
    for path in sorted(server_dir.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="cp932", errors="replace")
        for match in PATTERN.finditer(text):
            tools.append(match.group(1))
    return sorted(set(tools))


CPP_ROUTES = [
    {"id": 1, "name": "Actor"},
    {"id": 2, "name": "Blueprint"},
    {"id": 3, "name": "BlueprintGraph"},
    {"id": 4, "name": "Material"},
    {"id": 5, "name": "ProjectEditor"},
    {"id": 6, "name": "ContentBrowser"},
    {"id": 7, "name": "AssetImport"},
    {"id": 8, "name": "MeshEditing"},
    {"id": 9, "name": "EnhancedInput"},
    {"id": 10, "name": "GameplayFramework"},
    {"id": 11, "name": "UMG"},
    {"id": 12, "name": "Rendering"},
    {"id": 13, "name": "LightingAtmosphere"},
    {"id": 14, "name": "DataTable"},
    {"id": 15, "name": "Audio"},
    {"id": 16, "name": "Sequencer"},
    {"id": 17, "name": "Vroid"},
    {"id": 18, "name": "Cesium"},
    {"id": 19, "name": "Procedural"},
    {"id": 20, "name": "Navigation"},
    {"id": 21, "name": "Niagara"},
    {"id": 22, "name": "Physics"},
    {"id": 23, "name": "Validation"},
    {"id": 24, "name": "Instance"},
    {"id": 25, "name": "Landscape"},
    {"id": 26, "name": "MovieRenderQueue"},
    {"id": 27, "name": "Foliage"},
    {"id": 28, "name": "PCG"},
    {"id": 29, "name": "Chaos"},
    {"id": 30, "name": "GAS"},
    {"id": 31, "name": "Water"},
    {"id": 32, "name": "SourceControl"},
    {"id": 33, "name": "Localization"},
    {"id": 34, "name": "MetaSound"},
    {"id": 35, "name": "AnimationRigging"},
    {"id": 36, "name": "AiNavExtension"},
    {"id": 37, "name": "Networking"},
    {"id": 38, "name": "MobileXr"},
    {"id": 39, "name": "TestingValidation"},
    {"id": 40, "name": "DataTableExtension"},
    {"id": 41, "name": "SequencerExtension"},
    {"id": 42, "name": "PackagingExtension"},
]


def main():
    from server.planning.capability_registry import get_default_registry
    registry = get_default_registry()
    payload = {
        "version": "v3.0",
        "capabilities": registry.dump(),
        "python_tools": _collect_python_tools(),
        "cpp_routes": CPP_ROUTES,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    cap_count = len(payload["capabilities"])
    tool_count = len(payload["python_tools"])
    route_count = len(payload["cpp_routes"])
    print(f"Wrote {cap_count} capabilities, {tool_count} python tools, {route_count} cpp routes to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

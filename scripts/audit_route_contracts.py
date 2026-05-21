"""3-layer route contract audit (中長期-5).

Scans the three layers of the Unreal MCP stack and emits a CSV report
showing which commands exist in each layer. Useful for spotting drift
when a command is added to one layer but not the others.

Layers:
    Python  - server/*_tools.py        (calls via conn.send_command("name", ...))
    Rust    - rust/scene-syncd/src/api (axum Router::new().route("/path", ...))
    UE C++  - Plugins/.../*Commands.cpp (dispatch tables {TEXT("name"), &Handler})

Outputs:
    artifacts/route_contracts.csv with columns:
        command_name,python_callers,rust_routes,cpp_handlers,layers

Exit codes:
    0  success (or only informational drift)
    1  hard inconsistency detected when --strict is passed
"""

from __future__ import annotations

import argparse
import ast
import csv
import io
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SERVER_DIR = REPO_ROOT / "Python" / "server"
PYTHON_HELPERS_DIR = REPO_ROOT / "Python" / "helpers"
RUST_DIR = REPO_ROOT / "rust" / "scene-syncd" / "src" / "api"
CPP_DIR = REPO_ROOT / "Plugins" / "UnrealMCP" / "Source" / "UnrealMCP" / "Private" / "Commands"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "route_contracts.csv"

# Commands that are intentionally cpp-only because they are either dispatched
# through aggregate tools (e.g. asset_mesh_editing_tool), wrappers (e.g.
# `set_*_setting` exposed via engine_settings_tool), explicitly unsupported
# (`import_mp3`), or low-level primitives invoked by the orchestrator
# directly. Mirrors the whitelist in
# Python/tests/unit/test_tool_registration_and_mapping.py.
CPP_ONLY_WHITELIST: Set[str] = {
    "ping",
    "apply_scene_delta",
    "clone_actor",
    "create_spline_from_points",
    "start_pie",
    "stop_pie",
    "start_simulate",
    "start_standalone_game",
    "set_engine_scalability",
    "set_rendering_setting",
    "set_physics_setting",
    "set_input_setting",
    "set_collision_setting",
    "set_ai_setting",
    "set_navigation_setting",
    "set_packaging_setting",
    "import_mp3",
}


def _iter_python_files() -> Iterable[Path]:
    files: List[Path] = []
    if PYTHON_SERVER_DIR.exists():
        files.extend(sorted(PYTHON_SERVER_DIR.rglob("*.py")))
    if PYTHON_HELPERS_DIR.exists():
        files.extend(sorted(PYTHON_HELPERS_DIR.rglob("*.py")))
    return files


def _iter_rust_files() -> Iterable[Path]:
    if not RUST_DIR.exists():
        return []
    return sorted(RUST_DIR.glob("*_routes.rs"))


def _iter_cpp_files() -> Iterable[Path]:
    if not CPP_DIR.exists():
        return []
    return sorted(CPP_DIR.glob("*Commands.cpp"))


def collect_python_send_commands() -> Dict[str, List[str]]:
    """Return {command_name: [source files]} from Python conn.send_command() calls."""
    result: Dict[str, List[str]] = defaultdict(list)

    for path in _iter_python_files():
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "send_command":
                if node.args:
                    first = node.args[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        result[first.value].append(str(path.relative_to(REPO_ROOT)))
                    elif isinstance(first, ast.Str):  # py<3.8 backstop
                        result[first.s].append(str(path.relative_to(REPO_ROOT)))
    return result


def collect_rust_routes() -> Dict[str, List[str]]:
    """Return {route_path: [source files]} from axum router declarations."""
    result: Dict[str, List[str]] = defaultdict(list)
    pattern = re.compile(r'\.route\(\s*"([^"]+)"')
    for path in _iter_rust_files():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in pattern.finditer(text):
            route = match.group(1)
            result[route].append(str(path.relative_to(REPO_ROOT)))
    return result


def collect_cpp_handlers() -> Dict[str, List[str]]:
    """Return {command_name: [source files]} from C++ handler dispatch.

    Recognizes two dispatch styles used by the plugin:
      1. ``{TEXT("name"), &FXxx::HandleY}`` — TMap dispatch tables.
      2. ``if (CommandType == TEXT("name")) return HandleY(Params);`` — chained
         if-statements (used by handlers split off in Phase 4 refactor).

    Router files (EpicUnrealMCPRouter.cpp) also contain ``{TEXT("name"), N}``
    entries that route to a numbered handler bucket; those are matched so the
    audit can see them, but with a lighter pattern.
    """
    result: Dict[str, List[str]] = defaultdict(list)
    # Pattern A: {TEXT("name"), &FEpicUnrealMCPxxxCommands::HandleY}
    handler_pattern = re.compile(
        r'\{\s*TEXT\(\s*"([^"]+)"\s*\)\s*,\s*&\s*F?Epic[A-Za-z0-9_]+::[A-Za-z0-9_]+\s*\}'
    )
    # Pattern B: if (CommandType == TEXT("name"))   ... return HandleX(Params);
    if_pattern = re.compile(r'CommandType\s*==\s*TEXT\(\s*"([^"]+)"\s*\)')
    # Pattern C: router buckets {TEXT("name"), <int>}
    router_pattern = re.compile(r'\{\s*TEXT\(\s*"([^"]+)"\s*\)\s*,\s*\d+\s*\}')

    for path in _iter_cpp_files():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in handler_pattern.finditer(text):
            result[match.group(1)].append(str(path.relative_to(REPO_ROOT)))
        for match in if_pattern.finditer(text):
            result[match.group(1)].append(str(path.relative_to(REPO_ROOT)))
        for match in router_pattern.finditer(text):
            result[match.group(1)].append(str(path.relative_to(REPO_ROOT)))
    # Deduplicate per-command file references.
    for k, v in list(result.items()):
        result[k] = sorted(set(v))
    return result


def _rust_route_to_command_name(route: str) -> str:
    """Convert "/scenes/create" -> "scenes_create" for cross-layer matching."""
    s = route.strip("/").replace("/", "_")
    # Curly braces in axum path params: /{run_id} -> _run_id_
    s = re.sub(r"\{([^}]+)\}", r"_\1_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def build_report() -> Tuple[List[Dict[str, object]], Dict[str, Set[str]]]:
    py = collect_python_send_commands()
    rust = collect_rust_routes()
    cpp = collect_cpp_handlers()

    all_names: Set[str] = set()
    all_names.update(py.keys())
    all_names.update(cpp.keys())
    # Rust routes are paths; map them to flattened names so we can join.
    rust_flat: Dict[str, List[str]] = defaultdict(list)
    for route, files in rust.items():
        key = _rust_route_to_command_name(route)
        rust_flat[key].extend(files)
        all_names.add(key)

    rows: List[Dict[str, object]] = []
    for name in sorted(all_names):
        py_files = py.get(name, [])
        rust_files = rust_flat.get(name, [])
        cpp_files = cpp.get(name, [])
        layers: List[str] = []
        if py_files:
            layers.append("python")
        if rust_files:
            layers.append("rust")
        if cpp_files:
            layers.append("cpp")
        rows.append(
            {
                "command_name": name,
                "python_callers": ";".join(py_files),
                "rust_routes": ";".join(rust_files),
                "cpp_handlers": ";".join(cpp_files),
                "layers": "+".join(layers) if layers else "",
            }
        )

    layer_index: Dict[str, Set[str]] = {
        "python_only": set(),
        "rust_only": set(),
        "cpp_only": set(),
        "python_and_cpp": set(),
        "python_and_rust": set(),
        "rust_and_cpp": set(),
        "all_three": set(),
    }
    for row in rows:
        layers = str(row["layers"]).split("+") if row["layers"] else []
        s = set(layers)
        if s == {"python"}:
            layer_index["python_only"].add(str(row["command_name"]))
        elif s == {"rust"}:
            layer_index["rust_only"].add(str(row["command_name"]))
        elif s == {"cpp"}:
            layer_index["cpp_only"].add(str(row["command_name"]))
        elif s == {"python", "cpp"}:
            layer_index["python_and_cpp"].add(str(row["command_name"]))
        elif s == {"python", "rust"}:
            layer_index["python_and_rust"].add(str(row["command_name"]))
        elif s == {"rust", "cpp"}:
            layer_index["rust_and_cpp"].add(str(row["command_name"]))
        elif s == {"python", "rust", "cpp"}:
            layer_index["all_three"].add(str(row["command_name"]))

    return rows, layer_index


def write_csv(rows: List[Dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "command_name",
                "python_callers",
                "rust_routes",
                "cpp_handlers",
                "layers",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def print_summary(layer_index: Dict[str, Set[str]], output_path: Path) -> None:
    print(f"Route contracts written to: {output_path}")
    for category in [
        "all_three",
        "python_and_cpp",
        "python_and_rust",
        "rust_and_cpp",
        "python_only",
        "rust_only",
        "cpp_only",
    ]:
        items = sorted(layer_index[category])
        print(f"  {category}: {len(items)}")
        if items and category in {"python_only", "rust_only", "cpp_only"}:
            sample = ", ".join(items[:8]) + (" ..." if len(items) > 8 else "")
            print(f"    -> {sample}")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output CSV path (default: artifacts/route_contracts.csv)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 when a Python or Cpp handler is alone (no match in the other code layer).",
    )
    args = parser.parse_args(argv)

    rows, layer_index = build_report()
    write_csv(rows, args.output)
    print_summary(layer_index, args.output)

    if args.strict:
        # python_only is always a hard drift; cpp_only is allowed if whitelisted.
        unexpected_cpp_only = layer_index["cpp_only"] - CPP_ONLY_WHITELIST
        drift = layer_index["python_only"] | unexpected_cpp_only
        if drift:
            print("\nDrift detected (Python or unwhitelisted Cpp commands):")
            for name in sorted(drift):
                print(f"  - {name}")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

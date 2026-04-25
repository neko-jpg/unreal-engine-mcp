#!/usr/bin/env python3
"""CLI for operating scene-syncd managed Unreal scenes.

The CLI intentionally talks to scene-syncd instead of writing SurrealDB records
directly. That keeps scene-syncd as the API boundary for future UI and AI tools.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_SCENE_SYNCD_URL = os.getenv("SCENE_SYNCD_URL", "http://127.0.0.1:8787")
DEFAULT_UNREAL_HOST = os.getenv("UNREAL_MCP_HOST", "127.0.0.1")
DEFAULT_UNREAL_PORT = int(os.getenv("UNREAL_MCP_PORT", "55557"))
DEFAULT_SURREAL_HEALTH_URL = os.getenv("SURREAL_HEALTH_URL", "http://127.0.0.1:8000/health")
REPO_ROOT = Path(__file__).resolve().parents[1]
NO_COLOR = os.getenv("NO_COLOR") is not None


def enable_windows_ansi() -> None:
    if os.name != "nt" or NO_COLOR:
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


enable_windows_ansi()


class Style:
    RESET = "" if NO_COLOR else "\033[0m"
    BOLD = "" if NO_COLOR else "\033[1m"
    DIM = "" if NO_COLOR else "\033[2m"
    RED = "" if NO_COLOR else "\033[31m"
    GREEN = "" if NO_COLOR else "\033[32m"
    YELLOW = "" if NO_COLOR else "\033[33m"
    BLUE = "" if NO_COLOR else "\033[34m"
    CYAN = "" if NO_COLOR else "\033[36m"


def color(text: str, style: str) -> str:
    return f"{style}{text}{Style.RESET}" if style else text


class CliError(RuntimeError):
    pass


class SceneSyncdClient:
    def __init__(self, base_url: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get(self, path: str) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(f"{self.base_url}{path}", timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise CliError(f"GET {path} failed with HTTP {exc.code}: {body}") from exc
        except OSError as exc:
            raise CliError(f"cannot connect to scene-syncd at {self.base_url}: {exc}") from exc

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise CliError(f"POST {path} failed with HTTP {exc.code}: {body}") from exc
        except OSError as exc:
            raise CliError(f"cannot connect to scene-syncd at {self.base_url}: {exc}") from exc


class UnrealBridgeClient:
    def __init__(self, host: str, port: int, timeout: int = 30) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def command(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = json.dumps({"command": command, "params": params or {}}).encode("utf-8") + b"\n"
        try:
            with socket.create_connection((self.host, self.port), timeout=10) as client:
                client.settimeout(self.timeout)
                client.sendall(payload)
                data = bytearray()
                while b"\n" not in data:
                    chunk = client.recv(262144)
                    if not chunk:
                        break
                    data.extend(chunk)
        except OSError as exc:
            raise CliError(f"cannot connect to Unreal bridge at {self.host}:{self.port}: {exc}") from exc
        if not data:
            raise CliError(f"Unreal returned no response for {command}")
        return json.loads(bytes(data).split(b"\n", 1)[0].decode("utf-8"))


def require_success(label: str, response: dict[str, Any]) -> dict[str, Any]:
    if response.get("success") is not True:
        error = response.get("error") or response
        raise CliError(f"{label} failed: {json.dumps(error, ensure_ascii=False)}")
    return response


def response_data(response: dict[str, Any]) -> dict[str, Any]:
    require_success("request", response)
    data = response.get("data")
    return data if isinstance(data, dict) else {}


def fetch_objects(client: SceneSyncdClient, scene_id: str, include_deleted: bool = False) -> list[dict[str, Any]]:
    data = response_data(client.post("/objects/list", {"scene_id": scene_id, "include_deleted": include_deleted}))
    objects = data.get("objects", [])
    if not isinstance(objects, list):
        raise CliError("scene-syncd returned non-list objects payload")
    return [obj for obj in objects if isinstance(obj, dict)]


def get_tags(obj: dict[str, Any]) -> list[str]:
    tags = obj.get("tags") or []
    return [str(tag) for tag in tags if tag is not None]


def object_group(obj: dict[str, Any]) -> str:
    group = obj.get("group")
    if not group:
        return ""
    text = str(group)
    return text.split(":", 1)[1] if text.startswith("scene_group:") else text


def matches_filters(obj: dict[str, Any], args: argparse.Namespace) -> bool:
    if getattr(args, "mcp_id", None) and obj.get("mcp_id") != args.mcp_id:
        return False
    if getattr(args, "group", None) and object_group(obj) != args.group:
        return False
    if getattr(args, "tag", None):
        tags = set(get_tags(obj))
        if not all(tag in tags for tag in args.tag):
            return False
    if getattr(args, "name_contains", None):
        needle = args.name_contains.lower()
        name = str(obj.get("desired_name") or obj.get("mcp_id") or "").lower()
        if needle not in name:
            return False
    if getattr(args, "changed", False):
        if obj.get("desired_hash") == obj.get("last_applied_hash"):
            return False
    return True


def filter_objects(objects: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    return [obj for obj in objects if matches_filters(obj, args)]


def object_to_upsert_payload(scene_id: str, obj: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "scene_id": scene_id,
        "mcp_id": obj["mcp_id"],
        "desired_name": obj.get("desired_name") or obj["mcp_id"],
        "actor_type": obj.get("actor_type") or "StaticMeshActor",
        "asset_ref": obj.get("asset_ref") or {},
        "transform": obj.get("transform"),
        "visual": obj.get("visual") or {},
        "physics": obj.get("physics") or {},
        "tags": get_tags(obj),
    }
    group = object_group(obj)
    if group:
        payload["group_id"] = group
    return payload


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def print_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> None:
    if not rows:
        print(color("(no rows)", Style.DIM))
        return
    widths = []
    for key, title in columns:
        width = max(len(title), *(len(str(row.get(key, ""))) for row in rows))
        widths.append(min(width, 80))
    header = "  ".join(title.ljust(widths[i]) for i, (_, title) in enumerate(columns))
    print(color(header, Style.BOLD))
    print(color("  ".join("-" * widths[i] for i in range(len(columns))), Style.DIM))
    for row in rows:
        values = []
        for i, (key, _) in enumerate(columns):
            value = str(row.get(key, ""))
            if len(value) > widths[i]:
                value = value[: widths[i] - 1] + "..."
            values.append(value.ljust(widths[i]))
        print("  ".join(values))


def summarize_object(obj: dict[str, Any]) -> dict[str, Any]:
    transform = obj.get("transform") or {}
    loc = transform.get("location") or {}
    return {
        "mcp_id": obj.get("mcp_id", ""),
        "name": obj.get("desired_name", ""),
        "group": object_group(obj),
        "status": obj.get("sync_status", ""),
        "deleted": obj.get("deleted", False),
        "location": f"{loc.get('x', 0)},{loc.get('y', 0)},{loc.get('z', 0)}",
        "tags": ",".join(get_tags(obj)),
    }


def cmd_doctor(args: argparse.Namespace) -> int:
    client = SceneSyncdClient(args.scene_syncd_url, args.timeout)
    unreal = UnrealBridgeClient(args.unreal_host, args.unreal_port, args.timeout)
    checks: list[dict[str, str]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "ok" if ok else "fail", "detail": detail})

    try:
        require_success("scene-syncd health", client.get("/health"))
        add("scene-syncd", True, args.scene_syncd_url)
    except Exception as exc:
        add("scene-syncd", False, str(exc))

    try:
        with urllib.request.urlopen(args.surreal_health_url, timeout=5) as response:
            add("SurrealDB", response.status == 200, args.surreal_health_url)
    except Exception as exc:
        add("SurrealDB", False, str(exc))

    try:
        response = unreal.command("get_actors_in_level", {})
        actors = response.get("result", {}).get("actors", [])
        add("Unreal bridge", response.get("status") == "success", f"{len(actors)} actors")
    except Exception as exc:
        add("Unreal bridge", False, str(exc))

    try:
        response = unreal.command("find_actor_by_mcp_id", {"mcp_id": "__scenectl_missing__"})
        unknown = "Unknown command" in json.dumps(response, ensure_ascii=False)
        add("mcp_id commands", not unknown, "find_actor_by_mcp_id available" if not unknown else "Unknown command")
    except Exception as exc:
        add("mcp_id commands", False, str(exc))

    if args.json:
        print_json({"success": all(row["status"] == "ok" for row in checks), "checks": checks})
    else:
        print_table(checks, [("check", "check"), ("status", "status"), ("detail", "detail")])
    return 0 if all(row["status"] == "ok" for row in checks) else 1


def cmd_start(args: argparse.Namespace) -> int:
    surreal = REPO_ROOT / "tools" / "surrealdb" / "surreal.exe"
    if not surreal.exists():
        surreal = REPO_ROOT / "surreal.exe"
    scene_syncd = REPO_ROOT / "rust" / "scene-syncd" / "target" / "debug" / "scene-syncd.exe"
    if not surreal.exists():
        raise CliError(f"SurrealDB executable not found at {surreal}")
    if not scene_syncd.exists():
        raise CliError(f"scene-syncd executable not found at {scene_syncd}; run cargo build in rust/scene-syncd")

    if args.surreal:
        subprocess.Popen(
            [str(surreal), "start", "--bind", args.surreal_bind, "--user", "root", "--pass", "secret", "memory"],
            cwd=str(REPO_ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        print(f"started SurrealDB on {args.surreal_bind}")
    if args.scene_syncd:
        subprocess.Popen(
            [str(scene_syncd)],
            cwd=str(scene_syncd.parent),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        print("started scene-syncd")
    if args.wait:
        time.sleep(args.wait)
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    if os.name != "nt":
        raise CliError("stop currently supports Windows process names only")
    names = []
    if args.surreal:
        names.append("surreal")
    if args.scene_syncd:
        names.append("scene-syncd")
    for name in names:
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Get-Process {name} -ErrorAction SilentlyContinue | Stop-Process"], check=False)
        print(f"stopped {name} if it was running")
    return 0


def cmd_scene_create(args: argparse.Namespace) -> int:
    client = SceneSyncdClient(args.scene_syncd_url, args.timeout)
    payload = {"scene_id": args.scene}
    if args.name:
        payload["name"] = args.name
    if args.description:
        payload["description"] = args.description
    response = require_success("scene create", client.post("/scenes/create", payload))
    print_json(response if args.json else response_data(response))
    return 0


def cmd_object_list(args: argparse.Namespace) -> int:
    client = SceneSyncdClient(args.scene_syncd_url, args.timeout)
    objects = filter_objects(fetch_objects(client, args.scene, args.include_deleted), args)
    if args.json:
        print_json({"scene_id": args.scene, "count": len(objects), "objects": objects})
    else:
        rows = [summarize_object(obj) for obj in objects]
        print_table(rows, [("mcp_id", "mcp_id"), ("name", "name"), ("group", "group"), ("status", "status"), ("deleted", "deleted"), ("location", "location"), ("tags", "tags")])
    return 0


def cmd_object_tag(args: argparse.Namespace) -> int:
    client = SceneSyncdClient(args.scene_syncd_url, args.timeout)
    objects = filter_objects(fetch_objects(client, args.scene, True), args)
    if not objects:
        raise CliError("no matching objects")
    if len(objects) > 1 and not args.yes:
        raise CliError(f"{len(objects)} objects match; pass --yes to update all")
    updated = []
    for obj in objects:
        tags = set(get_tags(obj))
        before = sorted(tags)
        if args.tag_action == "add":
            tags.update(args.tags)
        else:
            tags.difference_update(args.tags)
        if sorted(tags) == before:
            updated.append({"mcp_id": obj["mcp_id"], "changed": False, "tags": before})
            continue
        payload = object_to_upsert_payload(args.scene, obj)
        payload["tags"] = sorted(tags)
        require_success("object upsert", client.post("/objects/upsert", payload))
        updated.append({"mcp_id": obj["mcp_id"], "changed": True, "tags": sorted(tags)})
    print_json({"scene_id": args.scene, "updated": updated})
    return 0


def cmd_object_delete(args: argparse.Namespace) -> int:
    client = SceneSyncdClient(args.scene_syncd_url, args.timeout)
    objects = filter_objects(fetch_objects(client, args.scene, False), args)
    if not objects:
        raise CliError("no matching objects")
    summary = [{"mcp_id": obj.get("mcp_id"), "name": obj.get("desired_name"), "tags": get_tags(obj)} for obj in objects]
    if args.dry_run or not args.yes:
        print_json({"scene_id": args.scene, "dry_run": True, "would_tombstone": summary})
        if not args.yes:
            print("pass --yes to tombstone these objects", file=sys.stderr)
        return 0 if args.dry_run else 2
    for obj in objects:
        require_success("object delete", client.post("/objects/delete", {"scene_id": args.scene, "mcp_id": obj["mcp_id"]}))
    print_json({"scene_id": args.scene, "tombstoned": summary})
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    client = SceneSyncdClient(args.scene_syncd_url, args.timeout)
    response = require_success("sync plan", client.post("/sync/plan", {"scene_id": args.scene, "mode": "plan_only"}))
    data = response_data(response)
    if args.json:
        print_json(data)
    else:
        print_json(data.get("summary", {}))
        operations = data.get("operations") or []
        rows = [
            {"action": op.get("action"), "mcp_id": op.get("mcp_id"), "reason": op.get("reason")}
            for op in operations
            if args.all or op.get("action") != "noop"
        ]
        print_table(rows, [("action", "action"), ("mcp_id", "mcp_id"), ("reason", "reason")])
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    if not args.yes:
        raise CliError("apply changes Unreal; pass --yes after reviewing scenectl plan")
    client = SceneSyncdClient(args.scene_syncd_url, args.timeout)
    response = require_success(
        "sync apply",
        client.post(
            "/sync/apply",
            {
                "scene_id": args.scene,
                "mode": args.mode,
                "allow_delete": args.allow_delete,
                "max_operations": args.max_operations,
            },
        ),
    )
    data = response_data(response)
    if args.json:
        print_json(data)
    else:
        print_json(data.get("summary", {}))
        operations = data.get("operations") or []
        print_table(
            [{"action": op.get("action"), "mcp_id": op.get("mcp_id"), "status": op.get("status"), "error": op.get("error", "")} for op in operations],
            [("action", "action"), ("mcp_id", "mcp_id"), ("status", "status"), ("error", "error")],
        )
    return 0


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--scene-syncd-url", default=DEFAULT_SCENE_SYNCD_URL)
    parser.add_argument("--timeout", type=int, default=int(os.getenv("SCENE_SYNCD_TIMEOUT", "30")))
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")


def add_object_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--scene", default="main")
    parser.add_argument("--mcp-id")
    parser.add_argument("--tag", action="append", help="require tag; can be repeated")
    parser.add_argument("--group")
    parser.add_argument("--name-contains")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate scene-syncd managed Unreal scenes")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="check SurrealDB, scene-syncd, and Unreal bridge")
    add_common(doctor)
    doctor.add_argument("--unreal-host", default=DEFAULT_UNREAL_HOST)
    doctor.add_argument("--unreal-port", type=int, default=DEFAULT_UNREAL_PORT)
    doctor.add_argument("--surreal-health-url", default=DEFAULT_SURREAL_HEALTH_URL)
    doctor.set_defaults(func=cmd_doctor)

    start = sub.add_parser("start", help="start local SurrealDB and scene-syncd")
    start.add_argument("--surreal", action=argparse.BooleanOptionalAction, default=True)
    start.add_argument("--scene-syncd", action=argparse.BooleanOptionalAction, default=True)
    start.add_argument("--surreal-bind", default="127.0.0.1:8000")
    start.add_argument("--wait", type=float, default=2.0)
    start.set_defaults(func=cmd_start)

    stop = sub.add_parser("stop", help="stop local SurrealDB and scene-syncd")
    stop.add_argument("--surreal", action=argparse.BooleanOptionalAction, default=True)
    stop.add_argument("--scene-syncd", action=argparse.BooleanOptionalAction, default=True)
    stop.set_defaults(func=cmd_stop)

    scene = sub.add_parser("scene", help="scene operations")
    scene_sub = scene.add_subparsers(dest="scene_command", required=True)
    scene_create = scene_sub.add_parser("create", help="create or update a scene")
    add_common(scene_create)
    scene_create.add_argument("scene")
    scene_create.add_argument("--name")
    scene_create.add_argument("--description")
    scene_create.set_defaults(func=cmd_scene_create)

    obj = sub.add_parser("object", help="object operations")
    obj_sub = obj.add_subparsers(dest="object_command", required=True)

    obj_list = obj_sub.add_parser("list", help="list desired scene objects")
    add_common(obj_list)
    add_object_filters(obj_list)
    obj_list.add_argument("--include-deleted", action="store_true")
    obj_list.add_argument("--changed", action="store_true", help="show objects whose desired hash differs from last applied hash")
    obj_list.set_defaults(func=cmd_object_list)

    obj_tag = obj_sub.add_parser("tag", help="add or remove object tags")
    add_common(obj_tag)
    add_object_filters(obj_tag)
    obj_tag.add_argument("tag_action", choices=["add", "remove"])
    obj_tag.add_argument("tags", nargs="+")
    obj_tag.add_argument("--yes", action="store_true", help="allow multi-object tag updates")
    obj_tag.set_defaults(func=cmd_object_tag)

    obj_delete = obj_sub.add_parser("delete", help="tombstone objects in DB; use apply --allow-delete to delete in Unreal")
    add_common(obj_delete)
    add_object_filters(obj_delete)
    obj_delete.add_argument("--dry-run", action="store_true")
    obj_delete.add_argument("--yes", action="store_true")
    obj_delete.set_defaults(func=cmd_object_delete)

    plan = sub.add_parser("plan", help="preview DB -> Unreal sync operations")
    add_common(plan)
    plan.add_argument("--scene", default="main")
    plan.add_argument("--all", action="store_true", help="include noop operations in table output")
    plan.set_defaults(func=cmd_plan)

    apply = sub.add_parser("apply", help="apply DB -> Unreal sync operations")
    add_common(apply)
    apply.add_argument("--scene", default="main")
    apply.add_argument("--mode", default="apply_safe", choices=["apply_safe", "apply_all", "plan_only"])
    apply.add_argument("--allow-delete", action="store_true")
    apply.add_argument("--max-operations", type=int, default=500)
    apply.add_argument("--yes", action="store_true")
    apply.set_defaults(func=cmd_apply)

    return parser


INTERACTIVE_HELP = f"""{color("Common commands", Style.BOLD)}
  {color("/doctor", Style.CYAN)}                                      Check SurrealDB, scene-syncd, Unreal bridge
  {color("/start", Style.CYAN)}                                       Start local SurrealDB and scene-syncd
  {color("/object list --scene <id>", Style.CYAN)}                    List DB scene objects
  {color("/object list --scene <id> --tag <tag>", Style.CYAN)}        Filter objects by DB tag
  {color("/object tag --scene <id> --group <g> add <tag> --yes", Style.CYAN)}
                                              Add tags to matching DB objects
  {color("/plan --scene <id>", Style.CYAN)}                           Preview DB -> Unreal sync
  {color("/apply --scene <id> --yes", Style.CYAN)}                    Apply DB -> Unreal sync
  {color("/object delete --scene <id> --tag <tag> --dry-run", Style.CYAN)}
                                              Preview tombstones

{color("Shell commands", Style.BOLD)}
  {color("/help", Style.CYAN)}                 Show this help
  {color("/help <command>", Style.CYAN)}       Show argparse help for a command
  {color("/clear", Style.CYAN)}                Clear the terminal
  {color("/exit", Style.CYAN)} / {color("/quit", Style.CYAN)}        Leave scenectl
"""


SLASH_COMMANDS = [
    "/help",
    "/doctor",
    "/start",
    "/stop",
    "/scene create",
    "/object list",
    "/object tag",
    "/object delete",
    "/plan",
    "/apply",
    "/clear",
    "/exit",
    "/quit",
]


def print_banner() -> None:
    print(color("scenectl", Style.BOLD + Style.CYAN) + color(" interactive shell", Style.CYAN))
    print(color("Scene DB -> scene-syncd -> Unreal operations. Type '/help' or '/exit'.", Style.DIM))


def split_interactive_line(line: str) -> list[str]:
    return shlex.split(line, posix=True)


def print_slash_suggestions(prefix: str = "/") -> None:
    matches = [cmd for cmd in SLASH_COMMANDS if cmd.startswith(prefix)] or SLASH_COMMANDS
    print(color("commands:", Style.BOLD))
    for cmd in matches:
        print(f"  {color(cmd, Style.CYAN)}")


def read_interactive_line(prompt: str) -> str:
    if os.name != "nt" or not sys.stdin.isatty():
        return input(prompt)

    import msvcrt

    buffer: list[str] = []
    print(prompt, end="", flush=True)
    while True:
        ch = msvcrt.getwch()
        if ch in ("\r", "\n"):
            print()
            return "".join(buffer)
        if ch == "\x03":
            raise KeyboardInterrupt
        if ch == "\x1a":
            raise EOFError
        if ch == "\b":
            if buffer:
                buffer.pop()
                print("\b \b", end="", flush=True)
            continue
        if ch == "\t":
            current = "".join(buffer)
            if current.startswith("/"):
                print()
                print_slash_suggestions(current)
                print(prompt + current, end="", flush=True)
            continue
        if ch in ("\x00", "\xe0"):
            msvcrt.getwch()
            continue
        if ch.isprintable():
            buffer.append(ch)
            print(ch, end="", flush=True)
            current = "".join(buffer)
            if current == "/":
                print()
                print_slash_suggestions("/")
                print(prompt + current, end="", flush=True)


def run_parsed_command(parser: argparse.ArgumentParser, argv: list[str]) -> int:
    try:
        args = parser.parse_args(argv)
        return args.func(args)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else 1
    except CliError as exc:
        print(color(f"scenectl: {exc}", Style.RED), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print()
        return 130


def interactive_shell() -> int:
    parser = build_parser()
    print_banner()
    last_status = 0

    while True:
        prompt_color = Style.GREEN if last_status == 0 else Style.RED
        try:
            line = read_interactive_line(color("scenectl", prompt_color) + color("> ", Style.BOLD))
        except EOFError:
            print()
            return last_status
        except KeyboardInterrupt:
            print()
            last_status = 130
            continue

        line = line.strip()
        if not line:
            continue
        if line.startswith("/"):
            line = line[1:]
        if line in {"exit", "quit", ":q"}:
            return last_status
        if line == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            continue
        if line == "help":
            print(INTERACTIVE_HELP)
            continue
        if line.startswith("help "):
            line = f"{line[5:]} --help"

        try:
            argv = split_interactive_line(line)
        except ValueError as exc:
            print(color(f"parse error: {exc}", Style.RED), file=sys.stderr)
            last_status = 2
            continue

        last_status = run_parsed_command(parser, argv)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return interactive_shell()
    parser = build_parser()
    return run_parsed_command(parser, argv)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Launch the full Unreal MCP development stack in one command.

Starts SurrealDB, scene-syncd, Unreal Editor, and the Python MCP server.
Each service runs in its own subprocess. Logs are color-coded and streamed
to the console. Press Ctrl+C to gracefully shut everything down.

Usage:
    python scripts/launch-dev-stack.py --all
    python scripts/launch-dev-stack.py --surreal --scene-syncd
    python scripts/launch-dev-stack.py --unreal --mcp-server
    python scripts/launch-dev-stack.py --help
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = REPO_ROOT / "Python"
RUST_ROOT = REPO_ROOT / "rust" / "scene-syncd"
ROOT_PLUGIN_PATH = REPO_ROOT / "Plugins" / "UnrealMCP"
MATERIALIZED_PROJECT_ROOT = REPO_ROOT / "artifacts" / "dev_stack_host" / "materialized"
# Prefer the launcher-installed UE 5.7 project (EngineAssociation="5.7"). The
# source-built variant at FlopperamUnrealMCP/ requires a from-source engine.
# Override via UNREAL_MCP_UPROJECT env var to use a different .uproject.
_UPROJECT_57 = REPO_ROOT / "FlopperamUnrealMCP 5.7" / "FlopperamUnrealMCP.uproject"
_UPROJECT_SRC = REPO_ROOT / "FlopperamUnrealMCP" / "FlopperamUnrealMCP.uproject"
_UPROJECT_HOST = REPO_ROOT / "artifacts" / "dev_stack_host" / "HostProject" / "HostProject.uproject"
_UPROJECT_OVERRIDE = os.getenv("UNREAL_MCP_UPROJECT")
if _UPROJECT_OVERRIDE:
    UPROJECT_PATH = Path(_UPROJECT_OVERRIDE)
elif _UPROJECT_57.exists():
    UPROJECT_PATH = _UPROJECT_57
elif _UPROJECT_SRC.exists():
    UPROJECT_PATH = _UPROJECT_SRC
else:
    UPROJECT_PATH = _UPROJECT_HOST

DEFAULT_SURREAL_BIND = "127.0.0.1:8000"
DEFAULT_SCENE_SYNCD_URL = "http://127.0.0.1:8787"
DEFAULT_UNREAL_HOST = "127.0.0.1"
DEFAULT_UNREAL_PORT = 55771
UNREAL_MCP_PLUGIN_NAME = "UnrealMCP"

NO_COLOR = os.getenv("NO_COLOR") is not None


class Style:
    RESET = "" if NO_COLOR else "\033[0m"
    BOLD = "" if NO_COLOR else "\033[1m"
    DIM = "" if NO_COLOR else "\033[2m"
    RED = "" if NO_COLOR else "\033[31m"
    GREEN = "" if NO_COLOR else "\033[32m"
    YELLOW = "" if NO_COLOR else "\033[33m"
    BLUE = "" if NO_COLOR else "\033[34m"
    MAGENTA = "" if NO_COLOR else "\033[35m"
    CYAN = "" if NO_COLOR else "\033[36m"


def log(service: str, message: str, color: str = Style.RESET) -> None:
    prefix = f"[{color}{Style.BOLD}{service}{Style.RESET}]"
    print(f"{prefix} {message}", flush=True)


def _is_path_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def resolve_requested_uproject(args: argparse.Namespace) -> Path:
    """Resolve the user-selected .uproject before optional MCP materialization."""
    if getattr(args, "uproject", None):
        return Path(args.uproject)
    return UPROJECT_PATH


def _read_project_descriptor(uproject_path: Path) -> Dict[str, object]:
    try:
        return json.loads(uproject_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Could not parse .uproject JSON at {uproject_path}: {exc}") from exc


def _project_enables_plugin(descriptor: Dict[str, object], plugin_name: str) -> bool:
    plugins = descriptor.get("Plugins", [])
    if not isinstance(plugins, list):
        return False
    for entry in plugins:
        if isinstance(entry, dict) and entry.get("Name") == plugin_name:
            return bool(entry.get("Enabled", False))
    return False


def _ensure_project_plugin_enabled(uproject_path: Path, plugin_name: str) -> None:
    descriptor = _read_project_descriptor(uproject_path)
    plugins = descriptor.setdefault("Plugins", [])
    if not isinstance(plugins, list):
        plugins = []
        descriptor["Plugins"] = plugins

    for entry in plugins:
        if isinstance(entry, dict) and entry.get("Name") == plugin_name:
            entry["Enabled"] = True
            break
    else:
        plugins.append({"Name": plugin_name, "Enabled": True})

    uproject_path.write_text(json.dumps(descriptor, indent=2) + "\n", encoding="utf-8")


def _copy_project_for_materialization(source_project: Path, target_dir: Path) -> Path:
    source_dir = source_project.parent
    target_project = target_dir / source_project.name
    target_dir.mkdir(parents=True, exist_ok=True)

    ignored = {
        ".vs",
        "DerivedDataCache",
        "Intermediate",
        "Saved",
    }
    for item in source_dir.iterdir():
        if item.name in ignored:
            continue
        target = target_dir / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    return target_project


def _link_or_copy_plugin(plugin_source: Path, project_root: Path) -> str:
    plugin_target = project_root / "Plugins" / UNREAL_MCP_PLUGIN_NAME
    plugin_target.parent.mkdir(parents=True, exist_ok=True)
    if plugin_target.exists():
        return "existing"

    try:
        os.symlink(plugin_source, plugin_target, target_is_directory=True)
        return "symlink"
    except OSError:
        pass

    if sys.platform == "win32":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(plugin_target), str(plugin_source)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and plugin_target.exists():
            return "junction"

    shutil.copytree(
        plugin_source,
        plugin_target,
        ignore=shutil.ignore_patterns("Intermediate", "Saved", ".vs"),
    )
    return "copy"


def materialize_mcp_project(uproject_path: Path) -> tuple[Path, Optional[str]]:
    """Create a workspace project that can discover the repo UnrealMCP plugin."""
    if not ROOT_PLUGIN_PATH.exists():
        raise RuntimeError(f"UnrealMCP plugin not found at {ROOT_PLUGIN_PATH}")

    descriptor = _read_project_descriptor(uproject_path)
    project_plugin = uproject_path.parent / "Plugins" / UNREAL_MCP_PLUGIN_NAME / "UnrealMCP.uplugin"
    if _project_enables_plugin(descriptor, UNREAL_MCP_PLUGIN_NAME) and project_plugin.exists():
        return uproject_path, None

    digest = hashlib.sha1(str(uproject_path.resolve()).encode("utf-8")).hexdigest()[:12]
    target_dir = MATERIALIZED_PROJECT_ROOT / f"{uproject_path.stem}_{digest}"
    if target_dir.exists() and not _is_path_within(target_dir, MATERIALIZED_PROJECT_ROOT):
        raise RuntimeError(f"Refusing to reuse unexpected materialized project path: {target_dir}")

    target_project = _copy_project_for_materialization(uproject_path, target_dir)
    if not target_project.exists():
        raise RuntimeError(f"Materialized project was not created: {target_project}")

    link_mode = _link_or_copy_plugin(ROOT_PLUGIN_PATH, target_dir)
    _ensure_project_plugin_enabled(target_project, UNREAL_MCP_PLUGIN_NAME)
    return target_project, link_mode


def resolve_unreal_engine_root() -> Optional[Path]:
    """Find Unreal Engine installation directory."""
    # 1. Environment variable
    env_root = os.getenv("UNREAL_ENGINE_ROOT")
    if env_root:
        p = Path(env_root)
        if p.exists():
            return p

    # 2. Windows registry
    if sys.platform == "win32":
        try:
            import winreg

            for subkey in ["5.7", "5.5", "5.4", "5.3"]:
                try:
                    with winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        f"SOFTWARE\\EpicGames\\Unreal Engine\\{subkey}",
                    ) as key:
                        value, _ = winreg.QueryValueEx(key, "InstalledDirectory")
                        p = Path(value)
                        if p.exists():
                            return p
                except FileNotFoundError:
                    continue
        except Exception:
            pass

    # 3. Common paths
    for candidate in [
        r"C:\Program Files\Epic Games\UE_5.7",
        r"C:\Program Files\Epic Games\UE_5.5",
        r"C:\Program Files\Epic Games\UE_5.4",
    ]:
        p = Path(candidate)
        if p.exists():
            return p

    # 4. PATH
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["where", "UnrealEditor.exe"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                exe_path = Path(result.stdout.strip().splitlines()[0])
                # UnrealEditor.exe is at Engine/Binaries/Win64/UnrealEditor.exe
                return exe_path.parents[2]
        except Exception:
            pass

    return None


def resolve_surrealdb_exe() -> Optional[Path]:
    """Find SurrealDB executable."""
    # Check PATH
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["where", "surreal"], capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                return Path(result.stdout.strip().splitlines()[0])
        except Exception:
            pass
    else:
        try:
            result = subprocess.run(
                ["which", "surreal"], capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except Exception:
            pass

    # Check repo-local copies
    for candidate in [
        REPO_ROOT / "tools" / "surrealdb" / "surreal.exe",
        REPO_ROOT / "surreal.exe",
        REPO_ROOT / "tools" / "surrealdb" / "surreal",
        REPO_ROOT / "surreal",
    ]:
        if candidate.exists():
            return candidate

    return None


def resolve_scene_syncd_exe() -> Optional[Path]:
    """Find scene-syncd executable or indicate cargo build is needed."""
    exe = RUST_ROOT / "target" / "debug" / "scene-syncd.exe"
    if sys.platform != "win32":
        exe = RUST_ROOT / "target" / "debug" / "scene-syncd"
    if exe.exists():
        source_files = list((RUST_ROOT / "src").rglob("*.rs"))
        source_files.append(RUST_ROOT / "Cargo.toml")
        exe_mtime = exe.stat().st_mtime
        if any(path.exists() and path.stat().st_mtime > exe_mtime for path in source_files):
            return None
        return exe
    return None


def stream_output(proc: subprocess.Popen, service: str, color: str) -> None:
    """Stream subprocess stdout/stderr to console with color-coded prefix."""
    def read_stdout():
        try:
            if proc.stdout:
                for line in iter(proc.stdout.readline, b""):
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").rstrip()
                    if text:
                        log(service, text, color)
        except Exception:
            pass

    def read_stderr():
        try:
            if proc.stderr:
                for line in iter(proc.stderr.readline, b""):
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").rstrip()
                    if text:
                        log(service, f"{Style.RED}{text}{Style.RESET}", color)
        except Exception:
            pass

    t_out = threading.Thread(target=read_stdout, daemon=True)
    t_err = threading.Thread(target=read_stderr, daemon=True)
    t_out.start()
    t_err.start()
    t_out.join()
    t_err.join()


def wait_for_service(url: str, timeout: float = 30.0, interval: float = 0.5) -> bool:
    """Poll a URL until it responds or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def wait_for_tcp(host: str, port: int, timeout: float = 60.0, interval: float = 0.5) -> bool:
    """Poll a TCP port until it accepts connections or timeout."""
    import socket

    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def wait_for_tcp_or_process_exit(
    host: str,
    port: int,
    proc: subprocess.Popen,
    timeout: float = 60.0,
    interval: float = 0.5,
) -> tuple[bool, bool]:
    """Poll a TCP port until it accepts connections or the process exits.

    Returns (tcp_ready, process_exited).
    """
    import socket

    start = time.time()
    while time.time() - start < timeout:
        if proc.poll() is not None:
            return False, True
        try:
            with socket.create_connection((host, port), timeout=2):
                return True, False
        except Exception:
            pass
        time.sleep(interval)
    return False, proc.poll() is not None


class DevStackLauncher:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.processes: List[subprocess.Popen] = []
        self.service_processes: Dict[str, subprocess.Popen] = {}
        self.threads: List[threading.Thread] = []
        self._shutdown = False
        self.active_uproject_path: Optional[Path] = None
        self.active_uproject_materialized = False

    def start_surrealdb(self) -> bool:
        exe = resolve_surrealdb_exe()
        if not exe:
            log("SurrealDB", f"{Style.RED}executable not found. Install surreal or place surreal.exe in repo root.{Style.RESET}")
            return False

        db_dir = REPO_ROOT / ".surreal"
        db_dir.mkdir(exist_ok=True)
        db_path = db_dir / "unreal_mcp.db"

        cmd = [
            str(exe),
            "start",
            "--bind",
            self.args.surreal_bind,
            "--user",
            "root",
            "--pass",
            "secret",
            f"rocksdb://{db_path}" if not self.args.surreal_memory else "memory",
        ]

        log("SurrealDB", f"Starting: {Style.DIM}{' '.join(cmd)}{Style.RESET}", Style.CYAN)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(REPO_ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        self.processes.append(proc)
        self.service_processes["surreal"] = proc
        t = threading.Thread(target=stream_output, args=(proc, "SurrealDB", Style.CYAN), daemon=True)
        t.start()
        self.threads.append(t)

        health_url = f"http://{self.args.surreal_bind}/health"
        log("SurrealDB", f"Waiting for {health_url} ...", Style.CYAN)
        if wait_for_service(health_url, timeout=10.0):
            log("SurrealDB", f"{Style.GREEN}Ready{Style.RESET}", Style.CYAN)
            return True
        else:
            log("SurrealDB", f"{Style.YELLOW}Health check timed out; proceeding anyway{Style.RESET}", Style.CYAN)
            return True

    def start_scene_syncd(self) -> bool:
        exe = resolve_scene_syncd_exe()
        if exe:
            cmd = [str(exe)]
            cwd = str(exe.parent)
        else:
            # Fallback: cargo run
            cargo = "cargo"
            if sys.platform == "win32":
                # Try to find cargo in typical rustup location
                cargo_path = Path.home() / ".cargo" / "bin" / "cargo.exe"
                if cargo_path.exists():
                    cargo = str(cargo_path)
            cmd = [cargo, "run"]
            cwd = str(RUST_ROOT)
            log("scene-syncd", f"{Style.YELLOW}Binary not found; using 'cargo run' (slower startup){Style.RESET}", Style.BLUE)

        env = os.environ.copy()
        env.setdefault("SCENE_SYNCD_HOST", "127.0.0.1")
        env.setdefault("SCENE_SYNCD_PORT", "8787")
        env.setdefault("SURREAL_URL", f"ws://{self.args.surreal_bind}")
        env.setdefault("SURREAL_NS", "unreal_mcp")
        env.setdefault("SURREAL_DB", "scene")
        env.setdefault("SURREAL_USER", "root")
        env.setdefault("SURREAL_PASS", "secret")
        env.setdefault("UNREAL_MCP_HOST", DEFAULT_UNREAL_HOST)
        env.setdefault("UNREAL_MCP_PORT", str(DEFAULT_UNREAL_PORT))
        env.setdefault("SCENE_SYNCD_AUTOSYNC", "false")
        env.setdefault("SCENE_SYNCD_LOG", "info")

        log("scene-syncd", f"Starting on {env['SCENE_SYNCD_HOST']}:{env['SCENE_SYNCD_PORT']}", Style.BLUE)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        self.processes.append(proc)
        self.service_processes["scene_syncd"] = proc
        t = threading.Thread(target=stream_output, args=(proc, "scene-syncd", Style.BLUE), daemon=True)
        t.start()
        self.threads.append(t)

        health_url = f"{DEFAULT_SCENE_SYNCD_URL}/health"
        log("scene-syncd", f"Waiting for {health_url} ...", Style.BLUE)
        if wait_for_service(health_url, timeout=30.0):
            log("scene-syncd", f"{Style.GREEN}Ready{Style.RESET}", Style.BLUE)
            return True
        else:
            log("scene-syncd", f"{Style.YELLOW}Health check timed out; proceeding anyway{Style.RESET}", Style.BLUE)
            return True

    def start_unreal(self) -> bool:
        ue_root = resolve_unreal_engine_root()
        if not ue_root:
            log("Unreal", f"{Style.RED}Engine not found. Set UNREAL_ENGINE_ROOT or install UE 5.7+{Style.RESET}")
            return False

        editor_exe = ue_root / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
        if sys.platform != "win32":
            editor_exe = ue_root / "Engine" / "Binaries" / "Mac" / "UnrealEditor"
        if not editor_exe.exists():
            log("Unreal", f"{Style.RED}Editor not found at {editor_exe}{Style.RESET}")
            return False

        requested_uproject = resolve_requested_uproject(self.args)
        if not requested_uproject.exists():
            log("Unreal", f"{Style.RED}.uproject not found at {requested_uproject}{Style.RESET}")
            return False

        try:
            if getattr(self.args, "no_materialize_mcp_project", False):
                active_uproject = requested_uproject
            else:
                active_uproject, link_mode = materialize_mcp_project(requested_uproject)
                if active_uproject != requested_uproject:
                    self.active_uproject_materialized = True
                    log(
                        "Unreal",
                        (
                            f"Materialized MCP project from {requested_uproject} "
                            f"using {ROOT_PLUGIN_PATH} ({link_mode})"
                        ),
                        Style.MAGENTA,
                    )
            self.active_uproject_path = active_uproject
        except Exception as exc:
            log("Unreal", f"{Style.RED}Failed to prepare MCP project: {exc}{Style.RESET}")
            return False

        if self.active_uproject_materialized and not getattr(self.args, "skip_unreal_build", False):
            if not self.build_unreal_project(ue_root, active_uproject):
                return False

        cmd = [
            str(editor_exe),
            str(active_uproject),
            "-Windowed",
            "-ResX=1280",
            "-ResY=720",
        ]
        
        if getattr(self.args, "headless", False):
            cmd.append("-NullRHI")
        
        if getattr(self.args, "render_offscreen", False):
            cmd.append("-RenderOffScreen")

        log("Unreal", f"Starting: {Style.DIM}{editor_exe.name} {active_uproject.name}{Style.RESET}", Style.MAGENTA)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(REPO_ROOT),
            # Unreal Editor needs a window, so we don't use CREATE_NO_WINDOW here
            creationflags=0,
        )
        self.processes.append(proc)
        self.service_processes["unreal"] = proc
        t = threading.Thread(target=stream_output, args=(proc, "Unreal", Style.MAGENTA), daemon=True)
        t.start()
        self.threads.append(t)

        log("Unreal", f"Waiting for TCP {DEFAULT_UNREAL_HOST}:{DEFAULT_UNREAL_PORT} ...", Style.MAGENTA)
        ready, exited = wait_for_tcp_or_process_exit(DEFAULT_UNREAL_HOST, DEFAULT_UNREAL_PORT, proc, timeout=120.0)
        if ready:
            log("Unreal", f"{Style.GREEN}Ready{Style.RESET}", Style.MAGENTA)
            return True
        elif exited:
            log("Unreal", f"{Style.RED}Editor exited before MCP TCP became ready (code {proc.returncode}){Style.RESET}", Style.MAGENTA)
            return False
        else:
            log("Unreal", f"{Style.YELLOW}TCP probe timed out; editor may still be loading{Style.RESET}", Style.MAGENTA)
            return True

    def build_unreal_project(self, ue_root: Path, uproject_path: Path) -> bool:
        """Run an incremental UBT build so source project plugins are loadable."""
        if sys.platform != "win32":
            return True

        build_bat = ue_root / "Engine" / "Build" / "BatchFiles" / "Build.bat"
        if not build_bat.exists():
            log("Unreal", f"{Style.RED}Build.bat not found at {build_bat}{Style.RESET}")
            return False

        target = f"{uproject_path.stem}Editor"
        cmd = [
            str(build_bat),
            target,
            "Win64",
            "Development",
            f"-Project={uproject_path}",
            "-WaitMutex",
            "-NoHotReloadFromIDE",
        ]
        log("Unreal", f"Building source plugin target: {Style.DIM}{target}{Style.RESET}", Style.MAGENTA)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(ue_root / "Engine" / "Build" / "BatchFiles"),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.processes.append(proc)
        t = threading.Thread(target=stream_output, args=(proc, "UBT", Style.MAGENTA), daemon=True)
        t.start()
        self.threads.append(t)
        return_code = proc.wait()
        if return_code != 0:
            log("Unreal", f"{Style.RED}UBT build failed with exit code {return_code}{Style.RESET}", Style.MAGENTA)
            return False
        log("Unreal", f"{Style.GREEN}UBT build succeeded{Style.RESET}", Style.MAGENTA)
        return True

    def start_mcp_server(self) -> bool:
        entry = PYTHON_ROOT / "unreal_mcp_server_advanced.py"
        if not entry.exists():
            log("MCP", f"{Style.RED}Server entry point not found: {entry}{Style.RESET}")
            return False

        # Prefer uv; fallback to python -m
        uv_exe = "uv"
        if sys.platform == "win32":
            uv_win = Path.home() / ".local" / "bin" / "uv.exe"
            if uv_win.exists():
                uv_exe = str(uv_win)

        # Check if uv is available
        uv_available = False
        try:
            result = subprocess.run([uv_exe, "--version"], capture_output=True, check=False)
            uv_available = result.returncode == 0
        except Exception:
            pass

        if uv_available:
            cmd = [uv_exe, "run", str(entry)]
            cwd = str(PYTHON_ROOT)
        else:
            cmd = [sys.executable, str(entry)]
            cwd = str(PYTHON_ROOT)

        log("MCP", f"Starting Python MCP server", Style.GREEN)
        # MCP server uses stdio transport; keep stdin open so it doesn't
        # exit immediately when there's no connected client.
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        self.processes.append(proc)
        self.service_processes["mcp_server"] = proc
        t = threading.Thread(target=stream_output, args=(proc, "MCP", Style.GREEN), daemon=True)
        t.start()
        self.threads.append(t)

        # MCP server uses stdio transport; just give it a moment
        time.sleep(2.0)
        if proc.poll() is None:
            log("MCP", f"{Style.GREEN}Running (stdio transport){Style.RESET}", Style.GREEN)
            return True
        else:
            log("MCP", f"{Style.RED}Process exited early (code {proc.returncode}){Style.RESET}", Style.GREEN)
            return False

    def shutdown(self, signum=None, frame=None) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        print(f"\n{Style.YELLOW}{Style.BOLD}Shutting down development stack...{Style.RESET}")
        self.stop_processes()
        print(f"{Style.GREEN}{Style.BOLD}All services stopped.{Style.RESET}")
        sys.exit(0)

    def stop_processes(self) -> None:
        for proc in self.processes:
            if proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass

        # Wait a bit, then kill if needed
        time.sleep(2.0)
        for proc in self.processes:
            if proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass

    def verify_stack(self) -> Dict[str, object]:
        """Return a finite full-stack verification summary."""
        summary: Dict[str, object] = {
            "surreal_requested": bool(self.args.surreal),
            "scene_syncd_requested": bool(self.args.scene_syncd),
            "unreal_requested": bool(self.args.unreal),
            "mcp_server_requested": bool(self.args.mcp_server),
            "uproject": str(self.active_uproject_path) if self.active_uproject_path else None,
            "surreal_health": None,
            "scene_syncd_health": None,
            "unreal_tcp": None,
            "mcp_server_running": None,
        }
        if self.args.surreal:
            summary["surreal_health"] = wait_for_service(f"http://{self.args.surreal_bind}/health", timeout=3.0, interval=0.25)
        if self.args.scene_syncd:
            summary["scene_syncd_health"] = wait_for_service(f"{DEFAULT_SCENE_SYNCD_URL}/health", timeout=3.0, interval=0.25)
        if self.args.unreal:
            summary["unreal_tcp"] = wait_for_tcp(DEFAULT_UNREAL_HOST, DEFAULT_UNREAL_PORT, timeout=5.0, interval=0.5)
        if self.args.mcp_server:
            proc = self.service_processes.get("mcp_server")
            summary["mcp_server_running"] = bool(proc and proc.poll() is None)
        requested_checks = [
            value
            for key, value in summary.items()
            if key.endswith("_health") or key in {"unreal_tcp", "mcp_server_running"}
            if value is not None
        ]
        summary["passed"] = bool(requested_checks) and all(bool(value) for value in requested_checks)
        return summary

    def run(self) -> int:
        signal.signal(signal.SIGINT, self.shutdown)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, self.shutdown)

        log("Launcher", f"{Style.BOLD}Repo root:{Style.RESET} {REPO_ROOT}", Style.YELLOW)

        ok = True
        if self.args.surreal:
            ok = self.start_surrealdb() and ok
        if self.args.scene_syncd:
            ok = self.start_scene_syncd() and ok
        if self.args.unreal:
            ok = self.start_unreal() and ok
        if self.args.mcp_server:
            ok = self.start_mcp_server() and ok

        if not ok:
            log("Launcher", f"{Style.RED}Some services failed to start. Shutting down.{Style.RESET}", Style.YELLOW)
            self.shutdown()
            return 1

        print(f"\n{Style.GREEN}{Style.BOLD}Development stack is running!{Style.RESET}")
        print(f"{Style.DIM}Press Ctrl+C to stop all services.{Style.RESET}\n")

        if getattr(self.args, "verify", False):
            hold = max(0.0, float(getattr(self.args, "verify_hold_seconds", 2.0)))
            if hold:
                time.sleep(hold)
            summary = self.verify_stack()
            print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
            self.stop_processes()
            return 0 if summary.get("passed") else 1

        # Keep main thread alive
        try:
            while True:
                time.sleep(1.0)
                # Check if any process died unexpectedly
                for proc in self.processes:
                    if proc.poll() is not None and proc.returncode not in (0, -15, -9):
                        log("Launcher", f"{Style.RED}Process exited unexpectedly (code {proc.returncode}){Style.RESET}", Style.YELLOW)
        except KeyboardInterrupt:
            self.shutdown()

        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the full Unreal MCP development stack")
    parser.add_argument("--all", action="store_true", help="Start all services (default)")
    parser.add_argument("--surreal", action="store_true", help="Start SurrealDB")
    parser.add_argument("--scene-syncd", action="store_true", help="Start scene-syncd")
    parser.add_argument("--unreal", action="store_true", help="Start Unreal Editor")
    parser.add_argument("--mcp-server", action="store_true", help="Start Python MCP server")
    parser.add_argument("--surreal-memory", action="store_true", help="Use in-memory SurrealDB instead of rocksdb")
    parser.add_argument("--surreal-bind", default=DEFAULT_SURREAL_BIND, help=f"SurrealDB bind address (default: {DEFAULT_SURREAL_BIND})")
    parser.add_argument("--headless", action="store_true", help="Run Unreal Engine in headless mode (no window)")
    parser.add_argument("--render-offscreen", action="store_true", help="Use -RenderOffScreen for Unreal Engine")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup ports (55771, 8787, 8000) before starting")
    parser.add_argument("--uproject", help="Path to a .uproject to launch; overrides UNREAL_MCP_UPROJECT")
    parser.add_argument(
        "--no-materialize-mcp-project",
        action="store_true",
        help="Launch the selected .uproject directly without linking/enabling the repo UnrealMCP plugin",
    )
    parser.add_argument(
        "--skip-unreal-build",
        action="store_true",
        help="Skip the incremental UBT build for a materialized source-plugin project",
    )
    parser.add_argument("--verify", action="store_true", help="Run finite health/TCP checks after startup, then stop services")
    parser.add_argument("--verify-hold-seconds", type=float, default=2.0, help="Seconds to keep services alive before --verify checks")
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Default to --all if no service flags given
    if not any([args.all, args.surreal, args.scene_syncd, args.unreal, args.mcp_server]):
        args.all = True

    if args.all:
        args.surreal = True
        args.scene_syncd = True
        args.unreal = True
        args.mcp_server = True

    if getattr(args, "cleanup", False):
        log("Launcher", "Cleaning up ports before start...", Style.YELLOW)
        cleanup_script = REPO_ROOT / "scripts" / "cleanup-ports.py"
        if cleanup_script.exists():
            subprocess.run([sys.executable, str(cleanup_script)], check=False)
        else:
            log("Launcher", f"{Style.RED}Cleanup script not found at {cleanup_script}{Style.RESET}")

    launcher = DevStackLauncher(args)
    return launcher.run()


if __name__ == "__main__":
    sys.exit(main())

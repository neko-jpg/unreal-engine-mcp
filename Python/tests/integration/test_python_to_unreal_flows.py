from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_PATH = REPO_ROOT.parent / "FlopperamUnrealMCP" / "FlopperamUnrealMCP.uproject"
DEFAULT_ENGINE_ROOT = Path(r"C:\Program Files\Epic Games\UE_5.7")
EDITOR_CMD = "UnrealEditor-Cmd.exe"
UNREAL_HOST = "127.0.0.1"
UNREAL_PORT = 55557


def _engine_root() -> Path:
    return Path(os.environ.get("UNREAL_ENGINE_ROOT", DEFAULT_ENGINE_ROOT))


def _editor_executable() -> Path:
    return _engine_root() / "Engine" / "Binaries" / "Win64" / EDITOR_CMD


def _socket_is_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def unreal_editor_process():
    editor_exe = _editor_executable()
    if not editor_exe.exists():
        pytest.skip(f"Unreal editor executable was not found at {editor_exe}")

    args = [
        str(editor_exe),
        str(PROJECT_PATH),
        "-unattended",
        "-nop4",
        "-nosplash",
        "-NoSound",
        "-nullrhi",
        "-log",
    ]

    log_dir = REPO_ROOT.parent / "FlopperamUnrealMCP" / "Saved" / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / "pytest-unreal-editor.stdout.log"
    stderr_path = log_dir / "pytest-unreal-editor.stderr.log"
    stdout_file = stdout_path.open("wb")
    stderr_file = stderr_path.open("wb")
    stdin_file = open(os.devnull, "rb")

    try:
        process = subprocess.Popen(args, stdin=stdin_file, stdout=stdout_file, stderr=stderr_file)
    except OSError as exc:
        stdin_file.close()
        stdout_file.close()
        stderr_file.close()
        pytest.skip(f"Unreal Editor could not be started in this environment: {exc}")

    deadline = time.time() + 180
    while time.time() < deadline:
        if _socket_is_open(UNREAL_HOST, UNREAL_PORT):
            break
        if process.poll() is not None:
            pytest.fail("Unreal Editor exited before the MCP socket became available")
        time.sleep(2)
    else:
        process.terminate()
        pytest.fail("Timed out waiting for the Unreal MCP socket")

    yield process

    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
    stdin_file.close()
    stdout_file.close()
    stderr_file.close()


@pytest.fixture
def server_module():
    sys.path.insert(0, str(REPO_ROOT))
    import unreal_mcp_server_advanced as server

    server.reset_unreal_connection()
    yield server
    server.reset_unreal_connection()


def test_actor_lifecycle_flow(unreal_editor_process, server_module):
    actor_name = f"MCPPyActor_{uuid4().hex[:8]}"

    spawn_result = server_module.spawn_actor("StaticMeshActor", actor_name, location=[0, 0, 100])
    assert spawn_result["status"] == "success"

    transform_result = server_module.set_actor_transform(
        actor_name,
        location=[100, 200, 300],
        rotation=[0, 45, 0],
        scale=[1.25, 1.25, 1.25],
    )
    assert transform_result["status"] == "success"

    find_result = server_module.find_actors_by_name(actor_name)
    assert find_result["status"] == "success"
    assert any(actor["name"] == actor_name for actor in find_result["result"]["actors"])

    delete_result = server_module.delete_actor(actor_name)
    assert delete_result["status"] == "success"


def test_blueprint_graph_flow(unreal_editor_process, server_module):
    blueprint_name = f"MCPPyBlueprint_{uuid4().hex[:8]}"

    create_bp = server_module.create_blueprint(blueprint_name, parent_class="Actor")
    assert create_bp["status"] == "success"

    create_var = server_module.create_variable(
        blueprint_name,
        "Health",
        variable_type="float",
        default_value=100.0,
    )
    assert create_var["success"] is True

    create_function = server_module.create_function(blueprint_name, "ApplyDamage")
    assert create_function["success"] is True

    add_event = server_module.add_event_node(
        blueprint_name,
        event_name="ReceiveBeginPlay",
    )
    assert add_event["success"] is True

    add_print = server_module.add_node(
        blueprint_name,
        "Print",
        pos_x=300,
        pos_y=0,
        message="Integration",
    )
    assert add_print["success"] is True

    connect = server_module.connect_nodes(
        blueprint_name,
        add_event["node_id"],
        "then",
        add_print["node_id"],
        "execute",
    )
    assert connect["success"] is True

    analysis = server_module.analyze_blueprint_graph(blueprint_name)
    assert analysis["status"] == "success"


def test_blueprint_physics_actor_flow(unreal_editor_process, server_module):
    actor_name = f"MCPPhysicsActor_{uuid4().hex[:8]}"

    spawn_result = server_module.spawn_physics_blueprint_actor(
        actor_name,
        location=[0, 0, 150],
        mass=100.0,
        simulate_physics=True,
    )
    assert spawn_result["status"] == "success"

    delete_result = server_module.delete_actor(actor_name)
    assert delete_result["status"] == "success"

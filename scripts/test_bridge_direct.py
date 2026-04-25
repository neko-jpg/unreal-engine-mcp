#!/usr/bin/env python3
"""
Direct TCP test of the Unreal MCP bridge.
Usage: python test_bridge_direct.py
"""
import json, socket, sys

def send_command(host: str, port: int, command: str, params: dict) -> dict:
    payload = json.dumps({"command": command, "params": params}) + "\n"
    payload_bytes = payload.encode("utf-8")
    with socket.create_connection((host, port), timeout=10) as s:
        s.settimeout(30)
        s.sendall(payload_bytes)
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(8192)
            if not chunk:
                break
            buf += chunk
        line = buf.split(b"\n", 1)[0]
        return json.loads(line.decode("utf-8"))

HOST = "127.0.0.1"
PORT = 55557

def main():
    print(f"Connecting to {HOST}:{PORT} ...")
    try:
        r = send_command(HOST, PORT, "ping", {})
        print("ping =>", json.dumps(r, ensure_ascii=False, indent=2))
    except Exception as e:
        print("ping FAILED:", e)
        sys.exit(1)

    print("\n--- get_actors_in_level ---")
    r = send_command(HOST, PORT, "get_actors_in_level", {})
    actors = r.get("result", {}).get("actors", [])
    print(f"actors count: {len(actors)}")
    for a in actors:
        if a.get("name") == "TestCube_01":
            print("\nTestCube_01 details:")
            print(json.dumps(a, ensure_ascii=False, indent=2))

    print("\n--- find_actor_by_mcp_id test_mcp_001 (should fail if not exist) ---")
    r = send_command(HOST, PORT, "find_actor_by_mcp_id", {"mcp_id": "test_mcp_001"})
    print(json.dumps(r, ensure_ascii=False, indent=2))

    print("\n--- spawn_actor with mcp_id ---")
    r = send_command(HOST, PORT, "spawn_actor", {
        "name": "McpTestCube",
        "type": "StaticMeshActor",
        "mcp_id": "test_mcp_001",
        "location": [0, 0, 200],
        "rotation": [0, 0, 0],
        "scale": [1, 1, 1],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        "tags": ["managed_by_mcp", "mcp_id:test_mcp_001"]
    })
    print(json.dumps(r, ensure_ascii=False, indent=2))

    print("\n--- find_actor_by_mcp_id after spawn ---")
    r = send_command(HOST, PORT, "find_actor_by_mcp_id", {"mcp_id": "test_mcp_001"})
    print(json.dumps(r, ensure_ascii=False, indent=2))

    print("\n--- get_actors_in_level after spawn ---")
    r = send_command(HOST, PORT, "get_actors_in_level", {})
    actors = r.get("result", {}).get("actors", [])
    found = [a for a in actors if a.get("name") == "McpTestCube" or "mcp_id:test_mcp_001" in a.get("tags", [])]
    if found:
        print("Found:", json.dumps(found[0], ensure_ascii=False, indent=2))
    else:
        print("WARNING: actor not found in level listing")

if __name__ == "__main__":
    main()

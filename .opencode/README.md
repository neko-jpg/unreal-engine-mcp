# OpenCode MCP Configuration

This folder contains configuration for using the Unreal MCP server with [OpenCode](https://opencode.ai).

## Setup

1. **Install prerequisites**
   - Python 3.10+
   - A Python environment with this repository's MCP dependencies installed. The checked-out development environment uses `Python/.venv/Scripts/python.exe`.
   - [uv](https://github.com/astral-sh/uv) if you need to create or refresh the environment
   - Unreal Engine 5.5+ with the `UnrealMCP` plugin enabled

2. **Configure OpenCode**

   OpenCode reads project-local config from `.opencode/opencode.jsonc` when it is started from this repository. This folder already contains that file.

   For a global setup, copy the `mcp` object from `mcp.json` into your existing OpenCode config file:

   - **Windows**: `%USERPROFILE%\.config\opencode\opencode.jsonc`
   - **macOS/Linux**: `~/.config/opencode/opencode.jsonc`

   Current OpenCode versions require MCP servers under the top-level `mcp` key, not `mcpServers`.

3. **Verify connection**

   Start Unreal Editor with the plugin enabled, then run:

   ```powershell
   opencode mcp list
   ```

   The `unreal-engine-mcp` server should show as **connected**.

## Configuration Details

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "unreal-engine-mcp": {
      "type": "local",
      "command": [
        "Python/.venv/Scripts/python.exe",
        "Python/unreal_mcp_server_advanced.py"
      ],
      "environment": {
        "UNREAL_MCP_HOST": "127.0.0.1",
        "UNREAL_MCP_PORT": "55557"
      },
      "enabled": true
    }
  }
}
```

## Project Slash Commands

This folder also defines project-local OpenCode slash commands in `.opencode/commands/`.
Restart OpenCode after changing command files.

Common scene database commands:

```text
/scene-doctor
/scenectl doctor
/scene-list --scene castle_crown_064013 --tag white_castle_crown
/scene-plan castle_crown_064013
/scene-apply castle_crown_064013
/scene-delete-dry-run --scene castle_crown_064013 --tag white_castle_crown
```

Use `/scenectl ...` for the full CLI surface. It passes arguments to:

```powershell
scenectl ...
```

`/scene-apply` applies changes to Unreal and intentionally passes `--yes`; run `/scene-plan` first.

### Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `UNREAL_MCP_HOST` | `127.0.0.1` | TCP host where the UE plugin is listening |
| `UNREAL_MCP_PORT` | `55557` | TCP port for the UE plugin |

If you run multiple Editor instances or changed the plugin port in **Project Settings > Plugins > Unreal MCP**, update these values accordingly.

### With `uv`

If you prefer `uv`, replace the local server command with:

```json
{
  "type": "local",
  "command": [
    "uv",
    "--directory",
    "Python",
    "run",
    "unreal_mcp_server_advanced.py"
  ],
  "environment": {
    "UNREAL_MCP_HOST": "127.0.0.1",
    "UNREAL_MCP_PORT": "55557"
  },
  "enabled": true
}
```

## Troubleshooting

- **"Connection refused"** - Make sure the Unreal Editor is running with the `UnrealMCP` plugin enabled.
- **Timeout on large operations** - The server auto-detects heavy commands (town/castle generation, material scanning) and extends recv timeout to 300s.
- **Tool count mismatch** - The advanced server currently exposes 57 tools. If OpenCode shows fewer, check `unreal_mcp_server_advanced.py` registers all intended tool modules.

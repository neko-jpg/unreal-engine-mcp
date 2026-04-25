# 13. scenectl CLI

`scripts/scenectl.py` is the first command-line client for the scene database workflow.
It is intentionally a thin client over `scene-syncd`; it does not write SurrealDB records directly.

## Design Role

```text
scenectl -> scene-syncd HTTP API -> SurrealDB
scenectl -> Unreal MCP TCP bridge for diagnostics only
```

This keeps `scene-syncd` as the source-of-truth API boundary. Future Web UI, editor widgets, and AI agents should use the same API contract rather than duplicating database access.

## Common Commands

Run from the repository root:

```cmd
scenectl doctor
scenectl start
scenectl stop
```

The Windows `scenectl.cmd` wrapper delegates to `python scripts/scenectl.py`.
If the repository root is not the current directory, either run from the root or add the repository root to `PATH`.

Running `scenectl` with no arguments starts an interactive shell:

```cmd
C:\development\unreal-engine-mcp> scenectl
scenectl interactive shell
Scene DB -> scene-syncd -> Unreal operations. Type '/help' or '/exit'.
scenectl> /help
scenectl> /doctor
scenectl> /object list --scene castle_crown_064013 --tag white_castle_crown
scenectl> /exit
```

The interactive shell supports ANSI color output, `/help`, `/help <command>`, `/clear`, `/exit`, and `/quit`.
On Windows terminals, typing `/` shows command candidates immediately; pressing `Tab` after a partial slash command shows matching candidates again.
Set `NO_COLOR=1` to disable color.

The direct Python form also works:

```powershell
python scripts/scenectl.py doctor
python scripts/scenectl.py start
python scripts/scenectl.py stop
```

## OpenCode Slash Commands

Project-local OpenCode commands are defined in `.opencode/commands/`.
Restart OpenCode after adding or changing command files, then use:

```text
/scene-doctor
/scenectl doctor
/scenectl object list --scene castle_crown_064013 --tag white_castle_crown
/scene-list --scene castle_crown_064013 --tag white_castle_crown
/scene-plan castle_crown_064013
/scene-apply castle_crown_064013
/scene-delete-dry-run --scene castle_crown_064013 --tag white_castle_crown
```

`/scene-apply` intentionally passes `--yes`, so run `/scene-plan` first.
For destructive deletes, use `/scene-delete-dry-run` first, then run the explicit generic form when ready:

```text
/scenectl object delete --scene castle_crown_064013 --tag white_castle_crown --yes
/scenectl apply --scene castle_crown_064013 --allow-delete --yes
```

Create a scene:

```powershell
scenectl scene create my_scene --name "My Scene"
```

List desired objects:

```powershell
scenectl object list --scene castle_crown_064013
scenectl object list --scene castle_crown_064013 --tag white_castle_crown
scenectl object list --scene castle_crown_064013 --group white_castle_crown
scenectl object list --scene castle_crown_064013 --changed
```

Manage tags:

```powershell
scenectl object tag --scene castle_crown_064013 --group white_castle_crown add white_castle_crown huge_visible_test --yes
scenectl object tag --scene castle_crown_064013 --mcp-id castle_crown_064013_beacon_center remove huge_visible_test
```

Preview and apply sync:

```powershell
scenectl plan --scene castle_crown_064013
scenectl apply --scene castle_crown_064013 --yes
```

Preview delete by tag:

```powershell
scenectl object delete --scene castle_crown_064013 --tag white_castle_crown --dry-run
```

Tombstone and apply deletion:

```powershell
scenectl object delete --scene castle_crown_064013 --tag white_castle_crown --yes
scenectl apply --scene castle_crown_064013 --allow-delete --yes
```

## Safety Rules

- `apply` requires `--yes`.
- `object delete` without `--yes` prints a dry-run style target list and exits without writing.
- `object delete --dry-run` never writes.
- Multi-object tag updates require `--yes`.
- Use `--json` on most commands for machine-readable output suitable for AI tooling.

## Current Limits

- `start` and `stop` are local Windows-oriented helpers for this repository layout.
- The CLI currently relies on `scene-syncd` list endpoints and filters client-side.
- Material and visual apply operations are still limited by `scene-syncd` Phase 4 support.
- `doctor` opens direct Unreal TCP connections and may report transient bridge failures if Unreal is busy.

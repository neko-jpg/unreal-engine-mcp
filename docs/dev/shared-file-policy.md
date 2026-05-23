# Shared-file policy (234-stubs Waves 1-5)

234-stubs Wave 0.5 follow-up (umbrella: #69).

Wave 1-5 work involves up to 4 category PRs landing per week. To keep
merges friction-free we mark a small set of files as "shared":
**category PRs must not edit them.** The reviewer/integrator folds in
changes via a daily merge PR or the per-wave close PR.

## Shared files (do not edit from a category PR)

| File | Why it is shared |
|---|---|
| `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPRouter.cpp` | Single TMap with 700+ entries; any addition collides with every other category PR. |
| `Plugins/UnrealMCP/Source/UnrealMCP/Private/EpicUnrealMCPBridge.cpp` | Owns the handler-class registry; every new `*Commands` class touches it. |
| `scripts/live_e2e_smoke.py` | Single `WAVE_GROUPS` dict + `CASES` list shared by every wave. |
| `CHANGELOG.md` | 100+ KiB file; serializing PRs through it is slow. Use `CHANGELOG.d/` fragments. |
| `artifacts/queued_baseline.json` | Lowered only by wave-close PRs (via `scripts/audit_no_new_queued.py --update-baseline`). |

## How category PRs land changes that would touch a shared file

1. **Router.cpp / Bridge.cpp**
   - Add the new handler under the *existing* `F<Cat>Commands` class. The
     router already maps the command name to a numeric bucket; if a brand-new
     command is introduced, add it to the PR description's *Router entries*
     section and leave the actual edit to the reviewer/integrator.

2. **live_e2e_smoke.py**
   - Add the new `case_<name>` function in a small standalone file under
     `scripts/live_e2e_smoke_cases/<wave>_<category>.py` (created on demand)
     and import it from the runner via the next wave-close PR. Smoke cases
     that block a single PR's verification can be run locally with
     `python scripts/live_e2e_smoke.py --only <case>` (the reviewer wires
     it into the dispatch dict at fold-in time).

3. **CHANGELOG.md**
   - Always drop a fragment in `CHANGELOG.d/` (see that directory's
     `README.md`).

4. **artifacts/queued_baseline.json**
   - Never lower from a category PR. `scripts/audit_no_new_queued.py` will
     refuse to merge such a PR with a regression. The wave-close PR is the
     only place that runs `--update-baseline`.

## Conflict resolution

If two category PRs land within minutes of each other and rebase noise
appears on a shared file, **stop merging** and let the
reviewer/integrator land a rebase commit first. Do **not** force-push a
category branch with shared-file edits to "fix" the conflict.

## Categories and owners

See `docs/implementation-plan-234-stubs.md` for the per-wave / per-category
ownership table.

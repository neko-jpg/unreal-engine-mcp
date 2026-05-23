<!--
234-stubs Wave 0.5 follow-up (umbrella: #69).

If this PR promotes any stub handler to executed:true, keep the
sections below. The agents-md-pr-check workflow will fail the PR if
"## Scope reconciliation", "## UE 5.7 API research", or "## Tests" is
missing while the `stub-impl` label is applied.

For non-stub PRs (docs only, CI tweak, etc.) you can replace the
template with a single short paragraph.
-->

Refs #<issue>
<!-- or, for the final PR that finishes a category: Closes #<issue> -->

## Scope reconciliation

- Issue checklist count:
- Existing `queued:true` count (this PR before):
- Already `executed:true` count:
- Promoted in this PR:
- Notes on shallow real-impl vs full promotion:

## UE 5.7 API research

- Search terms (e.g. `web_search "UPCGGraph 5.7"`):
- Official docs / headers checked:
- Deprecated APIs avoided (must include `UpdateDefaultConfigFile()` if relevant):
- Config persistence decision (`TryUpdateDefaultConfigFileSafe` / N/A):
- Module gate(s) used (`WITH_<MODULE>_MCP`):

## Handlers promoted

- [ ] handler_a
- [ ] handler_b

## Tests

- Unit: `pytest Python/tests/unit -q`
- Contract: `pytest Python/tests/contract -q`
- Route audit: `python scripts/audit_route_contracts.py --strict`
- Queued audit: `python scripts/audit_no_new_queued.py`
- Live smoke (if applicable): `python scripts/live_e2e_smoke.py --only <case>`
- Local RunUAT or CI RunUAT: `pwsh -File scripts/run_local_uat_buildplugin.ps1`
- Log artifact path:

## CHANGELOG

- Fragment: `CHANGELOG.d/<wave>-<category>-<slug>.md`
- (Do not edit `CHANGELOG.md` directly.)

## Router / Bridge / live_e2e_smoke notes

<!--
If this PR needs a new entry in EpicUnrealMCPRouter.cpp,
EpicUnrealMCPBridge.cpp, or scripts/live_e2e_smoke.py, list the
desired entries here so the reviewer/integrator can fold them in via
the wave-close PR. Do not edit these shared files from a category PR.
See docs/dev/shared-file-policy.md.
-->

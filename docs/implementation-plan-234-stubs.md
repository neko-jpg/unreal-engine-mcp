# 234-Stubs → UE 5.7 Full Implementation Plan

> Umbrella tracker: `neko-jpg/unreal-engine-mcp#69`
> Compliance: `AGENTS.md` (UE 5.7 only, `TryUpdateDefaultConfigFile()`, no LLM-guessed APIs)
> Build target: UE 5.7 / Win64 / Development Editor
> Scope: `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/*.cpp`

This document is the durable source of truth for converting the **234 declared
stub / queued-only handlers** (275 when including `IsModuleAvailable`-gated
"shallow real-impl" handlers) into real UE 5.7 implementations.

## 0. Definitions

A handler is a **stub** when *any* of the following hold:

1. It calls a per-class `MakeUnavailable("<cmd>")` helper (the canonical pattern
   added in Phase 3 to keep the bridge compilable when an optional module is
   missing). Sample (current `MakeUnavailable` callers, one per category):
   - `FEpicUnrealMCPAiNavExtensionCommands::MakeUnavailable`
   - `FEpicUnrealMCPChaosCommands::MakeUnavailable`
   - `FEpicUnrealMCPDataTableExtensionCommands::MakeUnavailable`
   - `FEpicUnrealMCPFoliageCommands::MakeUnavailable`
   - `FEpicUnrealMCPGASCommands::MakeUnavailable`
   - `FEpicUnrealMCPLocalizationCommands::MakeUnavailable`
   - `FEpicUnrealMCPMetaSoundCommands::MakeUnavailable`
   - `FEpicUnrealMCPMobileXrCommands::MakeUnavailable`
   - `FEpicUnrealMCPMovieRenderQueueCommands::MakeUnavailable`
   - `FEpicUnrealMCPNetworkingCommands::MakeUnavailable`
   - `FEpicUnrealMCPPCGCommands::MakeUnavailable`
   - `FEpicUnrealMCPSequencerExtensionCommands::MakeUnavailable`
   - `FEpicUnrealMCPSourceControlCommands::MakeUnavailable`
   - `FEpicUnrealMCPTestingValidationCommands::MakeUnavailable`
   - `FEpicUnrealMCPWaterCommands::MakeUnavailable`
2. It sets `Data->SetBoolField(TEXT("queued"), true)` and returns without
   performing the underlying engine mutation. Current grep targets:
   - `EpicUnrealMCPAiNavExtensionCommands.cpp:38`
   - `EpicUnrealMCPGASCommands.cpp:140`
   - `EpicUnrealMCPNetworkingCommands.cpp:238`
   - plus all `Niagara/SetBoolField("queued", true)` paths that emit
     "asset dirtied" without an actual edit.
3. It returns "Payload accepted" / "MakeUnavailable" hints in
   `EpicUnrealMCPMobileXrCommands.cpp` (12 handlers across `Mobile/XR`).

## 1. Definition of Done — per handler

Each handler is "done" only when **all six** boxes are checked:

- [ ] No `MakeUnavailable` / `*Queued` / `"queued": true` field on the success
      path.  Use `*Unavailable` only as a real fallback (module truly missing).
- [ ] Returns `executed: true` together with a meaningful payload (asset path,
      created actor mcp_id, applied value, etc.).
- [ ] Wrapped in `FScopedTransaction` when it mutates editor-owned objects.
- [ ] No `UpdateDefaultConfigFile()` calls anywhere on the path; only
      `FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(Object)`.
- [ ] `Python/tests/unit/test_<module>_<handler>.py` covers the happy + error
      path with monkey-patched `get_unreal_connection`.
- [ ] `scripts/live_e2e_smoke.py --only <handler>` succeeds on a UE 5.7
      editor (validated locally, not just in CI).

## 2. Definition of Done — per wave

Each wave (W1..W5) is "shipped" only when:

- [ ] Every handler in the wave's category issues meets §1.
- [ ] `RunUAT BuildPlugin -Plugin=Plugins/UnrealMCP/UnrealMCP.uplugin` succeeds
      under both `-NoCompileChaos` (modules absent) and the full UE 5.7
      install (modules present).
- [ ] `pytest Python/tests/unit` is green; `pytest Python/tests/contract` is
      green; the `live_e2e_smoke.py` group for the wave passes.
- [ ] The roadmap issue for the wave (#78 / #83 / #88 / #93 / #98) is closed
      with a "Done" comment that links the merging PRs and lists residual
      `shallow real-impl` handlers that were promoted into full impls.

## 3. Foundation (Wave 0 / M5) — order of operations

The Wave 0 issues are interdependent. They must land in this order on one
branch so the rest of the waves can build on top:

| # | Issue | Why first |
|---|-------|-----------|
| 1 | #76 | This plan document — pinned source-of-truth for everyone. |
| 2 | #71 | `TryUpdateDefaultConfigFileSafe` + `FMCPScopedTransaction` RAII so every later handler can drop the legacy `UpdateDefaultConfigFile` call site in one mechanical sweep. |
| 3 | #70 | `UnrealMCP.Build.cs` optional-module gates so the wave 1–5 `*Commands.cpp` files compile against real headers when modules are present. |
| 4 | #72 | Python `assert_executed` + `assert_no_queued` envelope helpers so Wave 1+ tests can write a single `assert_executed(result, "<name>")` line instead of bespoke success checks. |
| 5 | #77 | Router-level "executed-or-error" contract: any handler that returns `success=true` without `executed=true` is converted to a structured `MCP-422` error (so we never silently regress to "queued"). |
| 6 | #75 | `scripts/live_e2e_smoke.py` grouping by wave + `--only / --skip` filters so Wave 1 reviewers can run only their slice. |
| 7 | #73 | `.github/workflows/ue57-build.yml` matrix workflow — gates plugin builds for every wave label. |
| 8 | #74 | `.github/workflows/python-tests.yml` expanded for the new unit tests. |

## 4. Wave 1 (M6) — Extend Existing (51 stubs)

| Category | Issue | Stubs | UE 5.7 module gate |
|---|---|---:|---|
| Animation Rigging | #79 | 20 | `WITH_CONTROLRIG_MCP` / `WITH_IKRIG_MCP` |
| Landscape | #80 | 22 | `WITH_LANDSCAPE_MCP` |
| Material | #81 | 2 | (already present, just promotion) |
| Niagara | #82 | 7 | `WITH_NIAGARA_MCP` |

**Strategy:** these categories already have working "shallow real-impl"
patterns (dirty + queued). For each, replace `queued: true` with the real
engine-side mutation (e.g. `Emitter->GetEmitterData()->...` for Niagara,
`LandscapeProxy->Modify(); LandscapeInfo->...` for Landscape, etc.) and add
the matching `FScopedTransaction`.

## 5. Wave 2 (M7) — Core Gameplay (54 stubs)

| Category | Issue | Stubs | UE 5.7 module gate |
|---|---|---:|---|
| AI / Navigation Extension | #84 | 23 | `AIModule` + `Navigation` + `StateTreeModule` |
| DataTable Extension | #85 | 9 | `Engine` only |
| GAS | #86 | 16 | `GameplayAbilities` + `GameplayTags` + `GameplayTasks` |
| Sequencer Extension | #87 | 6 | `Sequencer` + `LevelSequence` + `MovieScene` |

## 6. Wave 3 (M8) — World Building (74 stubs)

| Category | Issue | Stubs | UE 5.7 module gate |
|---|---|---:|---|
| Chaos Physics | #89 | 19 | `Chaos` + `GeometryCollectionEngine` + `ChaosCloth` + `ChaosVehicles` |
| Foliage | #90 | 20 | `Foliage` + `FoliageEdit` |
| PCG | #91 | 20 | `PCG` + `PCGEditor` |
| Water | #92 | 15 | `Water` + `WaterEditor` |

## 7. Wave 4 (M9) — Pipeline (65 stubs)

| Category | Issue | Stubs | UE 5.7 module gate |
|---|---|---:|---|
| Localization | #94 | 10 | `Localization` + `Internationalization` |
| Movie Render Queue | #95 | 21 | `MovieRenderPipelineCore` + `MovieGraph` |
| Networking | #96 | 21 | `OnlineSubsystem` + `NetCore` + `Iris` |
| Source Control | #97 | 13 | `SourceControl` + `SourceControlWindows` |

## 8. Wave 5 (M10) — Remainder (31 stubs)

| Category | Issue | Stubs | UE 5.7 module gate |
|---|---|---:|---|
| MetaSound | #99 | 7 | `MetasoundEngine` + `MetasoundFrontend` + `MetasoundEditor` |
| Mobile / XR | #100 | 14 | `XRBase` + `OpenXRHMD` + `AndroidPermission` |
| Testing / Validation | #101 | 10 | `AutomationController` + `AutomationTest` + `DataValidation` |

## 9. The "234 vs 275" reconciliation

The user-declared count of 234 is the number of handlers that **today** emit
`MakeUnavailable` or `queued: true` on every code path. The full extracted
count of 275 includes 41 handlers that already do real work when the optional
module is present but degrade to `MakeUnavailable` when the module is absent
(e.g. half of Niagara, Landscape, Animation Rigging). These 41 are tracked as
"polish" items in their respective category issues but **not** counted against
the headline 234 figure; the headline closes when 234 of them return
`executed: true` on at least one supported configuration.

## 10. Reference implementation skeleton (use this for every new handler)

```cpp
TSharedPtr<FJsonObject> F<Cat>Commands::Handle<Action>(const TSharedPtr<FJsonObject>& Params)
{
    if (!Is<Cat>Available()) return MakeUnavailable(TEXT("<command>"));

#if WITH_<MOD>_MCP
    // 1. Validate inputs (return CreateErrorResponse on failure).
    // 2. Resolve UObjects (asset / actor / component).
    // 3. FMCPScopedTransaction Tx(LOCTEXT(...));
    // 4. Object->Modify();
    //    perform the real UE 5.7 API call.
    // 5. If saving an .ini setting, call:
    //        FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(Object);
    //
    // 6. Build response:
    auto Data = MakeShared<FJsonObject>();
    Data->SetBoolField(TEXT("executed"), true);
    Data->SetStringField(TEXT("path"), Object->GetPathName());
    // ... domain-specific fields ...
    return MakeSuccessEnvelope(Data);
#else
    return MakeUnavailable(TEXT("<command>"));
#endif
}
```

## 11. Cross-cutting infrastructure that lands in Wave 0

These pieces live in the bridge and unblock every later wave:

- `FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(UObject*)`
  Single entry point for "persist editor-modified CDO to DefaultGame.ini".
  Internally calls `UObject::TryUpdateDefaultConfigFile()` and downgrades any
  failure to a structured warning (never throws).
- `FMCPScopedTransaction` (RAII wrapper around `FScopedTransaction`)
  Forces every `Object->Modify()` we add to live inside a transaction so the
  editor's Undo history is honoured.
- `Python.utils.envelope.assert_executed(result, command_name)`
  Single test-side assertion that enforces `executed=true` and surfaces the
  C++ `hint` field on failure.
- `scripts/live_e2e_smoke.py --group wave1` (and `--only`, `--skip`).
  Lets reviewers run only their wave slice on a real editor.
- `.github/workflows/ue57-build.yml` matrix and the expanded
  `.github/workflows/python-tests.yml` so PRs against a wave label get the
  right subset of checks.

## 12. Working-copy checklist for each PR

- [ ] Branch name: `codex/stubs-w<N>-<category>`
- [ ] Touches at most one Wave's category issue scope (no cross-wave leaks).
- [ ] `pytest Python/tests/unit` + `pytest Python/tests/contract` green.
- [ ] `scripts/audit_route_contracts.py` reports 0 new "queued" entries.
- [ ] `docs/implementation-plan-234-stubs.md` updated only if the plan
      itself changed (do **not** update it just to tick items — those go in
      the wave / category issue checklists).

## 13. Wave 0.5 follow-up infrastructure (delivered separately from #76)

The follow-up PR `codex/w0-followup-issue-resolution-infra` adds the
collision-avoidance and audit machinery that makes Waves 1-5
parallelisable across multiple worker agents. None of these files were
in scope for Wave 0 itself, but every Wave 1+ PR depends on them.

- `scripts/audit_no_new_queued.py` + `artifacts/queued_baseline.json`
  Promotes the legacy warn-only `queued: true` grep to a blocking
  audit. Run by `.github/workflows/queued-audit.yml`. Baseline is only
  lowered from a wave-close PR via `--update-baseline`.
- `scripts/run_local_uat_buildplugin.ps1`
  One-liner wrapper for `RunUAT BuildPlugin` that captures the log under
  `artifacts/local_uat/<timestamp>/runuat.log` so PR authors can quote a
  deterministic path in the PR description.
- `scripts/fold_changelog_fragments.py` + `CHANGELOG.d/`
  Lets every category PR drop a fragment instead of editing the
  100+ KiB `CHANGELOG.md` directly. The wave-close PR folds them into
  `## [Unreleased]` and removes the originals.
- `.github/labeler.yml` + `.github/workflows/labeler.yml`
  Apply `ue5.7-build`, `stub-impl`, and `stub-cat-<key>` automatically
  based on changed paths. `ue5.7-build` is required to trigger the
  self-hosted `RunUAT BuildPlugin` job in `ue57-build.yml`.
- `.github/workflows/agents-md-pr-check.yml`
  Fails the PR if the body of a `stub-impl` PR is missing
  `## Scope reconciliation`, `## UE 5.7 API research`, or `## Tests`.
  Mirrors the AGENTS.md mandate so reviewers do not have to enforce it
  manually.
- `.github/PULL_REQUEST_TEMPLATE.md`
  Canonical template that satisfies the agents-md check by default and
  records the data the reviewer needs to integrate the change without
  follow-up questions.
- `docs/dev/shared-file-policy.md`
  Single source of truth for "do not touch these files in a category
  PR". Category workers must read this before writing any C++.
- `docs/dev/runbooks/issue-resolution.md`
  Step-by-step recipe a worker can follow from issue selection to PR
  merge.
- `docs/dev/runbooks/wave-close.md`
  Step-by-step recipe the reviewer follows to drain `CHANGELOG.d/`,
  lower the queued baseline, and close the wave roadmap issue.

## 14. Updated PR / branch policy (supersedes #76 7.5)

- Branch: `codex/stubs-w<N>-<category>-part<M>`.
- Maximum 8 handlers per PR; large categories (>8) split into `part1`,
  `part2`, ...
- Final part PR uses `Closes #<issue>`; intermediate parts use
  `Refs #<issue>`.
- Shared files (router, bridge, `scripts/live_e2e_smoke.py`,
  `CHANGELOG.md`, queued baseline) are *queued in the PR description*
  and applied by the wave-close PR. See
  `docs/dev/shared-file-policy.md`.
- Every `stub-impl` PR must include `## Scope reconciliation`,
  `## UE 5.7 API research`, and `## Tests` sections (the
  agents-md-pr-check workflow enforces this).
- Before opening the PR, run:

  ```pwsh
  python scripts\audit_route_contracts.py --strict
  python scripts\audit_no_new_queued.py
  cd Python; python -m pytest tests\unit tests\contract -q
  pwsh -File scripts\run_local_uat_buildplugin.ps1
  ```

  and quote the artifact paths in the PR body.

## 15. Wave -> milestone schedule

| Phase | Issues | Target due |
|---|---|---|
| W0.5 | infra (this section) | 2026-05-27 |
| W1 (#78) | #79, #80 | 2026-06-07 |
| W2 (#83) | #84, #85, #86, #87 | 2026-07-04 |
| W3 (#88) | #89, #90, #91, #92 | 2026-07-18 |
| W4 (#93) | #94, #95, #96, #97 | 2026-08-01 |
| W5 (#98) | #99, #100, #101 | 2026-08-08 |
| Umbrella (#69) | close after W5 | 2026-08-08 + 2 days |

## 16. Resource allocation

- Worker A (light categories): Landscape, DataTable, Water, Localization,
  MetaSound.
- Worker B (editor / asset categories): Animation Rigging, Sequencer,
  Foliage, Source Control, Testing/Validation.
- Worker C (gameplay / physics categories): GAS, Chaos, Movie Render
  Queue, Mobile/XR.
- Worker D (high-risk-API categories): AI/Nav Extension, PCG, Networking.
- Reviewer/Integrator: owns W0.5, shared-file edits, wave-close PRs,
  CHANGELOG fold-in, queued baseline lowering, and #69.

With only two workers available, serialise PCG / Chaos / Networking /
Movie Render Queue and extend M8 / M9 / M10 due dates accordingly.

## 17. SME review recommendations

| Category | Reason |
|---|---|
| #84 AI/Nav Extension | StateTree + Navigation + AI Sense API churn in 5.7. |
| #89 Chaos | GeometryCollection / Cluster API churn in 5.7. |
| #91 PCG | PCG graph + GeometryScript interop is new in 5.7. |
| #95 Movie Render Queue | MovieGraph supersedes MRQ in 5.7. |
| #96 Networking | Iris + ReplicationGraph layout changes. |
| #99 MetaSound | MetaSoundFrontend reorg in 5.7. |

A spike doc lives under `docs/spike/<category>-ue57.md` for each of
these before the implementation PRs land.

# 234-stubs Issue Resolution Runbook

234-stubs Wave 0.5 follow-up (umbrella: #69).

Single-file recipe for taking a stub category issue from "open" to
"closed" without colliding with parallel workers. Read this once, then
keep it next to the PR you are about to open.

## 1. Pick a category

Pick an open issue from
`https://github.com/neko-jpg/unreal-engine-mcp/issues?q=is%3Aopen+label%3Astub-impl`.

Reconcile the *user-declared* stub count with the *current* `queued: true`
grep count:

```pwsh
python scripts\audit_no_new_queued.py --print
```

For each category, the printed count and the count in the issue title
should agree. If they don't, copy the delta into the *Scope reconciliation*
section of the PR body so reviewers can see whether you are doing a full
promotion or only finishing the residual handlers.

## 2. UE 5.7 API research (mandatory)

AGENTS.md requires you to verify every API call against UE 5.7 before
writing C++. The PR template's `## UE 5.7 API research` section is
enforced by `.github/workflows/agents-md-pr-check.yml` when the
`stub-impl` label is present.

Suggested checklist:

- `web_search` for `"<ClassOrStruct> 5.7"` and `"<HeaderName> 5.7"`.
- Confirm `TryUpdateDefaultConfigFile()` is used wherever `.ini` is persisted.
- Skim the relevant `Engine/Source/.../Public/*.h` headers in the
  UE 5.7 install (or the engine GitHub branch) for renamed symbols.

## 3. Branch + scope

```pwsh
git checkout main
git pull --ff-only origin main
git checkout -b codex/stubs-w<N>-<category>-part<M>
```

Cap each PR at **8 handlers**. If your issue has more, split it; only the
final PR carries `Closes #<issue>`.

## 4. Implement (C++ side)

Edit only the category's `EpicUnrealMCP<Cat>Commands.cpp` /
`EpicUnrealMCP<Cat>Commands.h`. Never edit `EpicUnrealMCPRouter.cpp`,
`EpicUnrealMCPBridge.cpp`, or `scripts\live_e2e_smoke.py` from a
category PR (see `docs/dev/shared-file-policy.md`).

Skeleton (copy and adapt):

```cpp
TSharedPtr<FJsonObject> FEpicUnrealMCP<Cat>Commands::Handle<Action>(
    const TSharedPtr<FJsonObject>& Params)
{
    if (!Is<Cat>Available()) return MakeUnavailable(TEXT("<command>"));

#if WITH_<MODULE>_MCP
    // 1. Validate inputs (return CreateErrorResponse on failure).
    // 2. Resolve UObjects.
    // 3. FMCPScopedTransaction Tx(LOCTEXT(...));
    // 4. Object->Modify();
    //    perform the real UE 5.7 API call.
    // 5. If persisting ini, use
    //    FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(Object);
    auto Data = MakeShared<FJsonObject>();
    Data->SetBoolField(TEXT("executed"), true);
    Data->SetStringField(TEXT("path"), Object->GetPathName());
    return MakeSuccessEnvelope(Data);
#else
    return MakeUnavailable(TEXT("<command>"));
#endif
}
```

Forbidden:

- `UpdateDefaultConfigFile()` (use the `Try` form).
- `Data->SetBoolField(TEXT("queued"), true)` on success paths.
- Adding entries to `EpicUnrealMCPRouter.cpp` (queue in PR body instead).

## 5. Implement (Python side)

Edit only `Python/server/<category>_tools.py`. Validate inputs with
`pydantic`. Map the new tool name to the C++ command name and add a unit
test under `Python/tests/unit/test_<category>_<handler>.py`.

Minimum tests per handler:

- happy path
- invalid input
- connection / command error
- `assert_executed(result, "<command>")`
- `queued: true` is **not** in the response data

## 6. Local validation

```pwsh
python scripts\audit_route_contracts.py --strict
python scripts\audit_no_new_queued.py
cd Python; python -m pytest tests\unit tests\contract -q
pwsh -File scripts\run_local_uat_buildplugin.ps1
```

Capture the `artifacts\local_uat\<timestamp>\runuat.log` path and paste
it into the PR body's `## Tests` section.

## 7. CHANGELOG fragment

Drop one Markdown file at
`CHANGELOG.d/w<N>-<category>-<slug>.md`. See
`CHANGELOG.d/README.md` for the shape.

## 8. Open the PR

Use the template. Make sure `## Scope reconciliation`,
`## UE 5.7 API research`, and `## Tests` are present; the labeler picks
up the `stub-impl` label automatically when you touch a category `*.cpp`
file, which in turn triggers the agents-md-pr-check workflow.

## 9. After merge

Comment on the parent issue with:

- handlers promoted
- residual queued sites (link to commit/lines)
- next planned PR (if any)

The reviewer/integrator folds your fragment(s) and updates
`artifacts/queued_baseline.json` during the wave-close PR.

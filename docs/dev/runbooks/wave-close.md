# Wave-close PR Runbook

234-stubs Wave 0.5 follow-up (umbrella: #69).

Recipe for the reviewer / integrator who lands the wave-close PR after
every category in the wave is done.

## 1. Confirm wave readiness

- Every category issue in the wave is closed (or has a final PR open).
- `python scripts/audit_no_new_queued.py --print` shows the expected
  per-file drop for the wave.
- `pytest Python/tests/unit Python/tests/contract` green on main.

## 2. Branch

```pwsh
git checkout main
git pull --ff-only origin main
git checkout -b codex/wave<N>-close
```

## 3. Fold CHANGELOG fragments

```pwsh
python scripts/fold_changelog_fragments.py --wave <N>
```

Commits should be:

1. `chore(changelog): fold wave <N> fragments`
2. `chore(audit): lower queued baseline after wave <N>`
3. `feat(shared): apply queued router / live-smoke edits collected during wave <N>`

The third commit applies any *Router / Bridge / live_e2e_smoke notes*
queued in the category PR bodies. Audit each insertion against
`docs/dev/shared-file-policy.md`.

## 4. Lower the queued baseline

```pwsh
python scripts/audit_no_new_queued.py --update-baseline
git add artifacts/queued_baseline.json
git commit -m "chore(audit): lower queued baseline after wave <N>"
```

## 5. Run the wave smoke

```pwsh
python scripts/live_e2e_smoke.py --group wave<N>
```

Copy the report path into the wave roadmap issue's Done comment.

## 6. Roadmap issue close

Close `#78 / #83 / #88 / #93 / #98` with a Done comment that lists:

- merged PRs
- handler count promoted
- residual queued sites (if any) + follow-up issue links
- live smoke result path

## 7. Umbrella update (#69)

Edit the umbrella issue's body table to tick the wave. Do not close
#69 until W5 is done.

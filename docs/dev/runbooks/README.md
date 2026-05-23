# Runbooks index — 234-stubs Waves 1-5

234-stubs Wave 0.5 follow-up (umbrella: #69).

| Runbook | When to use |
|---|---|
| [issue-resolution.md](./issue-resolution.md) | A worker is taking a category stub issue from open to merged. |
| [wave-close.md](./wave-close.md) | The reviewer/integrator is closing a wave roadmap issue (#78 / #83 / #88 / #93 / #98). |

Supporting docs:

- `../shared-file-policy.md` — list of files no category PR may edit.
- `../../implementation-plan-234-stubs.md` — wave / category roadmap and DoD.
- `../../spike/<category>-ue57.md` — pre-impl spike notes for high-risk categories.

CI surface used by these runbooks:

- `.github/workflows/labeler.yml` — auto-labels PRs.
- `.github/workflows/agents-md-pr-check.yml` — enforces PR body sections on `stub-impl` PRs.
- `.github/workflows/queued-audit.yml` — blocks any PR that increases `queued: true`.
- `.github/workflows/ue57-build.yml` — runs `RunUAT BuildPlugin` on self-hosted UE 5.7 runners when `ue5.7-build` label is present.
- `.github/workflows/route-contract-audit.yml` — drift between Python / Rust / Cpp command layers.
- `.github/workflows/python-tests.yml` — unit + contract + envelope helper smoke.

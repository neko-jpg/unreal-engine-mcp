# CHANGELOG fragments

234-stubs Wave 0.5 follow-up (umbrella: #69).

To avoid serializing every Wave 1-5 PR through the 100+ KiB `CHANGELOG.md`,
each PR drops a small fragment in this directory and the wave-close PR
(reviewer/integrator) folds them into `CHANGELOG.md`.

## Naming

```
CHANGELOG.d/<wave>-<category>-<short-slug>.md
```

Examples:

- `w1-anim-rigging-control-rig-bone.md`
- `w2-gas-add-attribute.md`
- `w3-pcg-graph-add-node-part1.md`

## Fragment shape

```md
### <category>: <handler list summary>

- Issue: #<n>
- PR: #<n>
- Wave: W<n>
- Handlers promoted: <count>
- New `executed: true` cases: <list>
- Build verified: local RunUAT / self-hosted CI / both
```

## Fold-in command

Run from the wave-close PR branch:

```pwsh
python scripts/fold_changelog_fragments.py --wave 3
```

The fold-in script appends each fragment under
`## [Unreleased] > 234-stubs > Wave <n>` in `CHANGELOG.md` and removes
the originals in the same commit.

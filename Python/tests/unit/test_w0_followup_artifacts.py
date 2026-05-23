"""234-stubs Wave 0.5 follow-up (umbrella: #69).

Static sanity checks that every artifact created by the W0.5 PR is
present and conforms to the contract that the rest of the wave-1+
machinery depends on. Treat these as canary tests: if you intentionally
remove an artifact, also remove its check here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "relative_path",
    [
        "scripts/audit_no_new_queued.py",
        "scripts/run_local_uat_buildplugin.ps1",
        "scripts/fold_changelog_fragments.py",
        "artifacts/queued_baseline.json",
        ".github/labeler.yml",
        ".github/workflows/labeler.yml",
        ".github/workflows/agents-md-pr-check.yml",
        ".github/workflows/queued-audit.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/stub_followup.yml",
        "docs/dev/shared-file-policy.md",
        "CHANGELOG.d/README.md",
    ],
)
def test_artifact_present(relative_path: str):
    p = REPO_ROOT / relative_path
    assert p.exists(), f"missing W0.5 artifact: {relative_path}"


def test_queued_baseline_schema():
    payload = json.loads(
        (REPO_ROOT / "artifacts" / "queued_baseline.json").read_text(encoding="utf-8")
    )
    assert payload.get("schema") == 1
    assert isinstance(payload.get("per_file"), dict)
    assert payload["per_file"], "baseline must list at least one file"
    assert payload.get("total") == sum(payload["per_file"].values())


def test_labeler_lists_every_stub_category():
    text = (REPO_ROOT / ".github" / "labeler.yml").read_text(encoding="utf-8")
    categories = [
        "EpicUnrealMCPAiNavExtensionCommands.cpp",
        "EpicUnrealMCPAnimationRiggingCommands.cpp",
        "EpicUnrealMCPChaosCommands.cpp",
        "EpicUnrealMCPDataTableExtensionCommands.cpp",
        "EpicUnrealMCPFoliageCommands.cpp",
        "EpicUnrealMCPGASCommands.cpp",
        "EpicUnrealMCPLandscapeCommands.cpp",
        "EpicUnrealMCPLocalizationCommands.cpp",
        "EpicUnrealMCPMetaSoundCommands.cpp",
        "EpicUnrealMCPMobileXrCommands.cpp",
        "EpicUnrealMCPMovieRenderQueueCommands.cpp",
        "EpicUnrealMCPNetworkingCommands.cpp",
        "EpicUnrealMCPPCGCommands.cpp",
        "EpicUnrealMCPSequencerExtensionCommands.cpp",
        "EpicUnrealMCPSourceControlCommands.cpp",
        "EpicUnrealMCPTestingValidationCommands.cpp",
        "EpicUnrealMCPWaterCommands.cpp",
    ]
    for name in categories:
        assert name in text, f"labeler.yml missing entry for {name}"


def test_pr_template_has_required_headers():
    text = (REPO_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(
        encoding="utf-8"
    )
    for header in (
        "## Scope reconciliation",
        "## UE 5.7 API research",
        "## Tests",
        "## CHANGELOG",
    ):
        assert header in text, f"PR template missing header: {header}"


def test_shared_file_policy_mentions_each_shared_file():
    text = (REPO_ROOT / "docs" / "dev" / "shared-file-policy.md").read_text(
        encoding="utf-8"
    )
    for shared in (
        "EpicUnrealMCPRouter.cpp",
        "EpicUnrealMCPBridge.cpp",
        "scripts/live_e2e_smoke.py",
        "CHANGELOG.md",
        "artifacts/queued_baseline.json",
    ):
        assert shared in text, f"shared-file policy missing: {shared}"

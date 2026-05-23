"""234-stubs Wave 0.5 follow-up refinements (umbrella: #69).

Regression tests that lock in the W0.5 hardening decisions made on top
of PR #105:

- ``agents-md-pr-check.yml`` must always run (no job-level skip on
  ``stub-impl``); the label check moves inside the step so the job
  status is reportable for branch protection.
- ``queued-audit.yml`` must declare a ``concurrency`` group so duplicate
  pushes do not race.
- ``labeler.yml`` must publish ``stub-impl`` whenever a category cpp
  file is touched (otherwise ``agents-md-pr-check`` is never wired up).
- ``ue5.7-build`` label is the trigger for the gated UE 5.7 RunUAT job;
  if it is missing from ``labeler.yml`` the build matrix can never fire.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover - dev env always has PyYAML via uv
    yaml = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[3]
WF_DIR = REPO_ROOT / ".github" / "workflows"


pytestmark = pytest.mark.skipif(yaml is None, reason="PyYAML not installed")


def _load(name: str) -> dict:
    return yaml.safe_load((WF_DIR / name).read_text(encoding="utf-8"))


def test_agents_md_pr_check_runs_unconditionally():
    """The job must not have a top-level ``if: contains(stub-impl)`` guard."""
    text = (WF_DIR / "agents-md-pr-check.yml").read_text(encoding="utf-8")
    # If the job-level guard is back the workflow becomes a "skipped"
    # check that branch protection cannot require.
    assert "if: contains(github.event.pull_request.labels.*.name, 'stub-impl')" not in text
    # The runtime guard must still exist inside the script body.
    assert "labels.includes(\"stub-impl\")" in text or "stub-impl" in text


def test_agents_md_pr_check_supports_workflow_dispatch():
    data = _load("agents-md-pr-check.yml")
    on = data.get(True) or data.get("on")
    assert isinstance(on, dict)
    assert "workflow_dispatch" in on
    dispatch = on["workflow_dispatch"]
    assert isinstance(dispatch, dict) and "inputs" in dispatch
    assert "pr_number" in dispatch["inputs"]


def test_agents_md_pr_check_has_concurrency_group():
    data = _load("agents-md-pr-check.yml")
    assert "concurrency" in data
    assert data["concurrency"].get("cancel-in-progress") is True


def test_queued_audit_has_concurrency_and_dispatch():
    data = _load("queued-audit.yml")
    on = data.get(True) or data.get("on")
    assert "workflow_dispatch" in on
    assert "concurrency" in data
    assert "cancel-in-progress" in data["concurrency"]


def test_labeler_workflow_dispatchable():
    data = _load("labeler.yml")
    on = data.get(True) or data.get("on")
    assert "workflow_dispatch" in on
    assert "concurrency" in data


def test_labeler_config_lists_ue57_build_label():
    text = (REPO_ROOT / ".github" / "labeler.yml").read_text(encoding="utf-8")
    assert re.search(r"^ue5\.7-build:\s*$", text, re.MULTILINE), text
    assert "stub-impl:" in text


def test_labeler_config_has_one_cat_label_per_category_cpp():
    text = (REPO_ROOT / ".github" / "labeler.yml").read_text(encoding="utf-8")
    pairs = {
        "EpicUnrealMCPAiNavExtensionCommands.cpp": "stub-cat-ai-nav-extension",
        "EpicUnrealMCPAnimationRiggingCommands.cpp": "stub-cat-anim-rigging",
        "EpicUnrealMCPChaosCommands.cpp": "stub-cat-chaos",
        "EpicUnrealMCPDataTableExtensionCommands.cpp": "stub-cat-data-table-extension",
        "EpicUnrealMCPFoliageCommands.cpp": "stub-cat-foliage",
        "EpicUnrealMCPGASCommands.cpp": "stub-cat-gas",
        "EpicUnrealMCPLandscapeCommands.cpp": "stub-cat-landscape",
        "EpicUnrealMCPLocalizationCommands.cpp": "stub-cat-localization",
        "EpicUnrealMCPMetaSoundCommands.cpp": "stub-cat-metasound",
        "EpicUnrealMCPMobileXrCommands.cpp": "stub-cat-mobile-xr",
        "EpicUnrealMCPMovieRenderQueueCommands.cpp": "stub-cat-movie-render-queue",
        "EpicUnrealMCPNetworkingCommands.cpp": "stub-cat-networking",
        "EpicUnrealMCPPCGCommands.cpp": "stub-cat-pcg",
        "EpicUnrealMCPSequencerExtensionCommands.cpp": "stub-cat-sequencer-extension",
        "EpicUnrealMCPSourceControlCommands.cpp": "stub-cat-source-control",
        "EpicUnrealMCPTestingValidationCommands.cpp": "stub-cat-testing-validation",
        "EpicUnrealMCPWaterCommands.cpp": "stub-cat-water",
    }
    for cpp, label in pairs.items():
        block_match = re.search(rf"^{re.escape(label)}:\s*$", text, re.MULTILINE)
        assert block_match, f"labeler.yml missing block: {label}"
        # The block must include the cpp filename glob.
        # Find the slice of text from this label to the next top-level label or EOF.
        start = block_match.end()
        next_label = re.search(r"^[a-z][a-z0-9._-]*:\s*$", text[start:], re.MULTILINE)
        end = start + next_label.start() if next_label else len(text)
        block = text[start:end]
        assert cpp in block, f"{label} block does not reference {cpp}"

"""234-stubs Wave 0.5 follow-up (umbrella: #69).

Unit tests for scripts/fold_changelog_fragments.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "fold_changelog_fragments.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "fold_changelog_fragments", SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def fold_mod():
    return _load_module()


def _set_paths(monkeypatch, mod, tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    fragment_dir = tmp_path / "CHANGELOG.d"
    fragment_dir.mkdir()
    monkeypatch.setattr(mod, "CHANGELOG", changelog)
    monkeypatch.setattr(mod, "FRAGMENT_DIR", fragment_dir)
    return changelog, fragment_dir


def test_fold_creates_unreleased_and_wave_section(tmp_path, monkeypatch, fold_mod):
    changelog, fragment_dir = _set_paths(monkeypatch, fold_mod, tmp_path)
    (fragment_dir / "w1-anim-rigging-test.md").write_text(
        "### anim-rigging: control_rig_bone\n\n- Promoted: 1\n",
        encoding="utf-8",
    )

    rc = fold_mod.fold(1)
    assert rc == 0

    text = changelog.read_text(encoding="utf-8")
    assert "## [Unreleased]" in text
    assert "### 234-stubs Wave 1" in text
    assert "control_rig_bone" in text
    assert not list(fragment_dir.glob("w1-*.md"))


def test_fold_skips_other_waves(tmp_path, monkeypatch, fold_mod):
    changelog, fragment_dir = _set_paths(monkeypatch, fold_mod, tmp_path)
    (fragment_dir / "w1-foo.md").write_text("- w1", encoding="utf-8")
    (fragment_dir / "w2-bar.md").write_text("- w2", encoding="utf-8")

    fold_mod.fold(1)
    fold_mod.fold(2)

    text = changelog.read_text(encoding="utf-8")
    assert "### 234-stubs Wave 1" in text
    assert "### 234-stubs Wave 2" in text
    assert "w1" in text and "w2" in text


def test_fold_appends_to_existing_wave_section(tmp_path, monkeypatch, fold_mod):
    changelog, fragment_dir = _set_paths(monkeypatch, fold_mod, tmp_path)
    changelog.write_text(
        "## [Unreleased]\n\n### 234-stubs Wave 1\n\n- existing\n",
        encoding="utf-8",
    )
    (fragment_dir / "w1-second.md").write_text("- second", encoding="utf-8")

    fold_mod.fold(1)
    text = changelog.read_text(encoding="utf-8")
    assert "existing" in text and "second" in text
    assert text.count("### 234-stubs Wave 1") == 1


def test_dry_run_keeps_fragments(tmp_path, monkeypatch, fold_mod):
    changelog, fragment_dir = _set_paths(monkeypatch, fold_mod, tmp_path)
    (fragment_dir / "w1-foo.md").write_text("- w1", encoding="utf-8")
    fold_mod.fold(1, dry_run=True)
    assert (fragment_dir / "w1-foo.md").exists()
    assert not changelog.exists()


def test_ignores_readme_and_gitkeep(tmp_path, monkeypatch, fold_mod):
    changelog, fragment_dir = _set_paths(monkeypatch, fold_mod, tmp_path)
    (fragment_dir / "README.md").write_text("doc", encoding="utf-8")
    (fragment_dir / ".gitkeep").write_text("", encoding="utf-8")
    rc = fold_mod.fold(1)
    assert rc == 0
    assert not changelog.exists()

def test_all_waves_runs_every_wave(tmp_path, monkeypatch, fold_mod):
    changelog, fragment_dir = _set_paths(monkeypatch, fold_mod, tmp_path)
    (fragment_dir / "w1-foo.md").write_text("- w1", encoding="utf-8")
    (fragment_dir / "w3-bar.md").write_text("- w3", encoding="utf-8")
    (fragment_dir / "w5-baz.md").write_text("- w5", encoding="utf-8")

    rc = fold_mod.main(["--all-waves"])
    assert rc == 0

    text = changelog.read_text(encoding="utf-8")
    for heading in ("### 234-stubs Wave 1", "### 234-stubs Wave 3", "### 234-stubs Wave 5"):
        assert heading in text
    assert not list(fragment_dir.glob("w[1-5]-*.md"))


def test_all_waves_and_wave_are_mutually_exclusive(fold_mod):
    import pytest as _pt
    with _pt.raises(SystemExit):
        fold_mod.main(["--all-waves", "--wave", "1"])


# harness-kit 2026.09 — stamp and harvest contracts.
"""One stamp method for every project. Harvest is proposal-only."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name: str):
    tools = ROOT / "reference" / "tools"
    if not (tools / f"{name}.py").is_file():
        tools = ROOT / "scripts"
    sys.path.insert(0, str(tools))
    spec = importlib.util.spec_from_file_location(f"_kit_{name}", tools / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def stamp_mod():
    return _load("kit_stamp")


@pytest.fixture
def harvest_mod():
    return _load("kit_harvest")


def _mini_kit(tmp_path: pathlib.Path) -> pathlib.Path:
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "STANDUP.md").write_text(
        "`templates/HARNESS.project.md` → `HARNESS.md`\n"
        "`reference/guards/*.py` → `scripts/`\n"
        "`reference/tools/kit_poll.py` → `scripts/`\n",
        encoding="utf-8",
    )
    (kit / "kit-files.txt").write_text(
        "templates/HARNESS.project.md\n"
        "reference/guards/az_guard.py\n"
        "reference/tools/kit_poll.py\n"
        "spec/guards.md\n",
        encoding="utf-8",
    )
    (kit / "kit-manifest.json").write_text(
        json.dumps({"files": {"CHANGELOG.md": "a" * 64}, "kit_version": "2026.09.4"}),
        encoding="utf-8",
    )
    (kit / "CHANGELOG.md").write_text("## 2026.09.4 — x\n", encoding="utf-8")
    return kit


def _project_with_harness(tmp_path: pathlib.Path) -> pathlib.Path:
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "HARNESS.md").write_text("# local harness\n", encoding="utf-8")
    (proj / "scripts").mkdir()
    (proj / "scripts" / "az_guard.py").write_text("# guard\n", encoding="utf-8")
    return proj


def test_stamp_fingerprints_only_present_mapped_dests(tmp_path, stamp_mod):
    kit = _mini_kit(tmp_path)
    proj = _project_with_harness(tmp_path)
    out = stamp_mod.stamp(proj, kit)
    assert out["kit_version"] == "2026.09.4"
    assert out["stamped"] == ["HARNESS.md", "scripts/az_guard.py"]
    assert (proj / "kit-files.txt").is_file()
    assert (proj / "kit-manifest.json").is_file()
    manifest = json.loads((proj / "kit-manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["files"]) == {"HARNESS.md", "scripts/az_guard.py"}
    assert "spec/guards.md" in out["kit_repo_only"]
    assert any(r["project"] == "scripts/kit_poll.py" for r in out["absent"])


def test_stamp_refuses_overwrite_without_refresh(tmp_path, stamp_mod):
    kit = _mini_kit(tmp_path)
    proj = _project_with_harness(tmp_path)
    stamp_mod.stamp(proj, kit)
    with pytest.raises(stamp_mod.KitError, match="--refresh"):
        stamp_mod.stamp(proj, kit)
    stamp_mod.stamp(proj, kit, refresh=True)


def test_stamp_refuses_empty_tree(tmp_path, stamp_mod):
    kit = _mini_kit(tmp_path)
    proj = tmp_path / "empty"
    proj.mkdir()
    with pytest.raises(stamp_mod.KitError, match="STANDUP"):
        stamp_mod.stamp(proj, kit)


def test_harvest_requires_stamp(tmp_path, harvest_mod):
    kit = _mini_kit(tmp_path)
    proj = _project_with_harness(tmp_path)
    with pytest.raises(harvest_mod.KitError, match="stamp first"):
        harvest_mod.harvest(proj, kit)


def test_stamp_dry_run_does_not_write(tmp_path, stamp_mod):
    kit = _mini_kit(tmp_path)
    proj = _project_with_harness(tmp_path)
    rc = stamp_mod.main(["--project", str(proj), "--kit", str(kit), "--dry-run"])
    assert rc == 0
    assert not (proj / "kit-files.txt").exists()
    assert not (proj / "kit-manifest.json").exists()


def test_refresh_picks_up_newly_present_dest(tmp_path, stamp_mod):
    kit = _mini_kit(tmp_path)
    proj = _project_with_harness(tmp_path)
    stamp_mod.stamp(proj, kit)
    (proj / "scripts" / "kit_poll.py").write_text("# poll\n", encoding="utf-8")
    out = stamp_mod.stamp(proj, kit, refresh=True)
    assert "scripts/kit_poll.py" in out["stamped"]


def test_harvest_reports_customized_and_extra(tmp_path, stamp_mod, harvest_mod):
    kit = _mini_kit(tmp_path)
    proj = _project_with_harness(tmp_path)
    stamp_mod.stamp(proj, kit)
    (proj / "HARNESS.md").write_text("# customized\n", encoding="utf-8")
    (proj / "scripts" / "cursor_harness_check.py").write_text("# extra\n", encoding="utf-8")
    (proj / "cursor-hook-debug.jsonl").write_text("{}\n", encoding="utf-8")
    (proj / ".cursor").mkdir()
    (proj / ".cursor" / "cursor-hook-debug.jsonl").write_text("{}\n", encoding="utf-8")
    (proj / "tests").mkdir()
    (proj / "tests" / "test_portal.py").write_text("# product\n", encoding="utf-8")
    (proj / "app").mkdir()
    (proj / "app" / "portal.py").write_text("# product\n", encoding="utf-8")
    out = harvest_mod.harvest(proj, kit)
    assert out["never_self_apply"] is True
    assert any(c["project"] == "HARNESS.md" and c["kit"] == "templates/HARNESS.project.md"
               for c in out["customized"])
    extras = {e["project"] for e in out["extra"]}
    assert "scripts/cursor_harness_check.py" in extras
    assert "tests/test_portal.py" not in extras
    assert "app/portal.py" not in extras
    assert "cursor-hook-debug.jsonl" not in extras
    assert ".cursor/cursor-hook-debug.jsonl" not in extras

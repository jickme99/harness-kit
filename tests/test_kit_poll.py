# harness-kit 2026.09 — kit_poll worklist and STANDUP-mapping contracts.
"""Poll is proposal-only. These tests watch the fail-open classes the recipe named:

- same-version changelog sections stay on the worklist
- unknown Applies-to is consider, never skip
- STANDUP arrows map kit paths (HARNESS.project.md is not HARNESS.md)
- a missing stamp refuses rather than inventing a version
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_poll():
    tools = ROOT / "reference" / "tools"
    if not (tools / "kit_poll.py").is_file():
        tools = ROOT / "scripts"
    sys.path.insert(0, str(tools))
    spec = importlib.util.spec_from_file_location("_kit_poll", tools / "kit_poll.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def poll():
    return load_poll()


def test_parse_version_calendar_line_is_patch_zero(poll):
    assert poll.parse_version("2026.09") == (2026, 9, 0)
    assert poll.parse_version("2026.09.1") == (2026, 9, 1)
    assert poll.parse_version("2026.09") < poll.parse_version("2026.09.1")
    with pytest.raises(poll.KitError):
        poll.parse_version("v1")


def test_same_version_stays_on_the_worklist(poll):
    sections = poll.parse_changelog(
        "## 2026.09 — baseline\n\n- **Applies to:** every stamp.\n\n"
        "## 2026.09.1 — poll surface\n\n- **Applies to:** every stamp.\n"
    )
    rows = poll.worklist("2026.09", sections)
    assert [r["version"] for r in rows] == ["2026.09", "2026.09.1"]
    assert rows[0]["same_version"] is True
    assert rows[1]["same_version"] is False
    older = poll.worklist("2026.09.1", sections)
    assert [r["version"] for r in older] == ["2026.09.1"]


def test_unknown_applies_to_is_consider_not_skip(poll):
    sections = poll.parse_changelog(
        "## 2026.09.2 — x\n\n- **Applies to:** the-new-harness-nobody-listed.\n"
        "- **Lane:** 1 (bug-fix).\n"
    )
    rows = poll.worklist("2026.09", sections)
    assert len(rows) == 1
    assert rows[0]["consider"] is True
    assert rows[0]["skip"] is False
    assert "the-new-harness-nobody-listed" in rows[0]["applies_to"]
    assert rows[0]["lane"].startswith("1")


def test_live_changelog_2026_09_2_keeps_wrapped_applies_to(poll):
    path = ROOT / "CHANGELOG.md"
    if not path.is_file():
        pytest.skip("CHANGELOG.md is kit-repo-only")
    rows = {r["version"]: r for r in poll.worklist(
        "2026.09.2", poll.parse_changelog(path.read_text(encoding="utf-8")))}
    row = rows["2026.09.2"]
    assert "AGENTS.project.md" in row["applies_to"]
    assert "Lane 3" in row["lane"]


def test_wrapped_lane_and_applies_to_keep_continuation_lines(poll):
    sections = poll.parse_changelog(
        "## 2026.09.2 — x\n\n"
        "- **Lane:** 1 for the install-path miss.\n"
        "  Lane 3 for the AGENTS template.\n"
        "- **Applies to:** Cursor for the install path.\n"
        "  Every stamp for `templates/AGENTS.project.md`.\n"
    )
    rows = poll.worklist("2026.09", sections)
    assert "Lane 3 for the AGENTS template" in rows[0]["lane"]
    assert "templates/AGENTS.project.md" in rows[0]["applies_to"]
    assert rows[0]["skip"] is False


def test_standup_maps_harness_template_and_guards(poll):
    standup_path = ROOT / "STANDUP.md"
    if not standup_path.is_file():
        pytest.skip("STANDUP.md is kit-repo-only; stamps do not install it")
    rules = poll.copy_rules(poll.map_source_texts(ROOT))
    assert poll.map_kit_path("templates/HARNESS.project.md", rules) == "HARNESS.md"
    assert poll.map_kit_path("templates/CLAUDE.project.md", rules) == "CLAUDE.md"
    assert poll.map_kit_path("templates/AGENTS.project.md", rules) == "AGENTS.md"
    assert poll.map_kit_path(
        "templates/START-HERE.project.md", rules) == "START-HERE.md"
    assert poll.map_kit_path(
        "templates/wiki/HANDOFF.md", rules) == "wiki/HANDOFF.md"
    mapped_guard = poll.map_kit_path("reference/guards/az_guard.py", rules)
    assert mapped_guard == "scripts/az_guard.py"
    assert "//" not in mapped_guard
    assert poll.map_kit_path(
        "reference/tools/kit_poll.py", rules) == "scripts/kit_poll.py"
    assert poll.map_kit_path(
        "reference/cursor/bridge.cmd", rules) == ".cursor/hooks/bridge.cmd"
    assert poll.map_kit_path("spec/operating-model.md", rules) is None
    assert poll.map_kit_path("adapters/cursor.md", rules) is None
    assert poll.map_kit_path("tests/test_kit_poll.py", rules) == "tests/test_kit_poll.py"
    assert poll.map_kit_path(
        "reference/cursor/BUGBOT.md", rules) == ".cursor/BUGBOT.md"
    assert poll.map_kit_path(
        "reference/cursor/project-rules.mdc",
        rules) == ".cursor/rules/project-rules.mdc"
    assert poll.map_kit_path(
        "reference/cursor/outside-the-lane.mdc",
        rules) == ".cursor/rules/outside-the-lane.mdc"
    assert poll.map_kit_path(
        "reference/claude/harness-auditor.md",
        rules) == ".claude/agents/harness-auditor.md"


def test_membership_new_member_vs_kit_repo_only(poll):
    rules = poll.copy_rules(
        "`templates/HARNESS.project.md` → `HARNESS.md`\n"
        "`reference/guards/*.py` → `scripts/`\n"
    )
    drift = poll.membership_drift(
        ["templates/HARNESS.project.md", "spec/guards.md",
         "reference/guards/az_guard.py"],
        ["scripts/az_guard.py"],
        rules,
    )
    assert drift["kit_repo_only"] == ["spec/guards.md"]
    assert drift["new_members"] == [
        {"kit": "templates/HARNESS.project.md", "project": "HARNESS.md"}]
    assert drift["project_only"] == []
    assert drift["mapped"]["reference/guards/az_guard.py"] == "scripts/az_guard.py"


def test_poll_refuses_unstamped_project(tmp_path, poll):
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "CHANGELOG.md").write_text("## 2026.09.3 — x\n", encoding="utf-8")
    with pytest.raises(poll.KitError, match="stamp first"):
        poll.poll(tmp_path / "proj", kit)


def _stamped_pair(tmp_path, poll, *, standup: bool = True, kit_files: bool = True):
    kit = tmp_path / "kit"
    proj = tmp_path / "proj"
    kit.mkdir()
    proj.mkdir()
    (kit / "CHANGELOG.md").write_text("## 2026.09.3 — x\n", encoding="utf-8")
    if standup:
        (kit / "STANDUP.md").write_text("`a.md` → `a.md`\n", encoding="utf-8")
    if kit_files:
        (kit / "kit-files.txt").write_text("a.md\n", encoding="utf-8")
        (kit / "a.md").write_text("x\n", encoding="utf-8")
    (proj / "kit-manifest.json").write_text(
        poll.canonical({"files": {"a.md": "a" * 64}, "kit_version": "2026.09.3"}),
        encoding="utf-8")
    return proj, kit


def test_poll_refuses_kit_without_standup(tmp_path, poll):
    proj, kit = _stamped_pair(tmp_path, poll, standup=False)
    with pytest.raises(poll.KitError, match="STANDUP.md is the membership map"):
        poll.poll(proj, kit)


def test_poll_refuses_kit_without_file_list(tmp_path, poll):
    proj, kit = _stamped_pair(tmp_path, poll, kit_files=False)
    with pytest.raises(poll.KitError, match="kit file list"):
        poll.poll(proj, kit)


def test_poll_json_never_self_apply(tmp_path, poll):
    kit = tmp_path / "kit"
    proj = tmp_path / "proj"
    kit.mkdir()
    proj.mkdir()
    (kit / "CHANGELOG.md").write_text(
        "## 2026.09.3 — poll\n\n- **Applies to:** every stamp.\n", encoding="utf-8")
    (kit / "STANDUP.md").write_text(
        "`templates/HARNESS.project.md` → `HARNESS.md`\n", encoding="utf-8")
    (kit / "kit-files.txt").write_text("templates/HARNESS.project.md\n", encoding="utf-8")
    (kit / "templates").mkdir()
    (kit / "templates" / "HARNESS.project.md").write_text("# h\n", encoding="utf-8")
    (kit / "kit-manifest.json").write_text(
        json.dumps({"files": {"CHANGELOG.md": "a" * 64}, "kit_version": "2026.09.3"}),
        encoding="utf-8")
    (proj / "HARNESS.md").write_text("# h\n", encoding="utf-8")
    from kit_manifest import digest
    stamp = {
        "files": {"HARNESS.md": digest(proj / "HARNESS.md")},
        "kit_version": "2026.09.2",
    }
    (proj / "kit-manifest.json").write_text(poll.canonical(stamp), encoding="utf-8")
    out = poll.poll(proj, kit)
    assert out["never_self_apply"] is True
    assert out["local_version"] == "2026.09.2"
    assert out["kit_version"] == "2026.09.3"
    assert [r["version"] for r in out["worklist"]] == ["2026.09.3"]
    assert out["worklist"][0]["skip"] is False
    assert out["classify"]["unmodified"] == ["HARNESS.md"]
    assert out["membership"]["new_members"] == []

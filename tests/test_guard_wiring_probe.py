# harness-kit 2026.09 — adapter-aware guard_wiring contracts.
"""STANDUP gate step 2 used to read only `.claude/settings.json`. A correct Cursor-only
stamp then reported every guard `not_armed` and failed the gate.

Facts, not verdicts: a missing unused adapter is not a fail; a present adapter whose
targets are missing is. Cursor `hooks.json` must point at `.cursor/hooks/bridge.cmd`.
"""
from __future__ import annotations

import importlib.util
import pathlib
import shutil

import pytest

import guard_registry as reg

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_probes():
    spec = importlib.util.spec_from_file_location(
        "_kit_probes", reg.GUARDS_DIR / "harness_probes.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _first_existing(*rels: str) -> pathlib.Path | None:
    for rel in rels:
        path = ROOT / rel
        if path.is_file():
            return path
    return None


HOOKS_JSON = _first_existing("reference/cursor/hooks.json", ".cursor/hooks.json")
BRIDGE_PY = _first_existing(
    "reference/cursor/hook_bridge.py", "scripts/cursor_hook_bridge.py")
BRIDGE_CMD = _first_existing(
    "reference/cursor/bridge.cmd", ".cursor/hooks/bridge.cmd")
CLAUDE_SETTINGS = _first_existing(
    "reference/claude/settings.json", ".claude/settings.json")

requires_cursor = pytest.mark.skipif(
    not (HOOKS_JSON and BRIDGE_PY and BRIDGE_CMD),
    reason="Cursor reference files not in this tree",
)
requires_claude = pytest.mark.skipif(
    CLAUDE_SETTINGS is None,
    reason="Claude settings sample not in this tree",
)


def _touch_guards(scripts: pathlib.Path) -> None:
    scripts.mkdir(parents=True, exist_ok=True)
    for name in ("az_guard.py", "git_scope_guard.py", "merge_green_check.py"):
        (scripts / name).write_text("# stamp fixture\n", encoding="utf-8")


def _install_cursor(tree: pathlib.Path, *, wrong_bridge_dir: bool = False) -> None:
    assert HOOKS_JSON and BRIDGE_PY and BRIDGE_CMD
    cursor_dir = tree / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(HOOKS_JSON, cursor_dir / "hooks.json")
    dest_dir = cursor_dir if wrong_bridge_dir else (cursor_dir / "hooks")
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(BRIDGE_CMD, dest_dir / "bridge.cmd")
    scripts = tree / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy(BRIDGE_PY, scripts / "cursor_hook_bridge.py")
    _touch_guards(scripts)


def _install_claude(tree: pathlib.Path) -> None:
    assert CLAUDE_SETTINGS
    claude = tree / ".claude"
    claude.mkdir(parents=True, exist_ok=True)
    shutil.copy(CLAUDE_SETTINGS, claude / "settings.json")
    _touch_guards(tree / "scripts")


@pytest.fixture
def probes(tmp_path, monkeypatch):
    module = load_probes()
    monkeypatch.setattr(module, "USER_SETTINGS", tmp_path / "no-user-settings.json")
    return module


def test_empty_tree_has_no_present_project_layer(probes, tmp_path):
    out = probes._probe_guard_wiring_at(tmp_path)
    assert out["ok_to_collect"] is True
    assert out["present_project_layers"] == []
    assert out["unarmed_present_project_layers"] == []
    assert out["layers"]["claude_project"]["settings_file_present"] is False
    assert out["layers"]["cursor_project"]["hooks_file_present"] is False


@requires_cursor
def test_cursor_only_stamp_is_armed_without_claude(probes, tmp_path):
    _install_cursor(tmp_path)
    out = probes._probe_guard_wiring_at(tmp_path)
    assert out["present_project_layers"] == ["cursor_project"]
    assert out["unarmed_present_project_layers"] == []
    cursor = out["layers"]["cursor_project"]
    assert cursor["not_armed"] == []
    residual = cursor["empty_stdin_residual"]
    assert residual.get("permission") == "allow"
    assert residual.get("recorded_as") == "residual"
    assert residual.get("watched") is True
    assert out["layers"]["claude_project"]["settings_file_present"] is False


@requires_cursor
def test_wrong_bridge_dir_leaves_cursor_unarmed(probes, tmp_path):
    """D1: adapter put bridge.cmd in `.cursor/` but hooks.json calls `.cursor/hooks/`."""
    _install_cursor(tmp_path, wrong_bridge_dir=True)
    out = probes._probe_guard_wiring_at(tmp_path)
    assert out["present_project_layers"] == ["cursor_project"]
    assert "cursor_project" in out["unarmed_present_project_layers"]
    cursor = out["layers"]["cursor_project"]
    assert cursor["bridge_cmd_exists"] is False
    assert cursor["not_armed"] == [
        "az_guard.py", "git_scope_guard.py", "merge_green_check.py"]


@requires_claude
def test_claude_only_stamp_is_armed_without_cursor(probes, tmp_path):
    _install_claude(tmp_path)
    out = probes._probe_guard_wiring_at(tmp_path)
    assert out["present_project_layers"] == ["claude_project"]
    assert out["unarmed_present_project_layers"] == []
    claude = out["layers"]["claude_project"]
    assert claude["not_armed"] == []
    assert out["layers"]["cursor_project"]["hooks_file_present"] is False


@requires_claude
def test_claude_settings_present_but_scripts_missing_is_unarmed(probes, tmp_path):
    claude = tmp_path / ".claude"
    claude.mkdir()
    shutil.copy(CLAUDE_SETTINGS, claude / "settings.json")
    out = probes._probe_guard_wiring_at(tmp_path)
    assert out["present_project_layers"] == ["claude_project"]
    assert "claude_project" in out["unarmed_present_project_layers"]


def test_command_points_at_accepts_backslash_form(tmp_path):
    probes = load_probes()
    expected = probes.EXPECTED_CURSOR_BRIDGE_REL
    (tmp_path / ".cursor" / "hooks").mkdir(parents=True)
    (tmp_path / expected).write_text("@echo off\n", encoding="utf-8")
    assert probes._command_points_at(
        r".cursor\hooks\bridge.cmd", expected, tmp_path) is True
    assert probes._command_points_at(
        ".cursor/bridge.cmd", expected, tmp_path) is False

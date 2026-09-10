# harness-kit 2026.09 — Cursor bridge residual + install-path contracts.
"""The Cursor hook path has two recorded failure classes this file watches.

1. **Install path (D1).** `hooks.json` calls `.cursor/hooks/bridge.cmd`. The `.cmd`
   resolves `%~dp0..\\..\\scripts\\` only from that folder. An adapter that installed
   `bridge.cmd` one level up produced a hook that never fired.
2. **Empty/unreadable stdin fail-open (D4).** On Windows, conda's `python.cmd` dropped
   the pipe and fail-closed froze every command. The bridge allows on empty stdin and
   on JSON parse failure. That is a named residual, not a wiring fail. These tests
   watch it fire so a silent flip to deny cannot land unreviewed.

Not a Guard in `guard_registry.py`: the bridge is an adapter, not a stdin-contract
guard. Stamp layout: if this tree has no Cursor bridge, the tests skip.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _first_existing(*rels: str) -> pathlib.Path | None:
    for rel in rels:
        path = ROOT / rel
        if path.is_file():
            return path
    return None


BRIDGE_PY = _first_existing(
    "reference/cursor/hook_bridge.py",
    "scripts/cursor_hook_bridge.py",
)
HOOKS_JSON = _first_existing(
    "reference/cursor/hooks.json",
    ".cursor/hooks.json",
)
BRIDGE_CMD = _first_existing(
    "reference/cursor/bridge.cmd",
    ".cursor/hooks/bridge.cmd",
)
ADAPTER = ROOT / "adapters" / "cursor.md"


def _run_bridge(stdin: str | bytes) -> dict:
    assert BRIDGE_PY is not None
    raw = stdin if isinstance(stdin, bytes) else stdin.encode()
    r = subprocess.run(
        [sys.executable, str(BRIDGE_PY)],
        input=raw,
        capture_output=True,
        timeout=15,
    )
    assert r.returncode == 0, r.stderr
    body = json.loads(r.stdout or b"{}")
    assert isinstance(body, dict)
    return body


@pytest.mark.skipif(BRIDGE_PY is None, reason="Cursor bridge not in this tree")
def test_empty_stdin_fail_opens_as_recorded_residual():
    body = _run_bridge(b"")
    assert body.get("permission") == "allow"
    assert body.get("continue") is True


@pytest.mark.skipif(BRIDGE_PY is None, reason="Cursor bridge not in this tree")
def test_unreadable_payload_fail_opens_as_recorded_residual():
    body = _run_bridge(b"this is not json {")
    assert body.get("permission") == "allow"
    assert body.get("continue") is True


@pytest.mark.skipif(HOOKS_JSON is None, reason="Cursor hooks.json not in this tree")
def test_hooks_json_command_is_the_hooks_subdir():
    settings = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    for event in ("beforeShellExecution", "beforeMCPExecution"):
        commands = [e["command"] for e in settings["hooks"][event]]
        assert commands, event
        assert all(c.replace("\\", "/") == ".cursor/hooks/bridge.cmd" for c in commands)


@pytest.mark.skipif(BRIDGE_CMD is None, reason="Cursor bridge.cmd not in this tree")
def test_bridge_cmd_relpath_only_resolves_from_hooks_subdir():
    text = BRIDGE_CMD.read_text(encoding="utf-8")
    assert r"%~dp0..\..\scripts\cursor_hook_bridge.py" in text


@pytest.mark.skipif(not ADAPTER.is_file(), reason="Cursor adapter not in this tree")
def test_adapter_installs_bridge_into_the_hooks_subdir():
    text = ADAPTER.read_text(encoding="utf-8")
    assert "`.cursor/hooks/bridge.cmd`" in text or ".cursor/hooks/bridge.cmd" in text
    assert "`.cursor/hooks/`" in text or ".cursor/hooks/" in text
    # The D1 miss: install both files into `.cursor/` with no hooks/ subdir.
    assert "bridge.cmd` into\n`.cursor/`" not in text
    assert "and `reference/cursor/bridge.cmd` into\n`.cursor/`" not in text


@pytest.mark.skipif(BRIDGE_PY is None, reason="Cursor bridge not in this tree")
def test_residual_watch_does_not_write_debug_jsonl(tmp_path):
    dest = tmp_path / "scripts"
    dest.mkdir()
    shutil.copy(BRIDGE_PY, dest / "cursor_hook_bridge.py")
    env = {k: v for k, v in os.environ.items() if k != "CURSOR_HOOK_DEBUG"}
    r = subprocess.run(
        [sys.executable, str(dest / "cursor_hook_bridge.py")],
        input=b"",
        capture_output=True,
        timeout=15,
        env=env,
    )
    assert r.returncode == 0
    assert not (tmp_path / "local" / "cursor-hook-debug.jsonl").exists()

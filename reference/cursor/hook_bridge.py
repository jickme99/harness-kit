"""Stamp into a project as scripts/cursor_hook_bridge.py (next to the three guards).

ROOT is parents[1] — this file must live in scripts/ when installed.

Cursor hook bridge: the three Claude PreToolUse guards, plus named-plugin refusal.

Claude Code feeds each guard::

    {"tool_name": "Bash", "tool_input": {"command": "<shell>"}}

Allow = silence. Deny = JSON with hookSpecificOutput.permissionDecision = deny.

Cursor beforeShellExecution feeds::

    {"command": "<shell>", "cwd": "...", "sandbox": false}

Cursor beforeMCPExecution feeds::

    {"tool_name": "...", "tool_input": "...", "mcp_server_name": "..."}

Allow/deny for Cursor MUST be a JSON object with a ``permission`` field.
Silence is invalid JSON; with failClosed that would block *every* command,
including the ones the guards would have allowed. So this bridge always
prints ``{"permission": "allow"|"deny", ...}``.

Azure MCP is unused in this venture (owner, 2026-09-01 — same posture as
Claude Desktop). The shell path (``az --subscription``) is the one the
az-guard can actually see. This bridge refuses Azure MCP by name so that
door cannot reopen by accident.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARDS = (
    ROOT / "scripts" / "az_guard.py",
    ROOT / "scripts" / "git_scope_guard.py",
    ROOT / "scripts" / "merge_green_check.py",
)
# Server/tool names that mean "this is the Azure MCP plugin", not Microsoft Learn.
_AZURE_MCP = ("plugin-azure", "azure-mcp", "azure mcp")


def _blob(*parts: object) -> str:
    return " ".join(str(p or "") for p in parts).lower()


def is_azure_mcp(payload: dict) -> bool:
    """True when this hook event is an Azure MCP tool call, not a shell command.

    Shell ``command`` text is ignored: a git commit message that names the
    plugin must not be treated as an MCP call (false deny on routine work).
    """
    if not isinstance(payload, dict):
        return False
    server = _blob(
        payload.get("mcp_server_name"),
        payload.get("mcp_server_url"),
        payload.get("url"),
    )
    if not server:
        return False
    if "microsoft-docs" in server or "microsoft-learn" in server:
        return False
    tool = _blob(payload.get("tool_name"))
    text = f"{server} {tool}"
    return any(marker in text for marker in _AZURE_MCP) or "azure" in server


def extract_command(payload: dict) -> str | None:
    """Pull the shell command out of a Cursor or Claude-shaped payload."""
    if not isinstance(payload, dict):
        return None
    if payload.get("mcp_server_name") or payload.get("mcp_server_url"):
        return None
    cmd = payload.get("command")
    if isinstance(cmd, str) and cmd.strip():
        return cmd
    ti = payload.get("tool_input")
    if isinstance(ti, dict):
        inner = ti.get("command")
        if isinstance(inner, str) and inner.strip():
            return inner
    if isinstance(ti, str) and ti.strip():
        try:
            parsed = json.loads(ti)
        except json.JSONDecodeError:
            return ti
        if isinstance(parsed, dict):
            inner = parsed.get("command")
            if isinstance(inner, str) and inner.strip():
                return inner
        return ti
    return None


def run_guard(script: Path, command: str) -> str | None:
    """Return the guard's deny reason, or None if it allowed (silence)."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    try:
        r = subprocess.run(
            [sys.executable, str(script)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=45,
            cwd=str(ROOT),
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"{script.name} could not run: {e}"
    if r.returncode != 0:
        err = (r.stderr or "").strip()[:240]
        return f"{script.name} exited {r.returncode}" + (f": {err}" if err else "")
    out = (r.stdout or "").strip()
    if not out:
        return None
    try:
        body = json.loads(out)
    except json.JSONDecodeError:
        return out[:400]
    return (
        body.get("hookSpecificOutput", {}).get("permissionDecisionReason")
        or out[:400]
    )


def decide(payload: dict) -> dict:
    """Return a Cursor permission object. Never returns an empty document."""
    if is_azure_mcp(payload):
        reason = (
            "Azure MCP is unused in this venture. Use `az` with "
            '`--subscription "Azure Sub.1"`; the az-guard cannot see MCP calls.'
        )
        return {
            "continue": True,
            "permission": "deny",
            "user_message": reason,
            "agent_message": reason,
        }
    if payload.get("mcp_server_name") or payload.get("mcp_server_url"):
        return {"continue": True, "permission": "allow"}

    command = extract_command(payload)
    if not command:
        reason = (
            "cursor-hook-bridge: no shell command in this payload; "
            "refusing rather than guessing."
        )
        return {
            "continue": True,
            "permission": "deny",
            "user_message": reason,
            "agent_message": reason,
        }
    for script in GUARDS:
        if not script.is_file():
            reason = f"cursor-hook-bridge: missing guard {script}"
            return {
                "continue": True,
                "permission": "deny",
                "user_message": reason,
                "agent_message": reason,
            }
        reason = run_guard(script, command)
        if reason:
            return {
                "continue": True,
                "permission": "deny",
                "user_message": reason,
                "agent_message": reason,
            }
    return {"continue": True, "permission": "allow"}


def _debug(event: dict) -> None:
    path = ROOT / "local" / "cursor-hook-debug.jsonl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
    except OSError:
        pass


def main() -> int:
    raw_bytes = sys.stdin.buffer.read() if not sys.stdin.closed else b""
    head_hex = raw_bytes[:240].hex()
    try:
        raw = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raw = raw_bytes.decode("utf-16", errors="replace")
    if not raw.strip() and len(sys.argv) > 1:
        raw = sys.argv[1]
    if not raw.strip():
        interesting = {
            k: os.environ[k]
            for k in os.environ
            if any(s in k.upper() for s in ("HOOK", "CURSOR", "AGENT", "PAYLOAD"))
        }
        _debug({"event": "empty-stdin", "argv": sys.argv[1:], "env": interesting,
                "nbytes": len(raw_bytes), "head_hex": head_hex})
        json.dump({"continue": True, "permission": "allow"}, sys.stdout)
        sys.stdout.write("\n")
        return 0
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
    except (json.JSONDecodeError, ValueError) as e:
        _debug({"event": "parse-fail", "error": str(e), "nbytes": len(raw_bytes),
                "head_hex": head_hex, "argv": sys.argv[1:]})
        # Fail OPEN on an unreadable payload so a Windows stdin encoding miss
        # cannot freeze the agent. Real denials require a parsed command.
        json.dump({"continue": True, "permission": "allow"}, sys.stdout)
        sys.stdout.write("\n")
        return 0
    json.dump(decide(payload), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

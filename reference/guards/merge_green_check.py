# harness-kit 2026.09 — reference guard, proven in the origin project's Claude Code harness.
"""PreToolUse guard: `gh pr merge` is refused unless the PR's checks are green.

Born 2026-08-29: ten merges sailed past a red main in week one (harness audit T3-1).
Fail-closed: an unparseable merge command, an unreadable PR/check state, a still-running
workflow, and a red conclusion each DENY; a repo with no workflow runs at all (e.g. a
notes-only repo with no CI) is allowed. Every `gh pr merge` in the call is checked, not
just the first — `gh pr merge 1 && gh pr merge 2` used to verify PR 1 and let PR 2 ride
through on its sibling's green, and a BARE `gh pr merge` (the current-branch form) used
to be invisible to the trigger pattern entirely; both were found by this guard's own
contract review before it ever gated a call here. Reads the hook JSON on stdin; silent
(exit 0, no output) for anything that is not a `gh pr merge`.

GUARD-CONTRACT: registered in `tests/guard_registry.py`; the safe verdict is DENY — for
a merge it cannot parse, a state it cannot read, a run still in flight, and a conclusion
that is not green — and silence for everything else. A crash would be an ALLOW (the
harness treats a failed hook as no decision), so nothing escapes `main()` and the error
path DENIES, the same payload hardening its sibling guards carry.
"""
import json
import os
import re
import subprocess
import sys


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": f"merge-green guard: {reason}",
    }}))
    sys.exit(0)


def gh(args: list[str]) -> str:
    env = dict(os.environ)
    if not env.get("GH_TOKEN"):
        try:
            # A workstation holding several gh accounts can pin which one the guard reads
            # CI with; everywhere else the active account is the account. INSTALL-TIME
            # SEAM (kit): the env var is HARNESS_GH_ACCOUNT here — the origin project
            # spells it VT_GH_ACCOUNT; the divergence is deliberate and recorded in the
            # kit's TODO.md.
            account = env.get("HARNESS_GH_ACCOUNT")
            token_args = ["gh", "auth", "token"] + (["-u", account] if account else [])
            tok = subprocess.run(token_args, capture_output=True, text=True, timeout=10)
            if tok.returncode == 0:
                env["GH_TOKEN"] = tok.stdout.strip()
        except Exception:
            pass
    r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=20, env=env)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return r.stdout


def check(d) -> None:
    """Read one hook payload; refuse via deny() (which exits) or return in silence."""
    if not isinstance(d, dict):
        return                                      # not a hook payload; stay silent
    tool_input = d.get("tool_input")
    if not isinstance(tool_input, dict):
        # The harness treats a crashed hook as NO DECISION, which is an ALLOW — the one
        # failure mode a guard must never have. A payload shaped in a way this guard
        # cannot read is refused rather than guessed at (None means no shell command).
        if tool_input is None:
            return
        deny("the hook payload's tool_input is not an object, so the command could not "
             "be read. Refusing rather than guessing.")
        return
    cmd = tool_input.get("command", "") or ""
    if not isinstance(cmd, str):
        return                                      # nothing to say about this call
    # EVERY occurrence is walked. The `\b` keeps prose like `gh pr merges` out; the old
    # pattern's trailing `\s+(.*)` is gone because it made the bare current-branch merge
    # unmatchable. A bare merge now lands on the no-selector refusal below, which names
    # the remedy: state the PR explicitly so the guard can check its CI.
    for m in re.finditer(r"gh\s+pr\s+merge\b", cmd):
        rest = re.split(r"[|;&>\n]", cmd[m.end():])[0]      # this command only
        repo_m = re.search(r"(?:-R|--repo)[=\s]+([\w.-]+/[\w.-]+)", rest)
        repo = repo_m.group(1) if repo_m else None
        rest = re.sub(r"(?:-R|--repo)[=\s]+\S+", " ", rest)
        tokens = [t for t in rest.split() if not t.startswith("-")]
        selector = tokens[0] if tokens else None
        if not selector:
            deny("could not parse the PR selector from the command; use `gh pr merge "
                 "<pr> [-R owner/repo] ...` so the guard can check CI")
            return
        try:
            args = ["pr", "view", selector, "--json", "headRefName,state"]
            if repo:
                args += ["-R", repo]
            pr = json.loads(gh(args))
            head = pr["headRefName"]
            run_args = ["run", "list", "--branch", head, "--limit", "20",
                        "--json", "name,status,conclusion,createdAt"]
            if repo:
                run_args += ["-R", repo]
            runs = json.loads(gh(run_args))
        except Exception as e:
            deny(f"could not read PR/check state ({e}); fix access or check manually "
                 f"first")
            return
        if not runs:
            continue  # repo/branch with no workflows at all (e.g. a notes repo): allowed
        latest: dict = {}
        for r in sorted(runs, key=lambda r: r.get("createdAt", "")):
            latest[r["name"]] = r  # newest per workflow wins
        for name, r in latest.items():
            if r["status"] != "completed":
                deny(f"workflow '{name}' on branch '{head}' is still {r['status']} — "
                     f"wait for the conclusion, then merge")
                return
            if r["conclusion"] not in ("success", "skipped", "neutral"):
                deny(f"workflow '{name}' on branch '{head}' concluded "
                     f"{r['conclusion']} — a red branch does not merge; fix it or take "
                     f"the finding to the owner")
                return
    return  # every merge in the call is green (or the call holds none): silent allow


def main() -> None:
    try:
        d = json.load(sys.stdin)
    except Exception:
        return                                      # not a hook payload; stay silent
    try:
        check(d)
    except SystemExit:
        raise
    except Exception as exc:
        # Bare indexing over a malformed `runs` row, or anything else nobody predicted:
        # an escaped exception exits non-zero, the harness reads that as no decision,
        # and no decision is an ALLOW. Refuse instead, naming the failure.
        deny(f"the guard itself failed on this command ({type(exc).__name__}), and a "
             f"guard that errors would otherwise let the call through. Refusing.")


if __name__ == "__main__":
    main()

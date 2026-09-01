# harness-kit 2026.09 — reference guard, proven in the origin project's Claude Code harness.
"""PreToolUse guard: `gh pr merge` is refused unless the PR's checks are green.

Born 2026-08-29: ten merges sailed past a red main in week one (harness audit T3-1).
Fail-closed: an unparseable merge command or still-running checks DENY; a repo with no
workflow runs at all (e.g. the HQ wiki repo, which has no CI) is allowed. Reads the hook
JSON on stdin; silent (exit 0, no output) for anything that is not a `gh pr merge`.
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
    # INSTALL-TIME SEAM (generalized for the kit; the origin hardcoded its account here):
    # on a machine with more than one gh login, set HARNESS_GH_ACCOUNT so the guard reads
    # PR/check state as the account that owns the project's repos — the ACTIVE account is
    # machine state, not a fact about the project. Unset, gh's active account is used.
    account = os.environ.get("HARNESS_GH_ACCOUNT", "")
    if not env.get("GH_TOKEN") and account:
        try:
            tok = subprocess.run(["gh", "auth", "token", "-u", account],
                                 capture_output=True, text=True, timeout=10)
            if tok.returncode == 0:
                env["GH_TOKEN"] = tok.stdout.strip()
        except Exception:
            pass
    r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=20, env=env)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return r.stdout


def main() -> None:
    try:
        d = json.load(sys.stdin)
    except Exception:
        return
    cmd = (d.get("tool_input") or {}).get("command", "") or ""
    m = re.search(r"gh\s+pr\s+merge\s+(.*)", cmd, re.S)
    if not m:
        return  # not a merge; stay silent
    rest = re.split(r"[|;&>]", m.group(1))[0]      # this command only, no redirections
    repo_m = re.search(r"(?:-R|--repo)\s+([\w.-]+/[\w.-]+)", rest)
    repo = repo_m.group(1) if repo_m else None
    rest = re.sub(r"(?:-R|--repo)\s+\S+", " ", rest)
    tokens = [t for t in rest.split() if not t.startswith("-")]
    selector = tokens[0] if tokens else None
    if not selector:
        deny("could not parse the PR selector from the command; use `gh pr merge <pr> "
             "[-R owner/repo] ...` so the guard can check CI")
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
        deny(f"could not read PR/check state ({e}); fix access or check manually first")
        return
    if not runs:
        return  # repo/branch with no workflows at all (e.g. the wiki repo): allowed
    latest: dict = {}
    for r in sorted(runs, key=lambda r: r.get("createdAt", "")):
        latest[r["name"]] = r  # newest per workflow wins
    for name, r in latest.items():
        if r["status"] != "completed":
            deny(f"workflow '{name}' on branch '{head}' is still {r['status']} — wait "
                 f"for the conclusion, then merge")
        if r["conclusion"] not in ("success", "skipped", "neutral"):
            deny(f"workflow '{name}' on branch '{head}' concluded {r['conclusion']} — "
                 f"a red branch does not merge; fix it or take the finding to the owner")
    return  # all green: silent allow


if __name__ == "__main__":
    main()

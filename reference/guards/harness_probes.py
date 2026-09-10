# harness-kit 2026.09 — reference probe pack, proven in the origin project's Claude Code
# harness. Generalized at three install-time seams (marked EXAMPLE below): the second-repo
# path/slug, the gh account, and the two repos' labels. Everything else is faithful.
"""The harness audit's instrument panel: every fact it needs, collected mechanically.

One command, one JSON document, sorted keys, no prose:

    python scripts/harness_probes.py            # every probe
    python scripts/harness_probes.py --probe ci_main --probe review_ledger

**Facts to machines, judgment to agents.** Everything here is countable — a CI conclusion, a
date difference, a commit count, a hash comparison. Nothing here decides whether a number is
a problem; that reading is what the `harness-auditor` role spends its attention on, and it is
why that role could move to the light tier (see the engine repo's `docs/MODELS.md` change log,
2026-08-30). A probe that returns a verdict would be doing the auditor's job badly and
hiding the input that produced it.

**Every probe answers `ok_to_collect`.** A probe that could not run says so, with the reason
attached as a fact — never a silent zero, never an inferred value, never a probe missing from
the output. "Nobody could read this instrument" is itself an audit finding, and it is exactly
the kind that a fabricated default would erase. Probes fail INDEPENDENTLY: one broken git
checkout does not take the CI answer down with it.

**Read-only.** No fetch, no pull, no prune, no branch deletion — the auditor's T1 tier may act
on some of these findings, but a probe pack that mutated the thing it measures could never be
run twice for the same answer. `checkout_drift` therefore reports the age of the last fetch
beside the behind-counts, because a behind-count computed against a week-old remote ref is a
week-old fact wearing a fresh timestamp.

**Determinism:** the document's shape and key order are fixed; the values are point-in-time
facts, and `collected_at` is in the output so an age can be interpreted rather than assumed
fresh. Two runs a minute apart differ only in the values that genuinely changed.

Spans both repos. The HQ checkout is this script's own; the engine checkout is
`VT_ENGINE_REPO` or the default beside it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

HQ_ROOT = pathlib.Path(__file__).resolve().parents[1]
# INSTALL-TIME SEAM (EXAMPLE values — set these for your project). In a two-repo shape,
# HQ_ROOT is the brain repo this script lives in and ENGINE_ROOT is the body repo; in a
# one-repo shape they are the same checkout and the engine-side probes read it too.
ENGINE_ROOT = pathlib.Path(os.environ.get("VT_ENGINE_REPO", r"D:\example\engine-repo"))
ENGINE_REPO = os.environ.get("VT_ENGINE_REPO_SLUG", "your-account/your-engine-repo")
GH_ACCOUNT = os.environ.get("VT_GH_ACCOUNT", "")  # empty = use gh's active account

#: The snapshot pages whose `updated:` frontmatter is compared against the newest log entry.
SNAPSHOT_PAGES = ("wiki/status.md", "wiki/parallel-sessions.md")
LOG_PAGE = "wiki/log.md"

DENYLIST = HQ_ROOT / "firewall" / "denylist.txt"
SYNCED_HASH = HQ_ROOT / "firewall" / ".synced-hash"

#: The pages the disposition rule covers, and the date the rule took force. Entries older
#: than the epoch are grandfathered (retrofit is opportunistic, not owed).
LESSON_PAGES = ("wiki/feedback.md", "wiki/lessons-learned.md")
DISPOSITION_EPOCH = "2026-08-28"

_FRONT_UPDATED = re.compile(r"^updated:\s*(\d{4}-\d{2}-\d{2})\s*$", re.M)
_LOG_ENTRY = re.compile(r"^##\s*\[(\d{4}-\d{2}-\d{2})\]", re.M)
#: Any ISO date anywhere in a page's body — used to ask what a snapshot page SAYS, as
#: distinct from what its frontmatter CLAIMS.
_ANY_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")

_LESSON_HEAD = re.compile(r"^##[^\[\n]*\[(\d{4}-\d{2}-\d{2})\]\s*(.*)$")
_DISPOSITION = re.compile(r"^\s*→ (encoded|noted-only):\s*(\S.*)$")


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def fail(reason: str) -> dict:
    """The one shape a probe returns when it could not collect. Never a fabricated value."""
    return {"ok_to_collect": False, "error": reason}


def run(args: list[str], cwd: pathlib.Path | None = None, timeout: int = 30) -> str:
    """A read-only subprocess. Raises on failure; every caller turns that into a fact."""
    r = subprocess.run(args, cwd=str(cwd) if cwd else None, capture_output=True,
                       text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])} exited {r.returncode}: "
                           f"{(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout


def git(args: list[str], cwd: pathlib.Path, timeout: int = 30) -> str:
    return run(["git", "-C", str(cwd)] + args, timeout=timeout)


def gh(args: list[str], timeout: int = 30) -> str:
    """`gh`, with the personal account's token pinned explicitly.

    The workstation has two GitHub accounts logged in; whichever is 'active' is a machine
    state, not a fact about this venture. A probe that read the wrong account would report a
    404 as an absent repository."""
    env = dict(os.environ)
    if not env.get("GH_TOKEN") and GH_ACCOUNT:
        try:
            tok = subprocess.run(["gh", "auth", "token", "-u", GH_ACCOUNT],
                                 capture_output=True, text=True, timeout=10)
            if tok.returncode == 0 and tok.stdout.strip():
                env["GH_TOKEN"] = tok.stdout.strip()
        except Exception:                       # noqa: BLE001 - the caller reports the fact
            pass
    r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=timeout,
                       env=env)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])} exited {r.returncode}: "
                           f"{(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout


def hours_since(stamp: str) -> float | None:
    """Hours between an ISO-8601 instant and now, rounded to one decimal."""
    try:
        when = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    return round((now() - when).total_seconds() / 3600, 1)


def checkouts(root: pathlib.Path) -> list[dict]:
    """`[{path, branch, is_main_checkout}]` for a repo and every worktree attached to it."""
    out: list[dict] = []
    porcelain = git(["worktree", "list", "--porcelain"], root)
    current: dict = {}
    for line in porcelain.splitlines():
        if line.startswith("worktree "):
            if current:
                out.append(current)
            current = {"path": line[len("worktree "):].strip(), "branch": None}
        elif line.startswith("branch "):
            current["branch"] = line[len("branch "):].strip().replace("refs/heads/", "")
        elif line.strip() == "detached":
            current["branch"] = None
    if current:
        out.append(current)
    for i, wt in enumerate(out):
        wt["is_main_checkout"] = i == 0
    return out


# ---------------------------------------------------------------- the probes

def probe_ci_main() -> dict:
    """The latest completed run per workflow on the engine repo's default branch.

    The founding miss of the auditor role, mechanised: a red main went unread for five days
    because reading it was somebody's intention rather than somebody's step."""
    try:
        raw = gh(["run", "list", "-R", ENGINE_REPO, "--branch", "main", "--limit", "40",
                  "--json", "name,status,conclusion,createdAt,updatedAt,url,headSha"])
        runs = json.loads(raw)
    except Exception as e:                                  # noqa: BLE001
        return fail(f"could not read Actions runs for {ENGINE_REPO}: {e}")
    latest: dict[str, dict] = {}
    for r in sorted(runs, key=lambda r: r.get("createdAt") or ""):
        latest[r.get("name", "?")] = r          # newest per workflow wins
    workflows = {}
    for name, r in sorted(latest.items()):
        stamp = r.get("updatedAt") or r.get("createdAt") or ""
        workflows[name] = {
            "age_hours": hours_since(stamp) if stamp else None,
            "conclusion": r.get("conclusion"),
            "head_sha": (r.get("headSha") or "")[:12] or None,
            "status": r.get("status"),
            "updated_at": stamp or None,
            "url": r.get("url"),
        }
    not_green = sorted(n for n, w in workflows.items()
                       if w["status"] == "completed"
                       and w["conclusion"] not in ("success", "skipped", "neutral"))
    return {
        "branch": "main",
        "not_green": not_green,
        "ok_to_collect": True,
        "repo": ENGINE_REPO,
        "runs_seen": len(runs),
        "workflows": workflows,
    }


def probe_snapshot_staleness() -> dict:
    """The snapshot pages' `updated:` against the newest dated entry in the append-only log.

    A status page is a claim about where things stand; the log is the record of what happened.
    The gap between them is the only mechanical reading of "is the snapshot current"."""
    log_path = HQ_ROOT / LOG_PAGE
    if not log_path.exists():
        return fail(f"{LOG_PAGE} does not exist")
    dates = _LOG_ENTRY.findall(log_path.read_text(encoding="utf-8"))
    if not dates:
        return fail(f"{LOG_PAGE} contains no `## [YYYY-MM-DD]` entries to compare against")
    newest = max(dates)
    pages: dict[str, dict] = {}
    for rel in SNAPSHOT_PAGES:
        path = HQ_ROOT / rel
        if not path.exists():
            pages[rel] = {"error": "page does not exist", "ok_to_collect": False}
            continue
        m = _FRONT_UPDATED.search(path.read_text(encoding="utf-8"))
        if not m:
            pages[rel] = {"error": "frontmatter has no `updated:` date",
                          "ok_to_collect": False}
            continue
        updated = m.group(1)
        text = path.read_text(encoding="utf-8")
        # The BODY's own newest date, independent of the frontmatter's claim. Bumping
        # `updated:` without rewriting the page scored CLEAN until 2026-09-01, when an audit
        # found status.md claiming currency while its body still described a fleet three
        # image tags old. Frontmatter is what the page CLAIMS; this is what it SAYS.
        # FUTURE dates are excluded, and the exclusion is the whole trick: these pages carry
        # scheduled reminders (a token renewal in 2027), so a naive max() reported status.md
        # as 332 days AHEAD of the log — a confident answer about the wrong thing, which is
        # the exact failure class this probe was added to catch. Only a date that has already
        # happened can evidence what a page currently says.
        today = now().date().isoformat()
        body_dates = [d for d in _ANY_DATE.findall(text[m.end():]) if d <= today]
        body_newest = max(body_dates) if body_dates else None
        pages[rel] = {
            "body_days_behind_log": ((dt.date.fromisoformat(newest)
                                      - dt.date.fromisoformat(body_newest)).days
                                     if body_newest else None),
            "body_newest_date": body_newest,
            "days_behind_log": (dt.date.fromisoformat(newest)
                                - dt.date.fromisoformat(updated)).days,
            "ok_to_collect": True,
            "updated": updated,
        }
    return {
        "log_entries_seen": len(dates),
        "log_newest_entry": newest,
        "ok_to_collect": True,
        "pages": pages,
    }


def _unpushed_for(root: pathlib.Path) -> dict:
    branches: dict[str, dict] = {}
    listing = git(["for-each-ref", "--format=%(refname:short)%09%(upstream)%09"
                   "%(committerdate:iso-strict)", "refs/heads"], root)
    worktree_of = {}
    for wt in checkouts(root):
        if wt.get("branch"):
            worktree_of[wt["branch"]] = wt["path"]
    for line in listing.splitlines():
        if not line.strip():
            continue
        name, _, rest = line.partition("\t")
        upstream, _, committed = rest.partition("\t")
        count = int(git(["rev-list", "--count", name, "--not", "--remotes"], root).strip())
        if count == 0:
            continue
        branches[name] = {
            "checked_out_at": worktree_of.get(name),
            "has_upstream": bool(upstream.strip()),
            "last_commit": committed.strip() or None,
            "last_commit_age_hours": hours_since(committed.strip()) if committed.strip()
            else None,
            "unpushed_commits": count,
        }
    return branches


def probe_unpushed_branches() -> dict:
    """Local branches carrying commits that exist on no remote, in both repos.

    Branches are repo-wide, not worktree-wide: one query per repository covers every worktree
    attached to it, and each answer carries the worktree the branch is checked out in (or
    null) so the finding has an address. `has_upstream` is the discriminator the auditor's
    T1/T3 split turns on — pushing a branch that already has an upstream is bookkeeping;
    pushing one that does not may be publishing work that is mid-flight on purpose."""
    repos: dict[str, dict] = {}
    ok = True
    for label, root in (("hq", HQ_ROOT), ("engine", ENGINE_ROOT)):
        if not (root / ".git").exists():
            repos[label] = fail(f"{root} is not a git checkout")
            ok = False
            continue
        try:
            branches = _unpushed_for(root)
        except Exception as e:                              # noqa: BLE001
            repos[label] = fail(f"could not read branches in {root}: {e}")
            ok = False
            continue
        repos[label] = {"branches": branches, "ok_to_collect": True,
                        "unpushed_branch_count": len(branches)}
    return {"ok_to_collect": ok, "repos": repos}


def probe_checkout_drift() -> dict:
    """How far each repo's local `main` is from `origin/main`, and how stale that comparison
    is. No fetch: a probe that refreshed the remote ref would be measuring its own side
    effect, and the fetch age is the honest caveat on every number here."""
    repos: dict[str, dict] = {}
    ok = True
    for label, root in (("hq", HQ_ROOT), ("engine", ENGINE_ROOT)):
        if not (root / ".git").exists():
            repos[label] = fail(f"{root} is not a git checkout")
            ok = False
            continue
        try:
            counts = git(["rev-list", "--left-right", "--count", "main...origin/main"],
                         root).split()
            ahead, behind = int(counts[0]), int(counts[1])
            head = git(["rev-parse", "--abbrev-ref", "HEAD"], root).strip()
            fetch_head = pathlib.Path(git(["rev-parse", "--git-common-dir"], root).strip())
            if not fetch_head.is_absolute():
                fetch_head = (root / fetch_head).resolve()
            fetch_head = fetch_head / "FETCH_HEAD"
            fetch_age = (round((now().timestamp() - fetch_head.stat().st_mtime) / 3600, 1)
                         if fetch_head.exists() else None)
            dirty = bool(git(["status", "--porcelain"], root).strip())
            repos[label] = {
                "last_fetch_age_hours": fetch_age,
                "main_ahead_of_origin": ahead,
                "main_behind_origin": behind,
                "ok_to_collect": True,
                "current_branch": head,
                "working_tree_dirty": dirty,
            }
        except Exception as e:                              # noqa: BLE001
            repos[label] = fail(f"could not compare main with origin/main in {root}: {e}")
            ok = False
    return {"ok_to_collect": ok, "repos": repos}


def probe_merged_worktrees() -> dict:
    """Worktrees whose branch tip is already contained in `origin/main` — the litter the
    auditor's T1 tier is permitted to remove. An UNMERGED stray is reported, never removed,
    and this probe keeps the two apart by answering only the containment question."""
    repos: dict[str, dict] = {}
    ok = True
    for label, root in (("hq", HQ_ROOT), ("engine", ENGINE_ROOT)):
        if not (root / ".git").exists():
            repos[label] = fail(f"{root} is not a git checkout")
            ok = False
            continue
        try:
            trees = []
            for wt in checkouts(root):
                if wt["is_main_checkout"]:
                    continue
                merged = None
                if wt.get("branch"):
                    r = subprocess.run(
                        ["git", "-C", str(root), "merge-base", "--is-ancestor",
                         wt["branch"], "origin/main"],
                        capture_output=True, text=True, timeout=30)
                    merged = (r.returncode == 0) if r.returncode in (0, 1) else None
                trees.append({"branch": wt.get("branch"),
                              "merged_into_origin_main": merged,
                              "path": wt["path"]})
            repos[label] = {"ok_to_collect": True,
                            "merged_count": sum(1 for t in trees
                                                if t["merged_into_origin_main"] is True),
                            "worktrees": trees}
        except Exception as e:                              # noqa: BLE001
            repos[label] = fail(f"could not list worktrees in {root}: {e}")
            ok = False
    return {"ok_to_collect": ok, "repos": repos}


def probe_review_ledger() -> dict:
    """The engine repo's review ledger: how many lines of each type, and the newest date.

    Read from the checkout as it stands. The ledger arrives with the model-policy branch, so
    a main-branch checkout answering "no such file" is a true fact about this workstation,
    not a broken probe — which is why it reports the path it looked at."""
    path = ENGINE_ROOT / "reviews" / "ledger.jsonl"
    if not path.exists():
        return fail(f"{path} does not exist in the current engine checkout (the ledger "
                    "arrives with the model-policy work; this is a fact about the "
                    "checkout, not a collection failure of the ledger itself)")
    counts: dict[str, int] = {}
    dates: list[str] = []
    malformed: list[int] = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            malformed.append(n)
            continue
        kind = str(obj.get("type", "<untyped>"))
        counts[kind] = counts.get(kind, 0) + 1
        if isinstance(obj.get("date"), str):
            dates.append(obj["date"])
    return {
        "last_line_date": max(dates) if dates else None,
        "lines_by_type": dict(sorted(counts.items())),
        "malformed_line_numbers": malformed,
        "ok_to_collect": True,
        "path": str(path),
        "total_lines": sum(counts.values()) + len(malformed),
    }


def probe_firewall_denylist_sync() -> dict:
    """Does the denylist file match the hash recorded when the Actions secret was last set?

    The gap this closes: the file is edited here, the secret is set THERE, and nothing but a
    recorded hash connects the two. `never_synced` is a distinct answer from `mismatch` on
    purpose — one means the secret has never been set from this file, the other means the
    file moved after it was."""
    if not DENYLIST.exists():
        return fail(f"{DENYLIST} does not exist")
    current = hashlib.sha256(
        DENYLIST.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if not SYNCED_HASH.exists():
        return {"denylist_sha256": current, "ok_to_collect": True,
                "recorded_sha256": None, "state": "never_synced",
                "synced_hash_path": str(SYNCED_HASH)}
    stated = SYNCED_HASH.read_text(encoding="utf-8").strip()
    recorded = stated.split()[0] if stated else ""
    return {
        "denylist_sha256": current,
        "ok_to_collect": True,
        "recorded_sha256": recorded or None,
        "state": "match" if recorded == current else "mismatch",
        "synced_hash_path": str(SYNCED_HASH),
    }


def _scan_dispositions(text: str) -> list[dict]:
    """Every dated `## [YYYY-MM-DD] ...` entry in a lessons page, with its disposition.

    An entry runs from its heading to the next `## ` heading; a disposition is a line
    inside that span matching the fixed syntax `→ encoded: <path>` / `→ noted-only:
    <reason>` — nothing looser counts, because the marker is a machine contract first
    and prose second."""
    entries: list[dict] = []
    current: dict | None = None
    for line in text.split("\n"):
        head = _LESSON_HEAD.match(line)
        if head:
            current = {"date": head.group(1), "disposition": None, "target": None,
                       "title": head.group(2).strip() or "<untitled>"}
            entries.append(current)
            continue
        if line.startswith("## "):
            current = None          # an undated section ends the previous entry's span
            continue
        if current is not None and current["disposition"] is None:
            marker = _DISPOSITION.match(line)
            if marker:
                current["disposition"] = marker.group(1)
                current["target"] = marker.group(2).strip()
    return entries


def probe_lesson_dispositions() -> dict:
    """Dated lesson entries on or after the disposition epoch that carry no marker.

    The rule (kit doctrine, 2026-08-30): a lesson's terminal state is a diff — every
    entry ends `→ encoded: <path>` or `→ noted-only: <reason>`. The window is anchored
    at the RULE'S epoch, not at the last audit, on purpose: an unmarked entry must keep
    flagging at every close-out until someone closes it, and a since-last-audit window
    would let an ignored flag silently expire the moment the next audit ran. Whether an
    open loop matters, and whether a `noted-only` reason is honest, is the auditor's
    judgment — this probe only counts."""
    files: dict[str, dict] = {}
    ok = True
    open_total = 0
    for rel in LESSON_PAGES:
        path = HQ_ROOT / rel
        if not path.exists():
            files[rel] = fail(f"{rel} does not exist")
            ok = False
            continue
        in_scope = [e for e in _scan_dispositions(path.read_text(encoding="utf-8"))
                    if e["date"] >= DISPOSITION_EPOCH]
        open_loops = [{"date": e["date"], "title": e["title"]}
                      for e in in_scope if e["disposition"] is None]
        open_total += len(open_loops)
        files[rel] = {
            "encoded": sum(1 for e in in_scope if e["disposition"] == "encoded"),
            "entries_in_scope": len(in_scope),
            "noted_only": sum(1 for e in in_scope if e["disposition"] == "noted-only"),
            "ok_to_collect": True,
            "open_loops": open_loops,
        }
    return {"epoch": DISPOSITION_EPOCH, "files": files, "ok_to_collect": ok,
            "open_loop_count": open_total}


#: The guard scripts every mechanical layer is expected to reach. Claude Code wires them
#: as PreToolUse commands in settings.json (two layers ON PURPOSE — HARNESS.md §2):
#: USER (`~/.claude/settings.json`, machine-absolute; fires in whichever checkout you
#: wandered into; lives outside the repo) and PROJECT (`.claude/settings.json`,
#: `${CLAUDE_PROJECT_DIR}` paths; travels with the clone). Cursor wires them through
#: `.cursor/hooks.json` → `.cursor/hooks/bridge.cmd` → `scripts/cursor_hook_bridge.py`.
#: A missing unused adapter is a fact, not a fail; a present adapter whose targets are
#: missing is the founding miss (23 deniable commands, 0 denied).
USER_SETTINGS = pathlib.Path.home() / ".claude" / "settings.json"
EXPECTED_GUARDS = ("az_guard.py", "git_scope_guard.py", "merge_green_check.py")
CURSOR_HOOKS_REL = pathlib.Path(".cursor") / "hooks.json"
EXPECTED_CURSOR_BRIDGE_REL = pathlib.Path(".cursor") / "hooks" / "bridge.cmd"
EXPECTED_CURSOR_BRIDGE_PY_REL = pathlib.Path("scripts") / "cursor_hook_bridge.py"


def _guard_wiring_layer(settings_path: pathlib.Path, project_dir: pathlib.Path) -> dict:
    """One settings file's answer: which expected guards it wires, and do the scripts exist.

    A settings file that does not exist is a wiring FACT (nothing is wired at this layer),
    not a collection failure — a fresh clone genuinely has no user-level file, and reporting
    that as a broken probe would hide the exact gap this probe exists to show. A file that
    exists but cannot be PARSED is different: it silently disables every hook it declares,
    so that is reported as a per-layer collection failure with the reason attached.

    `${CLAUDE_PROJECT_DIR}` (and its `%CLAUDE_PROJECT_DIR%` spelling) is resolved against
    `project_dir` for the existence check only — that is what the harness substitutes at
    runtime, and an unresolved placeholder would report every project-level target as
    missing on every machine, including the ones where it works."""
    if not settings_path.exists():
        return {
            "guards": {script: {"wired": False} for script in EXPECTED_GUARDS},
            "not_armed": sorted(EXPECTED_GUARDS),
            "ok_to_collect": True,
            "settings_file_present": False,
            "settings_path": str(settings_path),
        }
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        # A settings file that cannot be parsed disables EVERY hook it declares, silently.
        return fail(f"{settings_path} could not be read: {e}")
    commands: list[str] = []
    for entry in (settings.get("hooks") or {}).get("PreToolUse") or []:
        for hook in entry.get("hooks") or []:
            if isinstance(hook.get("command"), str):
                commands.append(hook["command"])
    guards: dict[str, dict] = {}
    for script in EXPECTED_GUARDS:
        wired = [c for c in commands if script in c]
        entry: dict = {"wired": bool(wired)}
        if wired:
            cmd = wired[0]
            m = re.search(r'"([^"]+\.py)"|(\S+\.py)', cmd)
            target = (m.group(1) or m.group(2)) if m else None
            entry["target"] = target
            resolved = (target or "").replace("${CLAUDE_PROJECT_DIR}", str(project_dir)) \
                                     .replace("%CLAUDE_PROJECT_DIR%", str(project_dir))
            entry["target_exists"] = bool(target) and pathlib.Path(resolved).exists()
            entry["interpreter"] = cmd.split()[0] if cmd.split() else None
        guards[script] = entry
    return {
        "guards": guards,
        "not_armed": _not_armed(guards),
        "ok_to_collect": True,
        "settings_file_present": True,
        "settings_path": str(settings_path),
    }


def _not_armed(guards: dict[str, dict]) -> list[str]:
    return sorted(s for s, g in guards.items()
                  if not g["wired"] or not g.get("target_exists"))


def _claude_settings_path(project_dir: pathlib.Path) -> pathlib.Path:
    return project_dir / ".claude" / "settings.json"


def _command_points_at(cmd: str, expected_rel: pathlib.Path,
                       project_dir: pathlib.Path) -> bool:
    """True when a hooks.json command names expected_rel under project_dir."""
    raw = cmd.strip().strip('"')
    expected = (project_dir / expected_rel).resolve()
    candidate = pathlib.Path(raw)
    if not candidate.is_absolute():
        candidate = project_dir / raw
    try:
        return candidate.resolve() == expected
    except OSError:
        return _posix_hook_rel(raw) == expected_rel.as_posix()


def _posix_hook_rel(raw: str) -> str:
    """Strip a `./` prefix, not a `./` character set.

    `str.lstrip("./")` would turn `.cursor/...` into `cursor/...` and the
    correct D1 path would look wrong.
    """
    norm = raw.replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    return norm


def _cursor_event_wiring(settings: dict, project_dir: pathlib.Path) -> dict[str, dict]:
    """beforeShellExecution / beforeMCPExecution commands, and whether each
    names `.cursor/hooks/bridge.cmd`."""
    hooks = settings.get("hooks") or {}
    events: dict[str, dict] = {}
    for event in ("beforeShellExecution", "beforeMCPExecution"):
        commands = [
            entry["command"]
            for entry in hooks.get(event) or []
            if isinstance(entry, dict) and isinstance(entry.get("command"), str)
        ]
        events[event] = {
            "commands": commands,
            "points_at_expected_bridge": any(
                _command_points_at(c, EXPECTED_CURSOR_BRIDGE_REL, project_dir)
                for c in commands
            ),
        }
    return events


def _empty_stdin_residual(bridge_py: pathlib.Path) -> dict:
    """Run the Cursor bridge with empty stdin. Fail-open is the recorded residual.

    Fail-closed on empty stdin froze every command on Windows when the pipe
    dropped (conda `python.cmd`). A probe that treated allow as a wiring fail
    would force the freeze back in. This is a named fact, not a gate fail.
    """
    try:
        r = subprocess.run(
            [sys.executable, str(bridge_py)],
            input="",
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return fail(f"cursor bridge empty-stdin probe could not run: {e}")
    raw = (r.stdout or "").strip()
    try:
        body = json.loads(raw) if raw else {}
    except json.JSONDecodeError as e:
        return fail(f"cursor bridge empty-stdin stdout was not JSON: {e}")
    permission = body.get("permission") if isinstance(body, dict) else None
    return {
        "ok_to_collect": True,
        "permission": permission,
        "recorded_as": "residual",
        "reason": (
            "empty/unreadable stdin fail-opens so a Windows pipe gap cannot freeze "
            "the agent; do not flip to deny without a live Windows test"
        ),
        "watched": permission == "allow",
    }


def _cursor_guard_wiring_layer(project_dir: pathlib.Path) -> dict:
    """Cursor project layer: hooks.json command path, bridge, and the three guards.

    Cursor does not name each guard in hooks.json. It names the bridge. A layer is
    armed when beforeShellExecution points at `.cursor/hooks/bridge.cmd`, that
    file exists, `scripts/cursor_hook_bridge.py` exists, and each guard script
    exists. The extra `hooks/` directory is load-bearing: the `.cmd` resolves
    `%~dp0..\\..\\scripts\\` only from `.cursor/hooks/`.
    """
    hooks_path = project_dir / CURSOR_HOOKS_REL
    if not hooks_path.exists():
        return {
            "empty_stdin_residual": {"present": False, "ok_to_collect": True},
            "events": {},
            "guards": {script: {"wired": False} for script in EXPECTED_GUARDS},
            "hooks_file_present": False,
            "kind": "cursor",
            "not_armed": sorted(EXPECTED_GUARDS),
            "ok_to_collect": True,
            "scope": "travels with the clone — Cursor beforeShell/beforeMCP",
            "settings_path": str(hooks_path),
        }
    try:
        settings = json.loads(hooks_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return fail(f"{hooks_path} could not be read: {e}")

    events = _cursor_event_wiring(settings, project_dir)
    bridge_cmd = project_dir / EXPECTED_CURSOR_BRIDGE_REL
    bridge_py = project_dir / EXPECTED_CURSOR_BRIDGE_PY_REL
    cmd_exists = bridge_cmd.is_file()
    py_exists = bridge_py.is_file()
    shell = events.get("beforeShellExecution") or {}
    shell_chain = (
        bool(shell.get("points_at_expected_bridge")) and cmd_exists and py_exists
    )
    guards: dict[str, dict] = {}
    for script in EXPECTED_GUARDS:
        target = project_dir / "scripts" / script
        exists = target.is_file()
        guards[script] = {
            "target": str(target),
            "target_exists": exists,
            "via": "cursor_hook_bridge",
            "wired": shell_chain and exists,
        }
    return {
        "bridge_cmd_exists": cmd_exists,
        "bridge_cmd_path": str(bridge_cmd),
        "bridge_script_exists": py_exists,
        "bridge_script_path": str(bridge_py),
        "empty_stdin_residual": (
            _empty_stdin_residual(bridge_py) if py_exists
            else {"present": False, "ok_to_collect": True}
        ),
        "events": events,
        "expected_bridge_rel": EXPECTED_CURSOR_BRIDGE_REL.as_posix(),
        "guards": guards,
        "hooks_file_present": True,
        "kind": "cursor",
        "not_armed": _not_armed(guards),
        "ok_to_collect": True,
        "scope": "travels with the clone — Cursor beforeShell/beforeMCP",
        "settings_path": str(hooks_path),
    }


def probe_guard_wiring() -> dict:
    """Are the guards actually WIRED — at each adapter layer — and do their scripts exist?

    The founding fact: the subscription guard sat inert through **23 commands that should
    have been denied and 0 were**, because the settings file lived in a commit the working
    branch predated. Wiring it at user level fixed that and moved the blind spot — the file
    is outside both repos, so this probe is the only reader that can exist. Phase 6a then
    added the PROJECT layer back, wired relative to `${CLAUDE_PROJECT_DIR}`, so a fresh
    clone is guarded too.

    Cursor is a third layer, not a second Claude settings file. A Cursor-only stamp
    that followed the adapter still failed this probe when it only read
    `.claude/settings.json`. Layers are reported separately because they answer
    different questions: `claude_user` is "is THIS machine belt-and-suspenders",
    `claude_project` / `cursor_project` are "does a cold start elsewhere get guards
    at all". A missing unused adapter is a fact. A present adapter with missing
    targets is the miss.

    What it CANNOT prove: that the harness actually invokes the hook at runtime.
    That is not observable from here. What it CAN prove is the failure mode that
    has actually bitten: a hook that is absent, or one whose target script is
    missing, or a Cursor `hooks.json` that points at a `bridge.cmd` that is not
    where the shipped file says. `interpreter` is reported on Claude layers
    because a missing interpreter exits 127 and is NON-blocking (silent).
    """
    return _probe_guard_wiring_at(HQ_ROOT)


def _probe_guard_wiring_at(root: pathlib.Path) -> dict:
    layers = {
        "claude_project": _guard_wiring_layer(_claude_settings_path(root), root),
        "claude_user": _guard_wiring_layer(USER_SETTINGS, root),
        "cursor_project": _cursor_guard_wiring_layer(root),
    }
    layers["claude_project"]["scope"] = "travels with the clone — Claude PreToolUse"
    layers["claude_user"]["scope"] = "this machine only — invisible to any other checkout"
    present: list[str] = []
    unarmed_present: list[str] = []
    # Project adapters only. A missing unused adapter is omitted, not a fail.
    for name in ("claude_project", "cursor_project"):
        layer = layers[name]
        if not layer.get("ok_to_collect"):
            unarmed_present.append(name)
            continue
        if not (layer.get("settings_file_present") or layer.get("hooks_file_present")):
            continue
        present.append(name)
        if layer.get("not_armed"):
            unarmed_present.append(name)
    return {
        "does_not_prove": "that the harness invokes the hook at runtime",
        "layers": layers,
        "ok_to_collect": all(v.get("ok_to_collect") for v in layers.values()),
        "present_project_layers": present,
        "proves": "the hook is declared and its script exists, per adapter layer",
        "unarmed_present_project_layers": unarmed_present,
    }


PROBES = {
    "checkout_drift": probe_checkout_drift,
    "guard_wiring": probe_guard_wiring,
    "ci_main": probe_ci_main,
    "firewall_denylist_sync": probe_firewall_denylist_sync,
    "lesson_dispositions": probe_lesson_dispositions,
    "merged_worktrees": probe_merged_worktrees,
    "review_ledger": probe_review_ledger,
    "snapshot_staleness": probe_snapshot_staleness,
    "unpushed_branches": probe_unpushed_branches,
}


def collect(names: list[str] | None = None) -> dict:
    """Run each requested probe, catching anything it did not catch itself.

    A probe that raises is reported as a probe that could not collect - never as a probe
    that found nothing, and never as a missing key. One broken instrument must not take the
    whole panel down with it."""
    chosen = names or sorted(PROBES)
    probes: dict[str, dict] = {}
    for name in sorted(chosen):
        fn = PROBES.get(name)
        if fn is None:
            probes[name] = fail(f"no such probe (known: {', '.join(sorted(PROBES))})")
            continue
        try:
            probes[name] = fn()
        except Exception as e:                              # noqa: BLE001
            probes[name] = fail(f"probe raised {type(e).__name__}: {e}")
    return {
        "collected_at": now().replace(microsecond=0).isoformat(),
        "engine_repo_path": str(ENGINE_ROOT),
        "hq_repo_path": str(HQ_ROOT),
        "probes": probes,
        "probes_failed": sorted(k for k, v in probes.items()
                                if not v.get("ok_to_collect")),
        "schema": 1,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", action="append", dest="probes",
                    help="run only this probe (repeatable); default is all of them")
    ap.add_argument("--indent", type=int, default=2)
    args = ap.parse_args(argv)
    payload = collect(args.probes)
    print(json.dumps(payload, sort_keys=True, indent=args.indent))
    return 0                # the pack always exits 0: a failed probe is a FACT, not an error


if __name__ == "__main__":
    sys.exit(main())

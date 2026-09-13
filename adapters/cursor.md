# Adapter: Cursor

**Status: VERIFIED 2026-09-01 on the origin, native Cursor Agent, Windows.** Rules files
remain as below. Enforcement hooks are no longer unverified — see the section after
Install.

## Install

1. **Rules files MUST be `.mdc`, with frontmatter.** A plain `.md` file in
   `.cursor/rules/` is **silently ignored** — no frontmatter, no `description`/`globs`/
   `alwaysApply`, the rules system skips it. An adapter written as `.md` would look
   installed, be committed, be reviewed, and never load — the "instrument that does not
   run" failure class, one file extension away. Install
   `reference/cursor/project-rules.mdc` → `.cursor/rules/project-rules.mdc` (always-on
   pointer rule) and `reference/cursor/outside-the-lane.mdc` →
   `.cursor/rules/outside-the-lane.mdc` (fence tripwire), re-pointing their EXAMPLE
   rows/globs at your project's files.
2. **Point Cursor at the real constitution — verify what `AGENTS.md` is first.** Cursor
   reads `AGENTS.md` natively, which makes it a trap when that file has a different job
   (in the origin it is the install runbook, not the constitution). If the file does not
   yet exist, install `templates/AGENTS.project.md` as `AGENTS.md`. Do not overwrite an
   existing `AGENTS.md` that already has another job. The pointer rule names the
   governing documents explicitly instead.
3. **`reference/cursor/BUGBOT.md` → `.cursor/BUGBOT.md`**, with your project's doctrine
   list swapped in. Read its own first paragraph: there is **no severity or finding-type
   filter** at repo or project level — severity appears in Bugbot's output but is not
   configurable, so this file is *prose handed to a reviewer*, not a setting. A policy
   that reads like a setting but is only a suggestion gets trusted too far; the file says
   so about itself.
4. **Bugbot settings** (owner-side, in the vendor UI): Incremental Review is already the
   DEFAULT (nothing to enable). Set Trigger Mode to **once per PR** — the origin measured
   the alternative: every-push triggering multiplied ~33 PRs into an estimated 80–100
   reviews and burned the credit allowance in two days. Fix findings **in the PR that
   raised them** — follow-up PRs pay for every finding twice and read to the reviewer as
   nothing ever being fixed. Autofix stays **OFF** (external reviewer is input, never
   author). Remote skip is **not** "we ran a review": GitHub Bugbot skips the remote pass
   only when local `/review-bugbot` stored a patch ID for the **same** diff. A generic
   code-reviewer pass does not set that ID. Sequence for Cursor-as-master: finish the
   branch → `/review-bugbot` on that exact diff → `gh pr create` with **no extra commits
   in between**.
5. **The lane** (if a human drives Cursor beside a dispatched-agent master): branch prefix
   `cursor/<task>`, the brain repo read-only, default fence on fast-visual-loop surfaces,
   `/review-bugbot` on the exact diff before `gh pr create`. The one-writer rule is
   tool-agnostic — the master treats the lane's held paths exactly like a worker's fence.
   Workers and the lane **never merge**. When the owner has delegated routine Merge
   (`spec/operating-model.md` invariant 3), the **standing master** squash-merges when
   checks are success / skipped / neutral. Publish is never delegated.

## Cursor-as-master — spawn, review seats, merge

**Task spawn: pin a slug, never inherit.** When the master chat is a costly model, Cursor
Task `inherit` makes every worker cost the same. Pin an explicit slug from the
**consuming project's** vendor adapter table (its `docs/MODELS.md` or equivalent). Do not
write those vendor names into `.claude/agents/*.md` `model:` fields — the model-policy CI
still checks Claude tokens (`haiku` / `sonnet` / `opus`). Keep slugs in the project's
adapter table; the kit does not ship a required starting-card for any vendor.

**Code-cyber seat.** On Cursor-as-master, the panel's code-cyber seat is
`/review-security`, at the same cadence as the panel. Do not also run a second prose
cyber lens on that PR. Required outcome: **findings** · **clean** · **blocked**. Blocked
is an owner ping; a silent empty report is not clean. This is a git-diff review, not
cloud-estate coverage.

**Done (Cursor-as-master), before `gh pr create`:**

1. `/review-security` on the branch diff (the cyber seat — outcome named above).
2. `/review-bugbot` on that **exact** diff (the patch ID that makes GitHub skip remote).
3. `gh pr create` with no extra commits after step 2.
4. If Merge is delegated: squash-merge when checks are success / skipped / neutral.
   Workers still never merge. Publish stays the owner.

## Enforcement hooks — verified 2026-09-01 on the origin (native Cursor Agent, Windows)

Cursor **does** have pre-execution hooks: `.cursor/hooks.json` `beforeShellExecution` and
`beforeMCPExecution`. They are **not** Claude Code's PreToolUse; `.claude/settings.json`
does not fire in native Cursor Agent (live unpinned `az account show` ran until this
adapter was wired).

Install:

- `reference/cursor/hooks.json` → `.cursor/hooks.json`
- `reference/cursor/bridge.cmd` → `.cursor/hooks/bridge.cmd`
- `reference/cursor/hook_bridge.py` → `scripts/cursor_hook_bridge.py` next to the three
  guards

The extra `hooks/` directory is **load-bearing**. The shipped `hooks.json` calls
`.cursor/hooks/bridge.cmd`, and the `.cmd` resolves the bridge with
`%~dp0..\..\scripts\`, which only lands on the repo `scripts/` folder from
`.cursor/hooks/`. Putting `bridge.cmd` in `.cursor/` (one level up) produces a hook
that never fires — the instrument-that-does-not-run class.

The `.cmd` wrapper is **also load-bearing on Windows**: `python scripts/...` as the hook
command uses conda's `python.cmd`, which drops piped stdin, and the hook then sees an
empty payload. Call `python.exe`.

The bridge always prints a Cursor `{permission: allow|deny}` object. Silence is invalid
JSON; with `failClosed: true` that would block every command. Azure MCP is refused by
server name (origin posture: unused; `az --subscription` is the path).

Live on the origin HQ checkout: unpinned `az account show` refused; pinned
`--subscription "Azure Sub.1"` allowed.

## Coverage

**REQUIRED** — stand-up is incomplete without this on Cursor (mechanical rows must be
armed at the Cursor project layer; doctrine rows you personally hold). **IF-AVAILABLE**
— only when that surface is opted in (vendor review, CI, MCP).

| Guarantee | Gate | Mechanical | Standalone-checkable | Doctrine-only |
|---|---|---|---|---|
| az pins `--subscription` | REQUIRED | **yes** — `beforeShellExecution` via the bridge (verified 2026-09-01) | yes — pipe payload to `az_guard.py` | residual: empty/unreadable stdin fail-opens (Windows pipe gap); named by the wiring probe, not a gate fail |
| Destructive git names its repo | REQUIRED | **yes** — same | yes — `git_scope_guard.py` | same residual |
| Merge only on green checks | REQUIRED | **yes** — same; a delegated master squash-merge still goes through this guard; a merge clicked in GitHub never does | yes — `merge_green_check.py` | web-UI merge is outside the hook |
| Azure MCP unused | IF-AVAILABLE | **yes** — `beforeMCPExecution` denies by server name | n/a | origin posture |
| CI gates (docs contract, ledger, firewall) | IF-AVAILABLE | **yes** — server-side, tool-independent | n/a | — |
| Fence awareness (rules in context) | IF-AVAILABLE | partial — `.mdc` rules inject the fence text when matching files are in context; **a tripwire is a reminder, not enforcement**, and attachment-on-context is not attachment-on-write | no | **yes** |
| Review policy (must-fix bar, fail-open-enumeration hunt) | IF-AVAILABLE | no — `BUGBOT.md` is prose to a reader, not a filter. Local `/review-bugbot` is what stores the patch ID GitHub uses to skip remote | no | **yes** |
| Code-cyber seat (`/review-security`) | IF-AVAILABLE | no — git-diff review, not a hook | the command's findings · clean · blocked | **yes** (do not also run a prose cyber lens) |
| Wiki protocol / commit protocol / report contract | REQUIRED | no | staleness + dispositions via `harness_probes.py` | **yes** |
| Keeping current (container freshness / canary) | IF-AVAILABLE | **yes** when STANDUP Question 3 copied the chassis (`adapters/github-azure.md`) | the rule tests | doctrine until then |

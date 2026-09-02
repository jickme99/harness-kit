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
   `reference/cursor/project-rules.mdc` (always-on pointer rule) and
   `reference/cursor/outside-the-lane.mdc` (fence tripwire) into `.cursor/rules/`,
   re-pointing their EXAMPLE rows/globs at your project's files.
2. **Point Cursor at the real constitution — verify what `AGENTS.md` is first.** Cursor
   reads `AGENTS.md` natively, which makes it a trap when that file has a different job
   (in the origin it is the install runbook, not the constitution). The pointer rule names
   the governing documents explicitly instead.
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
   nothing ever being fixed.
5. **The lane** (if a human drives Cursor beside a dispatched-agent master): branch prefix
   `cursor/<task>`, the brain repo read-only, default fence on fast-visual-loop surfaces,
   local Bugbot review before push. The one-writer rule is tool-agnostic — the master
   treats the lane's held paths exactly like a worker's fence.

## Enforcement hooks — verified 2026-09-01 on the origin (native Cursor Agent, Windows)

Cursor **does** have pre-execution hooks: `.cursor/hooks.json` `beforeShellExecution` and
`beforeMCPExecution`. They are **not** Claude Code's PreToolUse; `.claude/settings.json`
does not fire in native Cursor Agent (live unpinned `az account show` ran until this
adapter was wired).

Install `reference/cursor/hooks.json` and `reference/cursor/bridge.cmd` into
`.cursor/`, and `reference/cursor/hook_bridge.py` into `scripts/cursor_hook_bridge.py`
next to the three guards. The `.cmd` wrapper is **load-bearing on Windows**:
`python scripts/...` as the hook command uses conda's `python.cmd`, which drops piped
stdin, and the hook then sees an empty payload. Call `python.exe`.

The bridge always prints a Cursor `{permission: allow|deny}` object. Silence is invalid
JSON; with `failClosed: true` that would block every command. Azure MCP is refused by
server name (origin posture: unused; `az --subscription` is the path).

Live on the origin HQ checkout: unpinned `az account show` refused; pinned
`--subscription "Azure Sub.1"` allowed.

## Coverage

| Guarantee | Mechanical | Standalone-checkable | Doctrine-only |
|---|---|---|---|
| az pins `--subscription` | **yes** — `beforeShellExecution` via the bridge (verified 2026-09-01) | yes — pipe payload to `az_guard.py` | residual: empty/unreadable stdin fail-opens (Windows pipe gap) |
| Destructive git names its repo | **yes** — same | yes — `git_scope_guard.py` | same residual |
| Merge only on green checks | **yes** — same; the owner's Merge gate covers the web UI | yes — `merge_green_check.py` | a merge clicked in GitHub never passes a local guard |
| Azure MCP unused | **yes** — `beforeMCPExecution` denies by server name | n/a | origin posture |
| CI gates (docs contract, ledger, firewall) | **yes** — server-side, tool-independent | n/a | — |
| Fence awareness (rules in context) | partial — `.mdc` rules inject the fence text when matching files are in context; **a tripwire is a reminder, not enforcement**, and attachment-on-context is not attachment-on-write | no | **yes** |
| Review policy (must-fix bar, fail-open-enumeration hunt) | no — `BUGBOT.md` is prose to a reader, not a filter | no | **yes** |
| Wiki protocol / commit protocol / report contract | no | staleness + dispositions via `harness_probes.py` | **yes** |

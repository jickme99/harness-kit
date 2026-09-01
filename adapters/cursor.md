# Adapter: Cursor

**Status: CONFIGURED FROM VENDOR DOCUMENTATION, partially exercised.** The origin project
installed this adapter and validated the file formats against Cursor's own docs (three
plan-breaking corrections came out of that check — below). What has NOT been verified is
marked **unverified**, per row, in the coverage table. Vendor policy note: enabling
Bugbot sends repository content to the vendor — Question 2 in `STANDUP.md` applies
(personal repos: owner's call; corporate repos: recorded IT approval BEFORE enablement).

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

## Enforcement hooks — what the reference files establish, and no more

The origin's Cursor adapter contains **no enforcement hooks**: it is rules files (context
injection), Bugbot policy prose, and lane doctrine. From the reference files alone we
CANNOT establish that Cursor offers a pre-execution hook equivalent to Claude Code's
PreToolUse, and this adapter **does not claim hook support** for the three guards.
**Unverified:** whether any Cursor mechanism (hooks, extensions, or its agent runtime) can
block a shell command pre-execution against the guards' stdin contract. Until someone
verifies that and updates this table, the guards on Cursor are **standalone-checkable
only**: run them as pre-flight checks (`spec/guards.md` §standalone fallback), and carry
the rules as doctrine.

## Coverage

| Guarantee | Mechanical | Standalone-checkable | Doctrine-only |
|---|---|---|---|
| az pins `--subscription` | **unverified** — no known pre-execution hook surface | yes — pipe payload to `az_guard.py` before running | **yes** (the pointer rule states the rule) |
| Destructive git names its repo | **unverified** — same | yes — `git_scope_guard.py` | **yes** |
| Merge only on green checks | **unverified** — same; the owner's Merge gate covers it in practice (the lane never merges) | yes — `merge_green_check.py` | **yes** |
| CI gates (docs contract, ledger, firewall) | **yes** — server-side, tool-independent | n/a | — |
| Fence awareness (rules in context) | partial — `.mdc` rules inject the fence text when matching files are in context; **a tripwire is a reminder, not enforcement**, and attachment-on-context is not attachment-on-write | no | **yes** |
| Review policy (must-fix bar, fail-open-enumeration hunt) | no — `BUGBOT.md` is prose to a reader, not a filter | no | **yes** |
| Wiki protocol / commit protocol / report contract | no | staleness + dispositions via `harness_probes.py` | **yes** |

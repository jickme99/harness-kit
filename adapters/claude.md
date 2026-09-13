# Adapter: Claude Code

**Status: PROVEN.** This is the harness the kit was extracted from; every mechanical row
below ran live for weeks in the origin project.

## Install

1. Guards to `scripts/`, then `reference/claude/settings.json` → `.claude/settings.json`.
   This is the PROJECT layer: `${CLAUDE_PROJECT_DIR}` paths, travels with every clone.
2. **Add the USER layer too on any workstation that touches more than one project or
   tenant**: wire the same three scripts in `~/.claude/settings.json` with
   machine-absolute paths. Reason (`spec/guards.md`): the project layer lives in the
   checked-out COMMIT — a worktree branched before it landed is silently unguarded. The
   az and git hazards are cross-project; wire the guard where the MISTAKE can happen.
   Double execution is deliberate and free.
3. Role files to `.claude/agents/` (from `reference/claude/role-template.md` and the two
   function-role patterns). `CLAUDE.md` is the pointer stub (`templates/CLAUDE.project.md`);
   the constitution is `HARNESS.md`.
4. Verify with STANDUP's gate: contract tests + `harness_probes.py --probe guard_wiring` +
   a live negative test. The probe reports Claude and Cursor layers separately — a
   Claude-only stamp with Cursor hooks absent is a fact, not a fail. It honestly reports
   what it cannot prove — that the harness invokes hooks at runtime — which is what the
   live test is for.

Known residual (recorded, not fixed): hooks invoke bare `python`. A missing script exits 2
and BLOCKS (loud); a missing INTERPRETER exits 127, which is NON-blocking — the silent
failure mode. The probe reports the interpreter rather than assuming it.

One more, from the origin's own testing: the Claude Code **extension** inside another IDE
is a SUBSET of the harness. The full harness — hooks, settings, subagents, guards — runs
via the `claude` CLI in a terminal. Anything that assumes the desktop app is a bug in the
harness, not a constraint on the operator.

## Coverage

**REQUIRED** — stand-up is incomplete without this on Claude Code (mechanical rows must
be armed at the Claude **project** layer). **IF-AVAILABLE** — only when that surface is
opted in (user-level hooks, CI, two-repo firewall). The user-level Claude layer is
IF-AVAILABLE: wire it on workstations that touch more than one project; the gate does
not fail a stamp that skipped it.

| Guarantee | Gate | Mechanical | Standalone-checkable | Doctrine-only |
|---|---|---|---|---|
| az pins `--subscription` | REQUIRED | **yes** — PreToolUse hook (project + optional user layer) | yes — pipe payload to `az_guard.py` | fallback |
| Destructive git names its repo | REQUIRED | **yes** — PreToolUse hook | yes — pipe payload to `git_scope_guard.py` | fallback |
| Merge only on green checks | REQUIRED | **yes** — PreToolUse hook (needs `gh` auth) | yes — pipe payload to `merge_green_check.py` | fallback |
| CI gates (docs contract, ledger presence, model policy, firewall) | IF-AVAILABLE | **yes** — server-side, harness-independent (GitHub Actions) | n/a | — |
| Wiki append-only + auto-write | REQUIRED | no | partially — `harness_probes.py` measures staleness and lesson dispositions after the fact | **yes** |
| Commit protocol (never auto force-push / history rewrite) | REQUIRED | no | no | **yes** |
| One-writer-per-path fences | REQUIRED | no (frontmatter is machine-readable; the enforcement hook has not met its evidence bar — `spec/graduation.md`) | partially — role frontmatter is parseable | **yes** |
| Report + uncertainty contracts | REQUIRED | no | no | **yes** |
| Two-repo firewall promotion discipline | IF-AVAILABLE | no (the CI firewall polices entry to the body repo; promotion itself is a human act) | no | **yes** |
| Keeping current (container freshness / canary) | IF-AVAILABLE | **yes** when STANDUP Question 3 copied the chassis (`adapters/github-azure.md`) | the rule tests under `reference/keeping-current/tests/` | doctrine until then |

Read the last column as the promises you are personally holding even on the proven
harness.

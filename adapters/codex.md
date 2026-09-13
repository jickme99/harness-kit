# Adapter: Codex

**Status: UNTESTED.** No project has run this harness under Codex. Everything below is a
plan derived from the spec, not a record of anything that has worked. Treat every
"should" in this file as a hypothesis until a real cold start has exercised it — and when
one has, rewrite this file from what actually happened. (The kit's own validation
experiment is exactly that: a fresh project stood up from this repo on a non-Claude
agent. See `TODO.md`.)

## The plan (hypothesis, not record)

1. **Constitution:** Codex reads `AGENTS.md` natively. In a kit-stamped project the
   constitution is `HARNESS.md`, so `AGENTS.md` should be (or begin with) a pointer to it
   — install `templates/AGENTS.project.md` as `AGENTS.md` (the same pattern as
   `CLAUDE.md` / `templates/CLAUDE.project.md`). **Caution from the origin:** verify what
   an existing repo's `AGENTS.md` already is before repurposing it; in the origin it was
   the install runbook, and pointing an agent at it as the constitution would hand it the
   wrong document with confidence.
2. **Guards:** assume NO pre-execution hook surface until verified. The guards work as
   pre-flight checks on any harness (`spec/guards.md`): pipe the candidate command in as
   the stdin JSON contract; any stdout is a refusal. The constitution text must carry the
   obligation to run the check — that is doctrine, and it is what the coverage table
   admits.
3. **Contract tests:** fully portable (stdlib + pytest); run them in the project checkout
   as the stand-up gate regardless of tool.
4. **CI gates:** server-side and tool-independent; they work identically.
5. **Review:** Codex's PR-review surface (if enabled — vendor question in `STANDUP.md`
   applies, and for corporate repos it is often the only vendor IT permits) plays the
   external-reviewer role from `spec/review.md`: input, never an author; findings deduped
   into the PR's review package.

## Coverage

**REQUIRED** — stand-up is incomplete without this on Codex (today: contract tests plus
the doctrine to actually run the pre-flight). **IF-AVAILABLE** — only when that surface
is opted in (CI, vendor review). No project hook layer is expected; the wiring probe
reporting Claude and Cursor configs absent is a fact, not a fail.

| Guarantee | Gate | Mechanical | Standalone-checkable | Doctrine-only |
|---|---|---|---|---|
| az pins `--subscription` | REQUIRED | **untested** — assume no | yes — pipe payload to `az_guard.py` | **yes** |
| Destructive git names its repo | REQUIRED | **untested** — assume no | yes — `git_scope_guard.py` | **yes** |
| Merge only on green checks | REQUIRED | **untested** — assume no | yes — `merge_green_check.py` | **yes** |
| CI gates | IF-AVAILABLE | **yes** — server-side, tool-independent | n/a | — |
| Everything else (fences, wiki, commit, report contracts) | REQUIRED | no | probes where they run | **yes** |
| Keeping current (container freshness / canary) | IF-AVAILABLE | **yes** when STANDUP Question 3 copied the chassis (`adapters/github-azure.md`); server-side, tool-independent | the rule tests | doctrine until then |

On this harness, until someone upgrades a row with evidence, you are personally holding
every promise except the CI gates.

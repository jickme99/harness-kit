# Spec: versioning (the version-steward)

Dependency and runtime currency as a standing FUNCTION role with mechanical instruments —
because staleness is a silence problem: nothing goes red when a fix ships upstream and
nobody takes it. Reference role file: `reference/claude/version-steward.md`.

## The invariants (MUST)

1. **Instruments get named readers.** Every continuous measurement — dependency-update
   bots, security alerts, a CI dependency audit, deployment/image drift metrics — has ONE
   role designated as its reader, in writing. The founding failure: a fleet-drift metric
   measured everything and was read by nobody. And the reader is itself an instrument:
   the harness-auditor verifies the steward ran within cadence and that no lane is
   backing up.
2. **Three lanes, by risk shape:**
   - **Lane 1 — security: fast.** Security updates batch into one branch, run the FULL
     suite, and go through the Merge gate promptly. A security PR older than one sweep is
     a backlog finding.
   - **Lane 2 — minors/patches: bundled monthly.** Grouped updates ride one branch per
     cycle. No urgency, no drift past a month; a skipped month is the lane backing up.
   - **Lane 3 — MAJORS: never automatic.** Every major becomes a dispatched job: its own
     branch, real testing **including the mandatory fresh-install path**, and a
     plain-English break-risk note the owner can read (what changes, what could break,
     what was tested, what rollback looks like). The canonical lesson: a `>=` major pin
     once broke only fresh installs while every existing environment stayed green —
     **majors break the machines you do NOT have.**
3. **Machine-level tooling staleness is report-only** — the fix path is the operator's
   OS/package manager, never a repo PR.
4. **Identify credentials by their OWN properties, never by their position in a listing.**
   The steward reads its instruments through an API token; on a machine with multiple
   accounts, "the active account" and "the first entry" are guesses. The recorded cost:
   a steward once read the wrong account's token scopes and requested an owner action
   that could not be performed. Pin the identity per call.
5. **The kit itself is a dependency of every stamped project.** The project's steward
   compares its kit-version stamp (`kit-manifest.json`) against the current kit release
   in its sweep: kit bug-fixes flow lane 1; new kit components flow lane 3 — offered with
   a what-it-adds note, never automatic. **Updates arrive as PRs through the project's own
   Merge gate — never pushed** — and a DECLINED upgrade is kit feedback, not a compliance
   failure.

## Mechanics (reference)

Dependabot config (security immediate; grouped monthly minors; individual majors), repo
security alerts, a kept CI dependency-audit job, and the drift probe — with one worked
exception recorded in the role file: ecosystems whose pin file only moves by wholesale
regeneration (a constraints file) disable per-package bot updates and substitute a monthly
regenerate-and-read-the-diff act, keeping lane 1 intact via the security exemption. A bot
also REGENERATES PR bodies on rebase and silently deletes human annotations written there
(measured: an exemption count went 2 → 0 across a rebase) — a break-risk note needs a
durable home, not a PR body.

## What an implementing agent must achieve

The lanes and the reader-assignment rule are doctrine plus ordinary CI/bot configuration —
portable to any harness. What must survive re-implementation: the three-lane risk split,
the fresh-install test on majors, the named-reader table, and the kit-as-dependency sweep.

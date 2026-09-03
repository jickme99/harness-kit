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

## Kit versions and the poll (MUST)

The kit repo is the source of truth. Each stamp records where it started. The two are
compared by **version**, not by hoping someone noticed a hash change.

- **`kit_version`** lives in `kit-manifest.json` (generated; required). Scheme: calendar
  line `YYYY.MM` plus a patch (`2026.09`, `2026.09.1`, …). Bump it on every merge a
  consumer should notice. Git tags match the version string.
- **`CHANGELOG.md`** is the poll surface: what changed, who it applies to, lane 1 vs
  lane 3. `TODO.md` is the gap list — not a release log.
- **Poll-from-project is the primary path.** Any project, any IDE, no write access to
  consumers required. The kit master still decides what is *in* the kit; the project
  master still decides what is *applied*. Kit-opens-upgrade-PRs (the steward at consumer
  #2) is later automation, not a substitute for a project that can read the changelog.

### Poll recipe (in the consuming project)

A project with no `kit-manifest.json` cannot poll. Stamp first (`STANDUP.md` step 5).

1. **Read local version:**
   ```sh
   python -c "import json; print(json.load(open('kit-manifest.json'))['kit_version'])"
   ```
2. **Fetch the kit changelog and current version** from the kit repo on GitHub (private:
   use an authenticated `gh` or a local clone of harness-kit — raw URLs will 404). Read
   `CHANGELOG.md` and `kit-manifest.json`'s `kit_version` on `main`.
3. **List entries newer than local `kit_version`.** Default is **consider** (the entry
   applies until proven otherwise). **Applies to** is a hint, not a skip-allowlist: the
   five keys in `CHANGELOG.md` (every stamp / Claude / Cursor / Codex / optional) plus any
   conditional prose (`every stamp that installed merge_green_check.py`) are not a closed
   set. A value you do not recognise, or a condition you have not checked, is **not** a
   skip — skipping a lane-1 fix because the sentence did not match a worked example is
   fail-open enumeration. A skip is a recorded decision (why, and who decided), never a
   silent ignore.
4. **Do not copy files yet.** For each relevant entry, propose a project PR:
   - Run `classify` against the **project's** current stamp. Regenerate only
     **unmodified**; surface **customized** as conflicts; never silently restore
     **missing**.
   - Also diff the *kit's current* `kit-files.txt` (or the new manifest's `files` keys)
     against the project's stamp membership. Paths the kit added since the stamp are
     **new members**, not `missing`. `missing` means "our stamp named it and the tree
     does not have it." New members are offered for install; they are never dropped
     because `classify` never saw them. Path mapping follows STANDUP (kit
     `templates/HARNESS.project.md` → project `HARNESS.md`, kit `reference/guards/` →
     project `scripts/`, …).
   `classify` against the project stamp, not the kit repo's file list — the two trees
   are different shapes. Membership drift is a third list: kit-added / project-only.
5. **Never self-apply.** The project Merge gate is the activation. Declining an entry is
   kit feedback: send it up; do not quietly drift.

The kit's `classify` answers "may this upgrade rewrite this file in *this* tree?" The
changelog answers "is there anything to consider?" Neither is sufficient alone.

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
the fresh-install test on majors, the named-reader table, the kit-as-dependency sweep, a
versioned stamp, and a pollable changelog that a project can read without write access to
the kit.

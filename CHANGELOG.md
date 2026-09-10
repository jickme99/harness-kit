# harness-kit changelog

The poll surface. A stamped project's `kit-manifest.json` carries `kit_version`; this file
says what changed after that version, who it applies to, and whether it is a bug-fix
(lane 1) or a new component (lane 3). How to poll: `spec/versioning.md`.

**Scheme:** calendar line `YYYY.MM` plus a patch (`2026.09`, `2026.09.1`, …). Bump
`kit_version` in `kit-manifest.json` on every merge a consumer should notice. File hashes
moving under an unchanged version is a silent upgrade. Git tags match `kit_version`.

`TODO.md` is the gap list. This file is the release log. They are not interchangeable.

Applies-to keys (hints, not a skip-allowlist): **every stamp** · **Claude** · **Cursor** ·
**Codex** · **optional**. Conditional prose is allowed. A poll that cannot prove an entry
does not apply must **consider** it (`spec/versioning.md`).

---

## 2026.09.3 — 2026-09-10

Poll is a tool. Succession is a file.

- **Lane:** 3 (new component — poll CLI, HANDOFF/START-HERE, classify tests). Doctrine
  for one-tool-per-working-copy. No guard behavior change.
- **Applies to:** every stamp. A project without `kit-manifest.json` still cannot poll
  until it stamps (`STANDUP.md` step 5).
- **What changed:**
  - `reference/tools/kit_poll.py` — worklist (same-version stays; unknown Applies-to is
    consider, never skip), STANDUP-mapped membership, `classify` of the project stamp
    against the project tree. Never copies files.
    `python scripts/kit_poll.py --project . --kit <harness-kit clone>`.
  - Tests for `kit_manifest.py` generate/classify (empty list, missing version, CRLF,
    customized/missing buckets).
  - `templates/START-HERE.project.md` → `START-HERE.md`; `templates/wiki/HANDOFF.md`
    (last decision, next task, kit version, not in this repo). Close-out polls the kit
    (`spec/wiki-protocol.md`).
  - `spec/operating-model.md` invariant 10: one tool per working copy; user-level hooks
    and `gh` are machine-global; tool-local memory is named.
- **Does not change:** harvest CLI (still parked until a consumer is stamped); fail-closed
  empty stdin; stamping origin as consumer #1.

## 2026.09.2 — 2026-09-10

Cursor stand-up actually wires, and the gate is adapter-aware.

- **Lane:** 1 for the install-path miss (a Cursor stamp that followed the adapter produced
  a hook that never fired). Lane 3 for the AGENTS template, the Gate column, and the
  empty-stdin residual watcher.
- **Applies to:** Cursor for the install path, wiring probe, and residual. Every stamp
  for `templates/AGENTS.project.md`, the REQUIRED / IF-AVAILABLE column, STANDUP gate
  language, and `inbox/` being gitignored.
- **What changed:**
  - D1 — `adapters/cursor.md` / `STANDUP.md`: `bridge.cmd` installs to
    `.cursor/hooks/bridge.cmd`, matching shipped `hooks.json`. The extra `hooks/`
    directory is load-bearing (`%~dp0..\..\scripts\`).
  - D3 — `harness_probes.py --probe guard_wiring` reports `claude_project`,
    `claude_user`, and `cursor_project`. A missing unused adapter is a fact. JSON keys
    `project` / `user` are renamed to `claude_project` / `claude_user` (no consumer
    stamp known). `present_project_layers` / `unarmed_present_project_layers` are the
    STANDUP reading.
  - D4 — empty/unreadable stdin still fail-opens (Windows pipe gap). The Cursor layer
    names that residual; `tests/test_cursor_bridge.py` watches `permission: allow`.
    Do not flip to deny without a live Windows test. Bridge debug JSONL writes only
    when `CURSOR_HOOK_DEBUG` is set (probe/tests stay read-only).
  - D6 — `templates/AGENTS.project.md` pointer stub; STANDUP copy step. Verify an
    existing `AGENTS.md` before overwriting.
  - Adapter coverage tables (and the HARNESS template) gained a **Gate** column:
    REQUIRED vs IF-AVAILABLE.
  - `inbox/` is gitignored (owner drop-box, not kit membership).
- **Does not change:** empty stdin remains fail-open (watched, not flipped to deny);
  stamping origin as consumer #1; poll / harvest CLIs (Wave B); origin probe scripts
  copied by bytes.

## 2026.09.1 — 2026-09-03

Pollable versioning: this changelog, the poll recipe, and a patch bump so the first kit
update is visible.

- **Lane:** 3 (new component — the poll surface itself). Doctrine + stamp metadata; no
  guard behavior change.
- **Applies to:** every stamp. A project still labeled `2026.09` must read **this entry
  and** the `2026.09` baseline (same-version sections stay on the poll worklist —
  `spec/versioning.md`). Projects that never generated a stamp cannot poll until they
  do (`STANDUP.md` step 5).
- **What changed:**
  - `CHANGELOG.md` (this file) is a kit member.
  - `spec/versioning.md` — poll-from-project is the primary upgrade path; recipe included.
    Applies-to skips default to **consider**; new kit members are found by mapping
    STANDUP install paths (not a raw `kit-files.txt` diff); same-version changelog
    sections stay on the worklist (the `2026.09` reuse).
  - `STANDUP.md` / `README.md` — stamp the current version; pointer to the poll recipe.
  - `reference/tools/kit_manifest.py` — dropped the stale "dormant / no kit exists yet"
    claim. The tool is live.
- **Does not change:** guards, hooks, adapters' coverage tables, origin-project stamp
  (still a consumer install — `TODO.md`).

## 2026.09 — 2026-09-01 through 2026-09-03 (baseline)

Everything on `main` through kit PR #2, previously labeled only `2026.09` with no
changelog. No consumer is known to carry a stamp yet, so this line is the baseline a
first poll compares against.

### Extraction — 2026-09-01

- **Lane:** 3 (the kit itself).
- **Applies to:** every stamp.
- **What:** spec, Claude-proven reference guards, portable contract tests, adapters,
  templates, STANDUP protocol. Manifest membership is a decision (`kit-files.txt`), not a
  glob.

### Merge-green refresh — 2026-09-01

- **Lane:** 1 (bug-fix).
- **Applies to:** every stamp that installed `merge_green_check.py`.
- **What:** bare `gh pr merge` (no PR selector) refused; unreadable payloads deny. The
  kit's strict xfail became a live contract. Origin engine PR #47.

### Cursor hooks verified — 2026-09-02 (kit PR #1)

- **Lane:** 3 (new Cursor mechanical path).
- **Applies to:** Cursor. Optional on Claude-only stamps.
- **What:** `beforeShellExecution` / `beforeMCPExecution` via `reference/cursor/`
  (`hooks.json`, `bridge.cmd`, `hook_bridge.py`). Windows `.cmd` wrapper; Azure MCP
  deny-by-name. Live unpinned `az` denied on the origin. Residual: empty-stdin fail-open
  on Windows pipes (still parked).

### Mode B harvest — 2026-09-03 (kit PR #2)

- **Lane:** 3 (doctrine from consumer #1).
- **Applies to:** Cursor-as-master for spawn/review/workshop; delegated Merge is every
  stamp whose owner has delegated the Merge gate.
- **What (accepted 1–5, nothing declined):**
  1. Task spawn: pin a slug from the project's vendor adapter table; never inherit.
     Do not write vendor names into Claude role-file `model:` fields.
  2. `/review-bugbot` on the exact diff, then `gh pr create` with no extra commits.
     Generic code-reviewer does not set the GitHub skip patch ID. Autofix OFF.
  3. Code-cyber seat is `/review-security` (findings · clean · blocked). No second prose
     cyber lens. Git-diff review, not cloud estate.
  4. Workshop invoke is the owner's spoken/slash phrase; master does not become the
     workshop; mailbox is a dated Inbox on the notebook page; two chats on one
     deliverable forbidden.
  5. Workers never merge. Standing master squash-merges when checks are success /
     skipped / neutral. Publish is never delegated.

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

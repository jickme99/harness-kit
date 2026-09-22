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

## 2026.09.9 — 2026-09-22

Stand-up asks about today. A predicted host no longer installs the chassis.

- **Lane:** 3 (stand-up doctrine — not a new component, not a guard change).
- **Applies to:** every new stand-up from this clone. `STANDUP.md` and
  `START-HERE.md` are kit-repo-only. Existing stamps do not install them.
  `templates/wiki/operating-model.md` is a dest: a filled page is `customized`
  and an upgrade must leave it alone. Do not regenerate a page the project
  has already written.
- **What changed:**
  - Question 1 asks whether the repository is public or shared **today**. A
    later published page is not a yes and does not install the firewall.
  - Question 2 asks whether a tool is being turned on **now**. Later is not a
    yes. The default is no. Saying yes records the decision and does not
    install the tool.
  - Question 3 asks where it runs **today**. The default is this machine.
    The keeping-current chassis is copied only when an image definition is
    already in the new project. A plan to host later is not a yes.
  - Question 4 asks whether the product sends information to anyone but the
    owner. That is not the reviewer question. It copies nothing.
  - Each of those four is provisional: the decision records what re-opens it.
  - The stand-up gate does not treat "no Dockerfile, chassis tests copied"
    as an expected red. That failure means remove the chassis.
- **Does not change:** the three REQUIRED guards; the chassis files
  themselves; `harness_probes.py` seams (still origin-shaped — `TODO.md`).

## 2026.09.8 — 2026-09-13

Work map as operating-model doctrine. The master infers kinds of work; the owner never authors them.

- **Lane:** 3 (new component — wiki snapshot + invariant 11). No guard behavior change.
- **Applies to:** every stamp — consider. New member
  `templates/wiki/operating-model.md` → `wiki/operating-model.md`. A project that
  already keeps an operating-model page under a house name (origin's probe lists
  `wiki/parallel-sessions.md` as a snapshot) does not restore the template: it adds
  a **Kinds of work** section to its page and points `HARNESS.md` §4 at its own
  path. Poll will list the template as missing for such a project; that is
  expected, not a restore.
- **What changed:**
  - `spec/operating-model.md` invariant 11: infer the map, write it, owner confirms
    the outcome once. Report is the record of a job; the map is the record of a
    kind; dest files are products; only the master writes the map.
  - Wiki skeleton ships `operating-model.md`. Session start fills
    `{{KIND_PLACEHOLDER}}` before product edits. STANDUP gate does not check
    kinds of work (empty tree).
  - `HARNESS.md` §4 pointer is a real path; the comment now says the contract is
    the kit spec and the wiki page is this project's snapshot.
- **Does not change:** the three REQUIRED guards; `harness_probes.py`
  `SNAPSHOT_PAGES` (still origin-shaped); no second orchestrator; no catalog of
  workflows.

## 2026.09.7 — 2026-09-12

Keeping current. Optional chassis for a project that ships a container.

- **Lane:** 3 (new component — `spec/keeping-current.md`, `adapters/github-azure.md`,
  `reference/keeping-current/`). No guard behavior change.
- **Applies to:** optional. New stand-ups answer STANDUP Question 3. Existing stamps
  see the files as new members and consider them; a wiki or library declines. Do not
  install into a project that does not ship a container image.
- **What changed:**
  - Tool-neutral spec: two lanes by what the change is; routine Merge is still the
    Merge gate, exercised by records; three outcomes; canary (or one real job
    execution); hashed lock; kill switch fails to OFF; weekly note; drills; dry
    first. Publish is never routine.
  - GitHub + Azure Container Apps method as an adapter, proven on production
    2026-09-08..12.
  - Portable rule modules and tests (stdlib + pytest). Workflows and shells ship
    with placeholders and refuse to run while one remains. Scheduled freshness is
    `dry` until `FRESHNESS_APPLY=on`. Auto-merge is adoption D and no-ops while
    `ROUTINE_LANE` is not `on`. A job-only stamp skips `deploy.yml`.
  - Version-steward reads the weekly note when the chassis is installed; it does
    not bump those pins by hand.
- **Does not change:** the three REQUIRED guards; default stamps without Question 3;
  this factory clone (it still does not run a freshness job against itself).
  Auto-merge of patch/minor lock-only updates is off until the canary drills pass
  and `ROUTINE_LANE` is set.

## 2026.09.6 — 2026-09-10

Kit front door. This clone is the factory, not the product.

- **Lane:** 3 (new component — kit-repo `START-HERE.md` / `CLAUDE.md` / `AGENTS.md`).
  No guard behavior change.
- **Applies to:** every new stand-up from this clone. Existing stamps do not install
  these files (kit-repo-only; they are not STANDUP dests).
- **What changed:**
  - Opening this repo in Claude, Cursor, or ChatGPT Codex now says: create a
    **separate** project folder, run STANDUP, hide stamp/poll from the human, then
    tell them to open the new path. Do not turn this checkout into the app.
  - Claude reads `CLAUDE.md`. Cursor and ChatGPT Codex read `AGENTS.md`. ChatGPT
    in the browser gets the paste prompt in `START-HERE.md`.
  - `STANDUP.md` / `README.md` state the same shape. After-stand-up enforcement
    is unchanged (Claude proven, Cursor verified, Codex still doctrine-only).
- **Does not change:** stamp/poll/harvest CLI; empty-stdin fail-open; corporate kit.

## 2026.09.5 — 2026-09-10

First harvest from consumer #1. STANDUP maps the review tools. Poll tests skip a product changelog.

- **Lane:** 1 for the poll test that treated any `CHANGELOG.md` as the kit poll surface
  (a stamp with Keep a Changelog then failed `parse_changelog`). Lane 3 for STANDUP
  copy arrows on `review_stamp.py` / `review_rates.py` (already in the kit, never
  installed).
- **Applies to:** every stamp. A project that already copied those two scripts is
  unchanged except the test skip. New stand-ups copy them.
- **What changed:**
  - `tests/test_kit_poll.py` — live changelog contract skips unless the file has
    `## 2026.09.2` (kit poll surface, not a product changelog).
  - `STANDUP.md` — `reference/tools/review_stamp.py` → `scripts/` and
    `reference/tools/review_rates.py` → `scripts/` as two separate bullets.
  - Consumer #1 harvest (origin engine): **accepted** the STANDUP mapping (tools
    already in the kit). **Declined** product roles, Cursor lane rules, product
    scripts, and `firewall_scan.py` — those stay in the project. Never copied
    origin bytes.
- **Does not change:** stamp/poll/harvest CLI shape; empty-stdin fail-open;
  corporate kit.

## 2026.09.4 — 2026-09-10

One stamp method. Harvest is a proposal. Empty stdin stays fail-open.

- **Lane:** 3 (new component — stamp CLI, harvest CLI). Empty-stdin is a recorded
  judgment, not a behavior change.
- **Applies to:** every stamp. New projects and existing consumers fingerprint the
  same way (`STANDUP.md` step 5). Harvest applies once `kit-manifest.json` exists.
- **What changed:**
  - `reference/tools/kit_stamp.py` — the only stamp method. STANDUP-mapped dests that
    already exist in the project tree become `kit-files.txt` (project paths) and
    `kit-manifest.json` (hashes + the kit's `kit_version`). Does not copy kit files,
    does not glob the project, does not name dests that are not installed.
    `--refresh` rebuilds; `--dry-run` prints the plan.
    `python scripts/kit_stamp.py --project . --kit <harness-kit clone>`.
  - `reference/tools/kit_harvest.py` — proposal-only two-way feedback. Reports
    `customized` stamp members (reverse-mapped to a kit path when STANDUP has one)
    and harness-adjacent `extra` files under `scripts/`, `.cursor/`, `.claude/`.
    Never copies into the kit. Product trees (`app/`, `tests/` beyond kit contracts)
    are out of scope.
    `python scripts/kit_harvest.py --project . --kit <harness-kit clone>`.
  - `STANDUP.md` step 5 is this command (not "copy kit-files.txt and hand-edit paths").
  - Empty stdin on the Cursor bridge **remains fail-open**. Deny froze every command
    on Windows when conda `python.cmd` dropped the pipe. The residual stays watched
    (`tests/test_cursor_bridge.py`). Do not flip `hook_bridge.py` without a live
    Windows test that does not freeze the shell.
- **Does not change:** Cursor install path; poll CLI shape (`--project` / `--kit`);
  kit-opens-upgrade-PRs (consumer #2); corporate kit.

## 2026.09.3 — 2026-09-10

Poll is a tool. Succession is a file.

- **Lane:** 3 (new component — poll CLI, HANDOFF/START-HERE, classify tests). Doctrine
  for one-tool-per-working-copy. No guard behavior change.
- **Applies to:** every stamp. A project without `kit-manifest.json` still cannot poll
  until it stamps (`STANDUP.md` step 5).
- **What changed:**
  - `reference/tools/kit_poll.py` — worklist (same-version stays; unknown Applies-to is
    consider, never skip), STANDUP-mapped membership (adapter docs included by default;
    Cursor `.mdc` / `BUGBOT.md` and Claude role files are STANDUP arrows; missing
    STANDUP.md or kit-files.txt fails closed), `classify` of the project stamp against
    the project tree. Never copies files.
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

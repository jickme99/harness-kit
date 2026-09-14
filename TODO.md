# TODO — known gaps, honestly

- **`SNAPSHOT_PAGES` is still origin-shaped.** `reference/guards/harness_probes.py`
  defaults to `wiki/status.md` and `wiki/parallel-sessions.md`. New stamps ship
  `wiki/operating-model.md` (`2026.09.8`). Do not change that default (it would fail
  origin). Later: a stamp-time seam writes the project's snapshot list. Twice-skipped
  maps graduate that seam (`spec/graduation.md`).
- **Engine HARNESS.md reconciliation pending.** The kit's `templates/HARNESS.project.md`
  was authored from the ORIGIN'S BRAIN-REPO `HARNESS.md` (merged) plus the spec; the
  origin's engine-repo HARNESS.md did not exist on main at extraction time (its 6a PR was
  in flight). When it merges, reconcile the template against it — the engine version is
  the one with CI legs and a different coverage table, so it may teach the template rows
  this one lacks.
- **The push-queued-runs check is due to graduate.** A dropped-GitHub-events class
  (workflow runs that never start after a push) was observed twice on 2026-09-01 — the
  hooks-by-evidence threshold (`spec/graduation.md`) is met. The shape: after a push, a
  probe that verifies the expected workflows actually QUEUED, so "no runs" is
  distinguished from "green". Propose as a probe-pack addition.
- **The kit-steward role activates at consumer #2.** One consumer = nothing to steward
  from the kit side. Poll-from-project is live as of `2026.09.1` (`CHANGELOG.md` +
  `spec/versioning.md`). Until consumer #2, kit-opens-upgrade-PRs stays future work;
  declined upgrades remain kit feedback either way.
- **RESOLVED 2026-09-10 — origin stamped as consumer #1.** Engine PR #53 landed
  `kit-files.txt` / `kit-manifest.json` via `kit_stamp.py`. Poll apply (stamp/poll/harvest
  CLIs, START-HERE; wiki and harness_probes declined — they live in HQ) is origin PR #54.
- **The corporate kit is HELD** (owner decision 2026-09-01) until this personal kit
  survives real cross-tool testing — Cursor, maybe ChatGPT. When it is authored, it is
  authored FRESH corp-side: patterns cross, files never, either direction — and patterns
  cross only after they have survived a second harness. There is one kit factory: this
  repo. Keeping-current harvested here as `2026.09.7`.

- **RESOLVED 2026-09-12 — keeping-current play harvested (`2026.09.7`).** Spec,
  GitHub/Azure adapter, portable rules and tests, STANDUP Question 3. Job-kind
  refresh *workflow* still per-project (rules shipped). Second-host adapter not
  written. Weekly note still one repository.

- **RESOLVED 2026-09-13 — work map as operating-model doctrine (`2026.09.8`).**
  Invariant 11, `templates/wiki/operating-model.md`, session-start tripwire,
  HARNESS pointer fixed. No twelfth spec page. `SNAPSHOT_PAGES` unchanged
  (parked above).
- **RESOLVED 2026-09-01 — bare selector-less merge bypassing the merge-green guard.**
  Found by this kit's contract suite at extraction; fixed upstream the same day (origin
  engine PR #47: every merge occurrence in a call checked, the bare current-branch form
  refuses with an ask-for-a-selector remedy, `--repo=owner/repo` read, unreadable
  payloads/rows DENY) and the kit's `reference/guards/merge_green_check.py` is refreshed
  from that merged copy. The strict xfail is flipped into a live passing contract in
  `tests/test_guard_contracts.py` — the record deleted, the fix kept red-able.
- **Deliberate env-seam divergence in the refreshed merge guard:** the kit copy reads the
  gh-account pin from `HARNESS_GH_ACCOUNT` where the origin spells it `VT_GH_ACCOUNT` —
  same seam, kit-neutral name, noted in the file itself. Keep the divergence when future
  refreshes flow through; everything else stays byte-faithful plus the kit header.
- **Second extraction finding, same guard, same class: `merge_green_check.py` reasons
  about the command as TEXT.** Its trigger regex matches the merge-command string
  anywhere in the whole command — including inside a quoted commit message or here-doc
  PROSE — so a `git commit -m "... about the merge guard ..."` naming the command
  literally is refused as if it were a merge (this bit the kit's own bootstrap commit).
  That is the az guard's recorded v1/v2 failure mode ("reasoned about the command as
  TEXT"), which its sibling guards solved with quote-aware parsing the merge guard never
  got. Fix upstream first, like the bare-merge fail-open above; the false-denial severity
  rule applies (commit messages are routine work).
- **RESOLVED 2026-09-02 — Cursor enforcement hooks verified on the origin**
  (`adapters/cursor.md`): native Cursor Agent `beforeShellExecution` /
  `beforeMCPExecution` via `reference/cursor/` bridge. Live unpinned `az` denied.
  Remaining: stamp origin as consumer #1 (E5); kit-steward still waits on consumer #2.

- **The Codex adapter is a hypothesis** (`adapters/codex.md`): rewrite it from evidence
  after the first real cold start on a non-Claude agent — which is also the kit's own
  validation experiment.

- **RESOLVED 2026-09-03 — consumer #1 Mode B harvest (accepted 1–5; nothing declined).**
  Cursor Task pin-never-inherit; `/review-bugbot` before `gh pr create` (patch-ID skip);
  code-cyber seat = `/review-security` (findings · clean · blocked); workshop invoke +
  notebook mailbox; delegated Merge is squash-merge when green, Publish never delegated.
  Parked (already listed above, not new): stamp origin as consumer #1; push-queued-runs
  probe; merge_green quote-aware parse; Codex rewrite. Empty-stdin fail-open is a
  recorded judgment as of `2026.09.4` (Windows freeze); not a parked flip.

- **RESOLVED 2026-09-03 — pollable kit versions (`2026.09.1`).** `CHANGELOG.md` is the
  poll surface; `spec/versioning.md` has the recipe; `kit_version` bumps on every merge
  a consumer should notice. Baseline `2026.09` (extraction through kit PR #2) is logged
  after the fact because those merges did not bump the string.

- **RESOLVED 2026-09-10 — Wave A from the 2026-09-08 review (`2026.09.2`).** Cursor
  install path matches `hooks.json` (`.cursor/hooks/`); `guard_wiring` is adapter-aware;
  `templates/AGENTS.project.md` ships; empty-stdin fail-open is a watched residual, not
  flipped to deny; adapter tables have REQUIRED / IF-AVAILABLE; `inbox/` gitignored.
  Still parked after this wave: stamp origin. Empty-stdin fail-open kept (see `2026.09.4`).

- **RESOLVED 2026-09-10 — Wave B (`2026.09.3`).** `kit_poll.py` is the poll (proposal
  only); `classify` has contracts; START-HERE / wiki/HANDOFF answer the four succession
  questions; one-tool-per-working-copy is operating-model invariant 10.

- **RESOLVED 2026-09-10 — stamp CLI, harvest CLI, empty-stdin judgment (`2026.09.4`).**
  `kit_stamp.py` is the only stamp method (STANDUP-mapped dests that exist; no glob, no
  silent restore). `kit_harvest.py` is the two-way feedback proposal (customized +
  harness-adjacent extra; never copies into the kit). Empty stdin on the Cursor bridge
  remains fail-open: deny froze every Windows command when conda `python.cmd` dropped
  the pipe. Residual stays watched. Harvest no longer waits on a consumer stamp — the
  tool ships; origin stamp landed as engine PR #53.

- **RESOLVED 2026-09-10 — first harvest from consumer #1 (`2026.09.5`).** Accepted:
  STANDUP now copies `review_stamp.py` / `review_rates.py` (already in the kit, were
  kit-repo-only). Poll live-changelog test skips a product CHANGELOG. Declined (stay
  in the project): product roles, Cursor lane `.mdc`s, product scripts, origin
  `firewall_scan.py`. Never copied origin bytes.

- **RESOLVED 2026-09-10 — kit front door (`2026.09.6`).** This clone is the factory.
  `START-HERE.md` / `CLAUDE.md` / `AGENTS.md` tell the agent to stand up a sibling
  project and hide stamp/poll from the human. Claude reads `CLAUDE.md`; Cursor and
  ChatGPT Codex read `AGENTS.md`; ChatGPT in the browser pastes the prompt in
  `START-HERE.md`. Those three files are kit-repo-only (not STANDUP dests). The
  product stubs stay `templates/*.project.md`. Codex *enforcement* after stand-up
  is still untested (`adapters/codex.md`).

# TODO — known gaps, honestly

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
- **Stamping the origin project as consumer #1 is a follow-up** — install
  `kit-files.txt`/`kit-manifest.json` into it so `classify` can tell kit files from
  tailoring there, making "the origin operates from the kit" literally true.
- **The corporate kit is HELD** (owner decision 2026-09-01) until this personal kit
  survives real cross-tool testing — Cursor, maybe ChatGPT. When it is authored, it is
  authored FRESH corp-side: patterns cross, files never, either direction — and patterns
  cross only after they have survived a second harness.
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
  probe; merge_green quote-aware parse; empty-stdin fail-open residual (named and
  watched as of `2026.09.2`; still not fail-closed); Codex rewrite.

- **RESOLVED 2026-09-03 — pollable kit versions (`2026.09.1`).** `CHANGELOG.md` is the
  poll surface; `spec/versioning.md` has the recipe; `kit_version` bumps on every merge
  a consumer should notice. Baseline `2026.09` (extraction through kit PR #2) is logged
  after the fact because those merges did not bump the string.

- **RESOLVED 2026-09-10 — Wave A from the 2026-09-08 review (`2026.09.2`).** Cursor
  install path matches `hooks.json` (`.cursor/hooks/`); `guard_wiring` is adapter-aware;
  `templates/AGENTS.project.md` ships; empty-stdin fail-open is a watched residual, not
  flipped to deny; adapter tables have REQUIRED / IF-AVAILABLE; `inbox/` gitignored.
  Still parked: fail-closed empty stdin; stamp origin; Wave B (poll/harvest tools,
  HANDOFF templates).

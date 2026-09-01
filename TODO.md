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
- **The kit-steward role activates at consumer #2.** One consumer = nothing to steward.
  Until then the kit versions by hand (this repo's own `kit-manifest.json` +
  `kit-files.txt`); the steward's pull-based design (reads consumers' standardized
  harness-audit reports; drift is information; declined upgrades are kit feedback) is
  specified in `spec/graduation.md` and `spec/versioning.md`.
- **Stamping the origin project as consumer #1 is a follow-up** — install
  `kit-files.txt`/`kit-manifest.json` into it so `classify` can tell kit files from
  tailoring there, making "the origin operates from the kit" literally true.
- **The corporate kit is HELD** (owner decision 2026-09-01) until this personal kit
  survives real cross-tool testing — Cursor, maybe ChatGPT. When it is authored, it is
  authored FRESH corp-side: patterns cross, files never, either direction — and patterns
  cross only after they have survived a second harness.
- **Found at extraction, fix upstream first: bare `gh pr merge` bypasses the merge-green
  guard.** The guard's regex requires text after `merge`, so `gh pr merge` with no
  selector — which gh resolves from the current branch and merges — passes in silence.
  Recorded as a strict xfail in `tests/test_guard_contracts.py` (the origin's
  known-failure mechanism: the entry goes red the day the guard is fixed). The fix
  belongs in the ORIGIN's `scripts/merge_green_check.py` first, then flows here — the
  kit copies faithfully; it does not fork the guards.
- **Second extraction finding, same guard, same class: `merge_green_check.py` reasons
  about the command as TEXT.** Its trigger regex matches the merge-command string
  anywhere in the whole command — including inside a quoted commit message or here-doc
  PROSE — so a `git commit -m "... about the merge guard ..."` naming the command
  literally is refused as if it were a merge (this bit the kit's own bootstrap commit).
  That is the az guard's recorded v1/v2 failure mode ("reasoned about the command as
  TEXT"), which its sibling guards solved with quote-aware parsing the merge guard never
  got. Fix upstream first, like the bare-merge fail-open above; the false-denial severity
  rule applies (commit messages are routine work).
- **Cursor enforcement-hook support is unverified** (`adapters/cursor.md`): nobody has
  established whether any Cursor mechanism can block a shell command pre-execution
  against the guards' stdin contract. Verify and upgrade or close that row.
- **The Codex adapter is a hypothesis** (`adapters/codex.md`): rewrite it from evidence
  after the first real cold start on a non-Claude agent — which is also the kit's own
  validation experiment.

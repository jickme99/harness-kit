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

---

## Consumer #2 findings — `sam-gov-typesafe`, stood up 2026-09-21

One project, stood up from `2026.09.8` and run for a day: harness installed, gate run,
product built to a first release. Everything below was **observed**, not suspected; each
entry names what happened. Written generically — the consumer is a Python project on
Windows using the Claude Code adapter, and entries say so only where it matters.

Nothing here self-applies. This is the gap list, per this file's own job.

### The stand-up asks for predictions, in our vocabulary, before the project exists

**The kit's own author could not answer its three questions correctly.** That is the
finding; the rest is evidence.

- **Question 3 (container)** was answered *"an app that serves traffic"*. The project
  turned out to be a nightly local job writing a static page, with a staged progression
  in which stage 1 has no hosting at all. The chassis was installed and removed inside a
  day — it had arrived with ~70 unfilled placeholders, a workflow on a daily cron and one
  on every push, all of which would have begun failing the moment a remote was added.
- **Question 1 (visibility)** was answered *"never public"*. The project's entire stated
  outcome is a **published page**. The answer was true of the repository on day one and
  false of the project, and nothing in the stand-up says which answers are expected to
  change or what re-opens them.
- **Question 2 (vendor)** asks whether an *adapter* sends repository content to a third
  party. It was answered "yes, approved" about a tool that was then never installed.
  Meanwhile the **product** sends data to an outside model vendor on every run — the
  premise of the project, and the stated blocker on its final stage. The kit never asks
  that, and it is the question with real consequences.

So: two of three answers were wrong in a way that caused work, and the third asked about
the wrong thing. A stranger will do worse than the author did.

**Proposed shape**, not a patch:
1. **Ask about now, not about later.** "Where does this run today?" with *on my machine*
   as a first-class answer and the default. Nobody knows their hosting model before they
   know the thing is worth hosting — see the freeze-rule entry below.
2. **Say which answers are provisional, and what re-opens them.** Visibility and hosting
   both change; the stand-up presents all three as settled facts.
3. **Add the missing question:** *does the product itself send data outside your
   organisation?* It is a different question from the adapter one, it drives real
   constraints, and it is the one a reviewer will ask first.
4. **State each answer's consequence in the question.** "Answering yes installs a
   deployment chassis with N placeholders you must fill" is the sentence that would have
   prevented the wrong answer here.

### Guards, probes and the roles that read them

- **The user-level guard layer has no neutral home, and fails silently.** `adapters/*.md`
  says to wire the same scripts with machine-absolute paths but never says where those
  scripts should live, and ships no user-layer file. The only copy a reader has is the one
  inside the project they are standing up — so that is what they point at. Observed: a
  workstation whose user layer ran all three guards out of an *unrelated* project's
  checkout. It works until that directory moves, and then it breaks in the **silent**
  direction the kit already documents (missing interpreter exits 127, non-blocking).
  Ship a user-layer template, install the guards somewhere project-independent, and have
  the wiring probe *flag* a user layer whose targets resolve inside a project tree.
- **A shipped role requires instruments the kit does not ship.** `harness-auditor.md`
  item 14 mandates reading an event-rollup script and ledger that are not in
  `kit-files.txt`. Every stamp inherits a checklist item that cannot be completed, which
  teaches operators to skip checklist items — the exact failure the role exists to catch.
  Ship the instrument, or mark such items `requires: <instrument> — not shipped` and force
  a decision at install.
- **The probe pack ships fabricated defaults, against its own docstring.** It says "never
  a silent zero, never an inferred value", then defaults the second-repo path to a
  placeholder directory, the slug to a placeholder string, the snapshot-page list to a
  page the template set never creates, and the lesson epoch to a date from the origin's
  calendar. All four needed hand-editing before the pack described the consumer rather
  than the origin, and nothing would have said so if one had been missed. Default every
  seam to an unset sentinel and let dependent probes return `ok_to_collect: false`.

### Stamp, upgrade and the gate

- **A container project cannot pass the gate on day one, by construction.** STANDUP says a
  project is not stood up until the gate passes; answering Question 3 "yes" copies a test
  that fails unless a container definition already exists; a project being stood up has no
  product. Observed: `1 failed, 216 passed` on a clean stand-up. The three ways out are
  all bad — stub a fake image, delete the test, or learn that red is normal. Either make
  the test's trigger true at stand-up, or state in STANDUP that this row is expected red
  until the first image and exclude it from the pass condition.
- **Install-time seam edits are indistinguishable from local drift.** STANDUP *instructs*
  edits to specific lines in shipped files; the stamper then fingerprints them and
  `classify` reports `customized` — the category an upgrade must "leave alone or raise as
  conflicts". Files the kit told you to touch become a private fork forever. Move seams
  out of shipped sources into generated config, or add a `seamed` classification.
- **The stamp is not stable where line endings are normalized.** The stamper hashes
  working-tree bytes, so on Windows a fresh clone of a correctly stamped project can
  classify the whole set as modified. Observed: conversion warnings on 14 files at the
  first commit. Hash normalized content — a one-line change that protects people who never
  configure their version control — and ship a line-ending attributes file besides.
- **`classify` accepts a manifest that cannot describe the tree.** Pointing it at the
  *kit's* manifest from inside a stamped project runs happily and reports ~91 files
  "missing" — the one category the kit says must never be silently restored. Record which
  mapping a manifest was generated for and refuse a mismatch.
- **Agent worktrees inside the tree get committed as embedded repositories.** The role
  template says workers run in an isolated worktree; a harness that creates it *under* the
  project means the next `git add -A` records a gitlink, with only git's hint as warning.
  Ship the worktree location in the template `.gitignore` and say in STANDUP that a
  worker's worktree is a branch, not a directory of the project.
- **Question 3 conflates "ships a container" with "deploys the way the origin deployed".**
  Freshness, canary, weekly note, dependency config and a host-specific deployment
  workflow all travel as one bundle. A project that wants the freshness guarantees but not
  that hosting model has no honest answer. Split the question, and ship the freshness core
  independently of any host.
- **The kit's own templates trip the kit's own guards.** Writing the project constitution
  through a shell heredoc was refused by the merge-green guard, because the constitution
  quotes the command it governs. The guard is right; the surprise is avoidable. One line
  in the adapters: install document templates with a file-writing tool, not by piping text
  through a shell.

### Patterns this consumer used that the kit may want

- **Apply the freeze rule to infrastructure, not only to enforcement.** `spec/graduation.md`
  refuses new harness components without evidence from operation — then Question 3 asks,
  at the moment of least evidence, what the deployment model will be, and installs on the
  answer. This consumer's owner independently described a three-stage progression (local →
  personal cloud → company cloud, each entered on evidence) which is invariant 1 restated
  one level up. Give STANDUP a **stage posture** — where this runs *now*, and what moves it
  — and let the chassis arrive at the stage that earns it, by the same poll mechanism as
  any other kit content.
- **Contract-first with two samples, and then an adversarial one.** A worker built a
  rendering surface against a committed JSON contract while the data layer was built in
  parallel; it never saw real data. That worked until a real day produced a `null` the
  sample never showed. Ship **two** samples — the good day and a sparse one with every
  nullable field null, every list empty, the "no previous period" case — and make
  "renders both without raising" a standing rule. Then a **third**, adversarial: real
  worst-case string lengths. A long real string pushed a page 226px wider than the
  viewport, and the sample-based checks were clean because the samples' strings were short.
  The dense sample buys a design; the sparse sample buys honest empty states; the
  adversarial sample buys the truth.
- **A renamed contract key needs a reader that spans both vocabularies** in any project
  that re-renders its own history. Two renames here each re-rendered stored artifacts
  written under the old names; the fix both times was a reader that accepts old and new,
  and in one case recomputes the value from a field that never changes.
- **Record an absent instrument as a finding rather than deleting the checklist item.**
  Keep the item, rewrite it to say the instrument does not exist here and that its absence
  is reported until it is built or the rule is retired in writing.
- **Say in the PR template which gates are mechanical here.** The shipped template's
  exemption lines read as though a CI gate honours them, which is only true if the optional
  workflows were installed. In a project without them the template overstates its own
  enforcement — the dishonesty the coverage tables exist to prevent.
- **Make the partial gate pass a named, expected outcome.** STANDUP prescribes recording a
  failing gate honestly, but as an exception in a closing paragraph. With the container
  contradiction above unfixed, the partial pass is the *normal* result — worth a worked
  example, and a decisions-template entry.
- **A mechanical merge gate for a fenced worker is a dozen lines** and worth shipping
  beside the guards: changed paths must match the fence and never the contract; grep the
  worker's own files for network requests; full suite green.

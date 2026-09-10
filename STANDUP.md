# STANDUP — cold-starting a new project from this kit

Written to be executed by an AI agent, with its human answering the questions. Work
top-to-bottom; do not skip the questions to get to the install steps — two of them change
what gets installed, and one of them is a compliance matter. The protocol ends in a
**runnable gate**; a project is not stood up until the gate passes.

## Question 1 — the visibility question (decides the repo shape)

> **"Will any part of this project ever be public, or shared beyond the owner?"**

- **YES → two-repo shape.** A sealed **brain** repo (private forever: strategy, candid
  plans, post-mortems, the wiki, the firewall denylist) and a publishable **body** repo
  (the product; assume everything committed there becomes public eventually). Public-safe
  pages are **promoted deliberately, one page at a time, never bulk-synced** — anything
  that could never be public lives in the brain and does not leave it. The body repo gets
  the firewall (`spec/firewall.md`).
- **NO → one-repo shape.** The brain is a `wiki/` folder inside the body. No firewall CI
  needed; everything else is identical.

Everything else in the kit — master, roles, gates, guards, auditor, docs doctrine — is
identical across shapes. Shape is a stand-up-time answer, not a fork of the kit.

## Question 2 — the vendor question (before ANY adapter that sends repo content out)

> **"Does any adapter you plan to enable send repository content to a third party?"**
> (External PR reviewers — e.g. Cursor's Bugbot — and any hosted review/analysis service
> qualify: enabling one means the repository's contents are processed by an outside
> vendor.)

- **Personal repos:** the owner's call. Ask, record the answer in `wiki/decisions.md`.
- **Corporate repos:** requires IT/security approval **BEFORE enablement, not after.**
  This is company IP crossing an organisational boundary through a tool someone switched
  on, and it fails the same way an information firewall does — quietly, and only visibly
  in hindsight. Do not install such an adapter without a recorded approval.

## Install steps

1. **Copy the core files.**
   - `templates/HARNESS.project.md` → the project root as `HARNESS.md`. Fill its
     placeholders: the project's rules, its own coverage table, its pointers.
   - `templates/CLAUDE.project.md` → `CLAUDE.md` (the Claude Code entry point; a pointer
     stub — the constitution is `HARNESS.md`, tool files point at it).
   - `templates/AGENTS.project.md` → `AGENTS.md` (Cursor and Codex read this natively;
     same pointer-stub pattern). If `AGENTS.md` already exists, read it first — do not
     overwrite an install runbook or other job with a pointer stub.
   - `templates/START-HERE.project.md` → `START-HERE.md` (succession: last decision,
     next task, kit version, what is not in this repo). Fill it; a cold start that
     cannot answer those four is not stood up.
   - `reference/guards/*.py` → `scripts/` in the project. Set the marked install-time
     seams (the probe pack's second-repo path/slug and gh account; the merge guard's
     `HARNESS_GH_ACCOUNT` if the machine has multiple gh logins).
   - `reference/tools/kit_manifest.py` → `scripts/`.
   - `reference/tools/kit_poll.py` → `scripts/`.
   - `reference/tools/kit_stamp.py` → `scripts/`.
   - `reference/tools/kit_harvest.py` → `scripts/`.
   - `reference/tools/review_stamp.py` → `scripts/`.
   - `reference/tools/review_rates.py` → `scripts/`.
   - `tests/` → `tests/` (the guard contract tests and the stamper/poll/harvest contracts).
     Adjust `GUARDS_DIR` at the top of `tests/guard_registry.py` if your scripts live
     elsewhere.
   - `templates/pr-template.md` → `.github/pull_request_template.md`, placeholders filled.
2. **Install the guards' wiring for your tool** — per the adapter doc (`adapters/claude.md`,
   `adapters/cursor.md`, `adapters/codex.md`). For Claude Code that is
   `reference/claude/settings.json` → `.claude/settings.json` (and optionally the
   user-level layer; see `spec/guards.md` on why two layers exist). For Cursor that is
   `reference/cursor/hooks.json` → `.cursor/hooks.json`, `reference/cursor/bridge.cmd` →
   `.cursor/hooks/bridge.cmd` (the extra `hooks/` directory is load-bearing — see
   `adapters/cursor.md`), `reference/cursor/hook_bridge.py` →
   `scripts/cursor_hook_bridge.py`, `reference/cursor/project-rules.mdc` →
   `.cursor/rules/project-rules.mdc`, `reference/cursor/outside-the-lane.mdc` →
   `.cursor/rules/outside-the-lane.mdc`, and `reference/cursor/BUGBOT.md` →
   `.cursor/BUGBOT.md`. For a harness without hooks, the adapter doc tells you what
   you are carrying as doctrine instead.
3. **Instantiate the wiki skeleton.** `templates/wiki/` → the brain (`wiki/` in the brain
   repo, or `wiki/` in the one-repo shape). Set each page's frontmatter dates; write the
   first `decisions.md` entry — the answers to Questions 1 and 2, dated.
4. **Roles.** Draft the project's product roles from `reference/claude/role-template.md`
   (fences are real paths — start narrow; widening is on the record). Install the two
   function-role patterns: `reference/claude/harness-auditor.md` →
   `.claude/agents/harness-auditor.md` and `reference/claude/version-steward.md` →
   `.claude/agents/version-steward.md`, replacing origin path and instrument names with
   the project's own.
5. **Stamp the project** — the fingerprint that makes poll and harvest possible. This is
   the only stamp method; a new project and an existing consumer run the same command.
   It does **not** copy kit files (install is steps 1–4). It fingerprints the
   STANDUP-mapped dests that **already exist** in this tree, writes `kit-files.txt`
   (project paths) and `kit-manifest.json` (hashes + the kit's current `kit_version`).
   Destinations that are not installed are not named, so `classify` `missing` does not
   fight "do not silently restore." Kit-repo-only paths (`spec/`, `adapters/`, …) stay
   in the kit. `kit-manifest.json` is the output, not a member of the list.

   ```sh
   python scripts/kit_stamp.py --project . --kit <harness-kit clone>
   ```

   Before the copy in step 1 exists, the same file from the clone is the same method:
   `python <clone>/reference/tools/kit_stamp.py --project . --kit <clone>`.
   `--dry-run` prints the plan. `--refresh` rebuilds an existing stamp from the current
   tree. Do not hand-edit a copied kit `kit-files.txt` — that is a second mapping and
   it will drift. Commit both files. A project without this stamp cannot poll or harvest.
   Later: `python scripts/kit_poll.py --project . --kit <harness-kit clone>`
   (`spec/versioning.md`). To offer local customizations back to the kit:
   `python scripts/kit_harvest.py --project . --kit <harness-kit clone>`
   (proposal-only; never copies into the kit). Never self-apply.
6. **(Two-repo shape only) Arm the firewall** per `spec/firewall.md`: author the scanner
   in the body repo, seed the denylist in the brain repo from your own hard constraints,
   sync the secret, record the hash.

## THE GATE (runnable — the stand-up is not done until this passes)

```sh
# 1. The contract tests, in the project's own checkout:
python -m pytest tests/ -q

# 2. The wiring probe:
python scripts/harness_probes.py --probe guard_wiring

# 3. The live negative test — ask YOUR harness to run a command a guard must refuse but
#    which touches nothing if it runs, and confirm the refusal:
#      az kit-probe-does-not-exist          (must be refused: no --subscription)
#      git reset --hard HEAD                (must be refused: no -C <absolute path>)
```

Read the probe JSON. Pass/fail is adapter-aware, not "every layer armed":

- A **project-level** layer whose config file is present (`claude_project` =
  `.claude/settings.json`, `cursor_project` = `.cursor/hooks.json`) must have an empty
  `not_armed` list and `ok_to_collect`. Cursor-only stamps show `claude_project` absent;
  that is a fact, not a fail. Claude-only stamps show `cursor_project` absent; same.
- `present_project_layers` names the configs that exist; `unarmed_present_project_layers`
  must be empty. Read those two lists — do not fail a Cursor-only stamp because
  `layers.claude_project.not_armed` (or the unused Cursor list) still names the three
  guards. An unused layer's `not_armed` is a fact about absence, not a gate fail.
- If **neither** project-level config is present, this step passes only when the adapter
  you installed is doctrine-only for the three guards (today: Codex). Record that in
  `wiki/decisions.md`.
- `claude_user` is IF-AVAILABLE: reported, not required for this gate.
- On a Cursor layer the probe may report `empty_stdin_residual.permission: allow`. That
  is the recorded Windows residual — not a wiring fail. Do not flip the bridge to deny
  on empty stdin without a live Windows test.

Pass = tests green, the probe matches the rules above, and the live probes are refused
on a harness that has hooks. A doctrine-only adapter has no live hook to fire; do not
pretend piping JSON at Python is that test (`tests/` already covers the guards).

**What a failing gate means — plainly:** the harness you just stood up does not enforce
what its documents claim, and every promise in `HARNESS.md`'s mechanical column is
currently false. Do not proceed to real work on the assumption that it mostly works: a
guard that is wired but never fires is indistinguishable from a working one until the day
it matters (the origin measured exactly this — 23 commands that should have been denied,
0 denied, because a settings file lived in the wrong commit). Fix the wiring, or move the
affected rows of the coverage table to doctrine-only in writing so the record stays
honest, and record the gap in `wiki/decisions.md`.

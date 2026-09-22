# STANDUP — cold-starting a new project from this kit

A human who is not technical opens **this kit clone** in Claude, Cursor, or ChatGPT
Codex. The front door is `CLAUDE.md` (Claude) / `AGENTS.md` (Cursor and ChatGPT Codex)
/ `START-HERE.md`. ChatGPT in the browser does not auto-read those files — they paste
the prompt in `START-HERE.md`. You stand up a **separate** project folder. This clone
stays the kit. They never run stamp, poll, harvest, or pytest — you do. When the gate
passes, they close this folder and open the new one.

Written to be executed by an AI agent. The human answers three things, in plain
English: whether the folder already exists, what the project is about, and what
we are doing. Do not ask whether it will be public, whether a tool will read the
repository, where it will be hosted, or whether the product will send data out.
They do not know yet, and they should not have to. The pieces for those moments
are later in this file. You bring a piece when the work needs it, in one
sentence: what is about to happen, and what you are adding. The protocol ends in
a **runnable gate**; a project is not stood up until the gate passes. Do not turn
this kit checkout into the product.

## The only questions

1. **New folder, or one that already exists?**
   - **Already has this harness** (`HARNESS.md` or `kit-manifest.json` in that
     folder): stop. Tell them the path and ask what we are doing. Do not copy
     again. Do not stand up a second tree.
   - **Exists, and has no harness:** install the core into **that** folder. Do
     not create a sibling. Do not copy a piece from the section below.
   - **New:** a sibling of this kit clone. Ask what it is about. That sentence
     is the outcome and the folder name.
2. **What is it about?** One sentence, in their words. Ask only if a new folder
   does not already have that sentence. Do not invent the product past what they
   said.
3. **What are we doing?** An existing folder: today's task. A new folder: the
   same sentence as what it is about, until the work itself splits into more.

## What stand-up always installs

One repository on this computer. Nothing is sent out. Guards, the wiki, and the
stamp. The brain is a `wiki/` folder inside the project. Record that in
`wiki/decisions.md` without asking — it is the start, not a prediction. Master,
roles, gates, guards, auditor, and docs doctrine are the same whatever gets
added later.

## Pieces, when the work needs them

Do not copy these at stand-up. Do not ask the owner to choose them. When the
work reaches one, write a new `wiki/decisions.md` entry and copy the piece.
Company material leaving the house stops for approval **before** the first send.

- **Keep an image current.** An image definition is already in the tree **and**
  the work is to keep that image current — they said so, or a deploy is about
  to be added. Then copy install step 5. An app that serves traffic includes
  `deploy.yml`. A scheduled job skips `deploy.yml`. GitHub + Azure Container
  Apps is the proven method (`adapters/github-azure.md`, `spec/keeping-current.md`).
  Fill every placeholder. First two runs of every job are `dry`. Write a
  plain-language page: what runs itself, what waits for a click, what to do
  when something is red. A plan to host later is not this. A container file
  with no such work is not this. Words do not install the chassis. Do not add
  an image file to turn a test green.
- **Share or publish the repository.** Before the first push that would make
  the repo public or shared beyond the owner: two repositories. A sealed
  **brain** (private forever: strategy, candid plans, post-mortems, the wiki,
  the firewall denylist) and a publishable **body** (assume everything
  committed there becomes public). Public-safe pages are promoted one page at
  a time, never bulk-synced. The body gets the firewall (`spec/firewall.md`,
  install step 7). Look at what is already committed before anything leaves.
  A page the product might publish later is not this: the repo can stay
  private while Publish still gates that page.
- **Something would be sent out.** A tool would read the repository (an outside
  reviewer, or any hosted review service), or the product would send
  information to anyone but the owner. Write the decision before the first
  send. On a company repo, approval comes before enablement. Do not discover
  either one from the first run.

## Install steps

Create the **new** project directory first (default: a sibling of this kit clone).
Every arrow below is *from this clone* into **that** directory. Do not copy product
files into this checkout. Do not `cd` this clone into becoming the app.

1. **Copy the core files** into the new project directory.
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
   repo, or `wiki/` in the one-repo shape). That copy includes `operating-model.md`: fill
   **Stated outcome** from what the project is about. Leave the constraint lines
   as the stand-up default (one repo, this computer, nothing sent out); a piece
   added later replaces the line it changes. Leave
   **Kinds of work** with the placeholder kind heading (`{{KIND_PLACEHOLDER}}`). The first session in the **project**
   folder fills kinds of work. The runnable gate below does **not** check that
   (the product tree is still empty). Set each page's frontmatter dates; write the
   first `decisions.md` entry — the stand-up default, dated, plus what the
   project is about. Do not record answers they were not asked.
4. **Roles.** Draft the project's product roles from `reference/claude/role-template.md`
   (fences are real paths — start narrow; widening is on the record). The roster is who
   may write which paths; kinds of work live on `wiki/operating-model.md`. Install the two
   function-role patterns: `reference/claude/harness-auditor.md` →
   `.claude/agents/harness-auditor.md` and `reference/claude/version-steward.md` →
   `.claude/agents/version-steward.md`, replacing origin path and instrument names with
   the project's own.
5. **Keeping current (not at stand-up).** Stand-up copies nothing in this step.
   Copy the arrows below later, when an image definition is already in the tree
   and the work is to keep that image current. A plan to host later is not this
   step. Fill every `__PLACEHOLDER__` and `__OWNER_GITHUB_LOGIN__`. Copying
   these tests into a project that has no Dockerfile fails the gate
   (`test_the_runtime_image_removes_pip_and_proves_it`). That failure means the
   chassis was copied too early: remove it. Do not add an image to turn the test
   green. The factory clone does not run these jobs against itself.
   - `reference/keeping-current/infra/` → `infra/`
   - `reference/keeping-current/app/` → `app/` (extend `selftest.py` with one
     real probe per service; a config read is not proof)
   - `reference/keeping-current/tests/` → `tests/`
   - `reference/keeping-current/templates/tests.yml` → `.github/workflows/tests.yml`
   - `reference/keeping-current/templates/deploy.yml` → `.github/workflows/deploy.yml`
     (apps that serve traffic only; a job-only stamp skips this)
   - `reference/keeping-current/templates/freshness.yml` → `.github/workflows/freshness.yml`
   - `reference/keeping-current/templates/weekly-note.yml` → `.github/workflows/weekly-note.yml`
   - `reference/keeping-current/templates/dependabot.yml` → `.github/dependabot.yml`
   - `reference/keeping-current/templates/CODEOWNERS` → `.github/CODEOWNERS`
   Do not copy `dependabot-automerge.yml` here. Then follow `adapters/github-azure.md`
   (identities, contracts, adoption A–F). The routine lane starts OFF. The
   version-steward reads the weekly note; it does not bump pins by hand on this
   project.
6. **Stamp the project** — the fingerprint that makes poll and harvest possible. This is
   the only stamp method; a new project and an existing consumer run the same command.
   It does **not** copy kit files (install is steps 1–5). It fingerprints the
   STANDUP-mapped dests that **already exist** in this tree, writes `kit-files.txt`
   (project paths) and `kit-manifest.json` (hashes + the kit's current `kit_version`).
   Destinations that are not installed are not named, so `classify` `missing` does not
   fight "do not silently restore." Kit-repo-only paths (`spec/`, `adapters/`, this clone's `CLAUDE.md` /
   `AGENTS.md` / `START-HERE.md`, …) stay in the kit. `kit-manifest.json` is the
   output, not a member of the list. `--project` is the **new** folder, not this
   clone.

   ```sh
   python scripts/kit_stamp.py --project <new project folder> --kit <harness-kit clone>
   ```

   Before the copy in step 1 exists, the same file from the clone is the same method:
   `python <clone>/reference/tools/kit_stamp.py --project <new project folder> --kit <clone>`.
   `--dry-run` prints the plan. `--refresh` rebuilds an existing stamp from the current
   tree. Do not hand-edit a copied kit `kit-files.txt` — that is a second mapping and
   it will drift. Commit both files. A project without this stamp cannot poll or harvest.
   Later: `python scripts/kit_poll.py --project . --kit <harness-kit clone>`
   (`spec/versioning.md`). To offer local customizations back to the kit:
   `python scripts/kit_harvest.py --project . --kit <harness-kit clone>`
   (proposal-only; never copies into the kit). Never self-apply.
7. **(When the repository would be shared or made public) Arm the firewall** per
   `spec/firewall.md`: author the scanner in the body repo, seed the denylist in
   the brain repo from your own hard constraints, sync the secret, record the
   hash. Not at stand-up.

## Adoption D (keeping-current, after drills — not stand-up)

After the canary drills and `ROUTINE_LANE=on`, copy auto-merge. The workflow
no-ops while the variable is not exactly `on`.
- `reference/keeping-current/templates/dependabot-automerge.yml` → `.github/workflows/dependabot-automerge.yml`

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

One red test is not a pass with an asterisk. If the only failure is
`test_the_runtime_image_removes_pip_and_proves_it` and the folder has no
Dockerfile, the chassis was copied before the work asked to keep an image
current. Remove it and re-run. Do not stub an image, and do not record a red
gate as the normal stand-up result.

**What a failing gate means — plainly:** the harness you just stood up does not enforce
what its documents claim, and every promise in `HARNESS.md`'s mechanical column is
currently false. Do not proceed to real work on the assumption that it mostly works: a
guard that is wired but never fires is indistinguishable from a working one until the day
it matters (the origin measured exactly this — 23 commands that should have been denied,
0 denied, because a settings file lived in the wrong commit). Fix the wiring, or move the
affected rows of the coverage table to doctrine-only in writing so the record stays
honest, and record the gap in `wiki/decisions.md`.

When the gate passes, tell the human the new folder path. They close this kit clone
and open that folder. The first session there fills **Kinds of work** if a heading is
still `{{KIND_PLACEHOLDER}}`, confirms the outcome in one sentence (the shape on
that page — never jobs), then starts product work. This checkout stays the kit.

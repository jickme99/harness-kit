# STANDUP — cold-starting a new project from this kit

A human who is not technical opens **this kit clone** in Claude, Cursor, or ChatGPT
Codex. The front door is `CLAUDE.md` (Claude) / `AGENTS.md` (Cursor and ChatGPT Codex)
/ `START-HERE.md`. ChatGPT in the browser does not auto-read those files — they paste
the prompt in `START-HERE.md`. You stand up a **separate** project folder. This clone
stays the kit. They never run stamp, poll, harvest, or pytest — you do. When the gate
passes, they close this folder and open the new one.

Written to be executed by an AI agent, with its human answering the questions. Work
top-to-bottom; do not skip the questions to get to the install steps. Ask about
**today**. A prediction is not an answer. If they do not know, or they do not want
the quiz, use the defaults and say so in `wiki/decisions.md`: this computer, the
repository is not shared, no outside reviewer, the product does not send data out
yet. Two answers change what gets installed: a repository that is public or shared
**now**, and a container image that **already exists**. The other two are written
down and copy nothing. Visibility and where-it-runs are provisional — the decision
records what re-opens them. One answer is a compliance matter (company material
leaving the house). The protocol ends in a **runnable gate**; a project is not
stood up until the gate passes. Do not turn this kit checkout into the product.

## Question 1 — the visibility question (decides the repo shape)

> **"Is this repository public today, or shared with anyone besides you?"**
> A page, app, or report you might publish later is not a yes. Saying yes installs
> a second repository and the firewall (`spec/firewall.md`).

- **YES, the repo is public or shared now → two-repo shape.** A sealed **brain** repo
  (private forever: strategy, candid plans, post-mortems, the wiki, the firewall
  denylist) and a publishable **body** repo (the product; assume everything committed
  there becomes public eventually). Public-safe pages are **promoted deliberately,
  one page at a time, never bulk-synced** — anything that could never be public lives
  in the brain and does not leave it. The body repo gets the firewall.
- **NO (the default) → one-repo shape.** The brain is a `wiki/` folder inside the
  body. No firewall CI needed; everything else is identical.

**Provisional.** Record the answer as of today. A later public page, a shared
checkout, or making the repo public re-opens it: a new `wiki/decisions.md` entry,
then the two-repo shape if the repository itself would be shared. Do not install
the firewall because the product might be published later.

Everything else in the kit — master, roles, gates, guards, auditor, docs doctrine — is
identical across shapes. Shape is a stand-up-time answer, not a fork of the kit.

## Question 2 — the vendor question (before ANY adapter that sends repo content out)

> **"Are you turning on a tool now that sends this repository to someone else?"**
> An outside pull-request reviewer (Cursor's Bugbot) or any hosted review service
> counts. A tool you might turn on later is not a yes. Saying yes does **not**
> install that tool; it records the decision. The default is no.

- **Personal repos:** the owner's call. Ask, record the answer in `wiki/decisions.md`.
- **Corporate repos:** requires IT/security approval **BEFORE enablement, not after.**
  This is company IP crossing an organisational boundary through a tool someone switched
  on, and it fails the same way an information firewall does — quietly, and only visibly
  in hindsight. Do not install such an adapter without a recorded approval.

**Provisional.** "Maybe later" stays no until the day it is enabled. Enabling it
re-opens this decision, and the corporate approval still has to come first.

## Question 3 — where it runs today (decides whether the keeping-current chassis is copied)

> **"Where does this run today?"** The default is **on my machine**. Words do not install the chassis. An image definition already in the new folder does: workflows, a canary, and placeholders that must be filled before anything runs. Those workflows refuse to start while a placeholder remains. A plan to host later is not a yes, and neither is saying "there is a container" when the folder has no image file.

- **A container that serves traffic is already in this project** (a `Dockerfile` or
  other image definition is in the new folder) → copy the chassis including
  `deploy.yml` (install step 5). GitHub + Azure Container Apps is the proven method
  (`adapters/github-azure.md`). Spec: `spec/keeping-current.md`. Record the answer.
  Fill every placeholder. First two runs of every job are `dry`. Write a
  plain-language page for the owner: what runs itself, what waits for a click, what
  to do when something is red.
- **A container that is only a scheduled job is already in this project** → copy the
  chassis EXCEPT `deploy.yml`. There is no ingress to split. Job refresh uses
  `infra/refresh_rules.py`; the workflow stays per-project (not a filled-in
  template). Same fill-in, dry first, and owner page as above.
- **On my machine, or not built yet (the default) → skip the chassis.** Do not copy
  it because a website, a nightly job, or a cloud account might come later. The spec
  still applies as doctrine where it fits (pin installed bytes, three outcomes,
  refuse rather than guess). The version-steward (`spec/versioning.md`) remains the
  weekly reader.

**Provisional.** Record where it runs today, and the sentence that re-opens this:
an image definition lands in the tree and someone asks to keep that image current.
The chassis arrives then, by the same poll path as any other kit content — not at
stand-up, on a guess. Do not add a Dockerfile to make a gate green.

## Question 4 — the product-data question (records a constraint; copies nothing)

> **"Does the thing you are building send information to anyone but you?"**
> This is not Question 2. Question 2 is a tool that reads the repository. This is
> the product's own calls: a model vendor, a payment API, a customer's system.
> The default, until a spec says otherwise, is no.

- Record the answer in `wiki/decisions.md`. Copy no files.
- **Corporate repos:** company data leaving the organisation needs the same
  approval-before-the-fact as Question 2. Do not discover it from the first run.
- **Provisional.** A later spec that adds an outside call re-opens this entry
  before that call is built.

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
   **Stated outcome** from their words and the Question 1–4 answers as constraints; leave
   **Kinds of work** with the placeholder kind heading (`{{KIND_PLACEHOLDER}}`). The first session in the **project**
   folder fills kinds of work. The runnable gate below does **not** check that
   (the product tree is still empty). Set each page's frontmatter dates; write the
   first `decisions.md` entry — the answers to Questions 1–4, dated, each marked
   as of today, with the sentence that re-opens a provisional one.
4. **Roles.** Draft the project's product roles from `reference/claude/role-template.md`
   (fences are real paths — start narrow; widening is on the record). The roster is who
   may write which paths; kinds of work live on `wiki/operating-model.md`. Install the two
   function-role patterns: `reference/claude/harness-auditor.md` →
   `.claude/agents/harness-auditor.md` and `reference/claude/version-steward.md` →
   `.claude/agents/version-steward.md`, replacing origin path and instrument names with
   the project's own.
5. **Keeping current (only when an image definition is already in the new project).**
   Question 3's default copies nothing here. A plan to host later is not this step.
   Copy the chassis only when a `Dockerfile` (or another image definition) is already
   in the new folder; fill every `__PLACEHOLDER__` and `__OWNER_GITHUB_LOGIN__`.
   Copying these tests into a project that has no Dockerfile fails the gate
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
7. **(Two-repo shape only) Arm the firewall** per `spec/firewall.md`: author the scanner
   in the body repo, seed the denylist in the brain repo from your own hard constraints,
   sync the secret, record the hash.

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
`test_the_runtime_image_removes_pip_and_proves_it` and the new folder has no
Dockerfile, the chassis was copied on a prediction. Remove it and re-run. Do not
stub an image, and do not record a red gate as the normal stand-up result.

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

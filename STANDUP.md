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
   - `reference/guards/*.py` → `scripts/` in the project. Set the marked install-time
     seams (the probe pack's second-repo path/slug and gh account; the merge guard's
     `HARNESS_GH_ACCOUNT` if the machine has multiple gh logins).
   - `reference/tools/kit_manifest.py` → `scripts/`.
   - `tests/` (the guard contract tests) → the project's `tests/`, adjusting the guard
     paths at the top of `tests/guard_registry.py` if your scripts live elsewhere.
   - `templates/pr-template.md` → `.github/pull_request_template.md`, placeholders filled.
2. **Install the guards' wiring for your tool** — per the adapter doc (`adapters/claude.md`,
   `adapters/cursor.md`, `adapters/codex.md`). For Claude Code that is
   `reference/claude/settings.json` → `.claude/settings.json` (and optionally the
   user-level layer; see `spec/guards.md` on why two layers exist). For a harness without
   hooks, the adapter doc tells you what you are carrying as doctrine instead.
3. **Instantiate the wiki skeleton.** `templates/wiki/` → the brain (`wiki/` in the brain
   repo, or `wiki/` in the one-repo shape). Set each page's frontmatter dates; write the
   first `decisions.md` entry — the answers to Questions 1 and 2, dated.
4. **Roles.** Draft the project's product roles from `reference/claude/role-template.md`
   (fences are real paths — start narrow; widening is on the record). Install the two
   function-role patterns (`harness-auditor.md`, `version-steward.md`), replacing the
   origin's path and instrument names with the project's own.
5. **Generate the kit manifest** — the project's stamp, and the hook for future upgrades:
   ```sh
   python scripts/kit_manifest.py generate --list kit-files.txt --root . --version 2026.09 --out kit-manifest.json
   ```
   where `kit-files.txt` lists the kit-owned files you just installed (copy the kit's own
   list as a starting point and edit it to your layout — membership is a decision, not a
   glob). Commit both files.
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

Pass = tests green, the probe reports every guard wired with its target existing at the
layer your tool uses, and the live probes are refused.

**What a failing gate means — plainly:** the harness you just stood up does not enforce
what its documents claim, and every promise in `HARNESS.md`'s mechanical column is
currently false. Do not proceed to real work on the assumption that it mostly works: a
guard that is wired but never fires is indistinguishable from a working one until the day
it matters (the origin measured exactly this — 23 commands that should have been denied,
0 denied, because a settings file lived in the wrong commit). Fix the wiring, or move the
affected rows of the coverage table to doctrine-only in writing so the record stays
honest, and record the gap in `wiki/decisions.md`.

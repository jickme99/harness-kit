# harness-kit

**New project:** clone this repo, open **this folder** in Claude, Cursor, or
ChatGPT Codex, and say what you want to build. Claude reads `CLAUDE.md`; Cursor
and ChatGPT Codex read `AGENTS.md`. The agent stands up a **separate** folder.
This clone stays the kit. You then open the new folder and work there. You do
not run stamp or poll commands. ChatGPT in the browser does not auto-read the
repo — paste the prompt in `START-HERE.md`.

**A specification with teeth for running a project as one master agent, many disposable
role-cast workers, and a human at exactly two gates — extracted 2026-09-01 from a live
venture after ~5 weeks of operation and a 4-day harness hardening.**

This kit is a **spec with teeth, not a turnkey harness**. It does not promise working
enforcement on every model and IDE. It promises three layers per guarantee:

1. **The specification** (`spec/`) — what enforcement must do, why each rule exists (the
   real failure that taught it), and each guard's safe direction.
2. **A reference implementation** (`reference/`) — proven in Claude Code: three PreToolUse
   guards, a probe pack, the measurement tools, the CI gate patterns, and the per-tool
   configuration files. Proven here; a sample elsewhere.
3. **Portable contract tests** (`tests/`) — the teeth. Plain Python + pytest, no project
   dependencies. Any re-implementation of a guard, in any language, on any harness, must
   pass them: novel input lands on the declared safe side, every time. **The portable part
   is the TEST, not the hook.**

**The honest promise: a massive head start for any capable agent on any IDE/model — not
turnkey.** On Claude Code, every mechanical guarantee is live out of the box. On anything
else, the adapter's coverage table (`adapters/`) says exactly which guarantees are
mechanical, which are standalone-checkable, and which you are personally holding as
doctrine — and which rows are REQUIRED for stand-up vs IF-AVAILABLE. Nothing here
pretends a rule is enforced when it is only written down.

Two more promises the kit makes about the projects it stamps:

- **Every stamped project works from a cold start ON THE PROJECT REPO ALONE.** The spec
  installs INTO projects (`templates/HARNESS.project.md` and friends); this repo is where
  it originates and is versioned. A model that has never seen this kit, opening only the
  project, can answer: *what harness does this project run, what does each tool-specific
  piece do, and what must I honor even though I cannot execute it?*
- **Self-updating is PROPOSAL-ONLY.** Projects poll the kit (`CHANGELOG.md` vs their
  stamp's `kit_version`) and apply through their own Merge gate — never self-apply.
  Stamp: `reference/tools/kit_stamp.py` (STANDUP step 6; the same command for every
  project). Poll: `reference/tools/kit_poll.py`. Harvest: `reference/tools/kit_harvest.py`
  (offer customizations back; never copies into the kit). Recipe: `spec/versioning.md`.
  Kit-opens-PRs is later automation (consumer #2). Current kit version is in
  `kit-manifest.json` and in `CHANGELOG.md`.

## Honest limits

- The guards are **mistake-preventers for an agent trying to comply, not sandboxes** —
  deliberate obfuscation defeats them, and each file names its residual holes.
- **Claude Code** is proven in production. **Cursor** enforcement hooks were verified
  2026-09-01 on the origin (see `adapters/cursor.md`); remaining Cursor rows are doctrine
  or residual. **Codex is untested** and its adapter says so.
- Several guarantees are **doctrine-only on every harness** (the wiki protocol's
  auto-write, the commit protocol, the report contract). The coverage tables read the
  doctrine column as the list of promises you personally hold.
- The reference guards parse **POSIX-plus-PowerShell shell commands**; another tool
  ecosystem's command surface needs its own analysis against the same contract tests.

## The map

| Path | What it is |
|---|---|
| `START-HERE.md` / `CLAUDE.md` / `AGENTS.md` | Kit front door. This clone is the factory; stand up a sibling project. Not the product stubs in `templates/`. |
| `STANDUP.md` | The cold-start protocol for a NEW project — run by an AI agent with its human answering questions; ends in a runnable gate. |
| `spec/` | One page per subsystem: `operating-model` (including the work map: kinds of work inferred onto `wiki/operating-model.md`) · `guards` · `review` · `wiki-protocol` · `firewall` · `versioning` · `graduation` · `keeping-current`. Invariants, failure history, mechanics, and what a re-implementation must achieve. |
| `reference/guards/` | The three guards + the probe pack, copied faithfully from the origin (install-time seams marked). |
| `reference/tools/` | `kit_manifest.py` (upgrade classifier) · `kit_stamp.py` (the stamp method; fingerprints dests that exist) · `kit_poll.py` (changelog worklist + STANDUP mapping; never copies files) · `kit_harvest.py` (proposal-only offer of customized/extra files) · `review_stamp.py` (config stamper) · `review_rates.py` (catch/escape rollup). |
| `reference/ci/` | The docs-gate (four fail-closed PR gates) and firewall-on-push workflow patterns, with EXAMPLE markers. |
| `reference/keeping-current/` | Optional chassis, copied when the work is to keep an image that already exists current. Not at stand-up, and not because one might exist later. Freshness rules, canary, weekly note, GitHub/Azure templates. Spec: `spec/keeping-current.md`. |
| `reference/claude/` | Hook wiring sample, role-file template, and the two function-role patterns (harness-auditor, version-steward). |
| `reference/cursor/` | The `.mdc` pointer-rule pattern, the outside-the-lane tripwire, `BUGBOT.md`, and verified hooks (`hooks.json`, `bridge.cmd`, `hook_bridge.py`). |
| `adapters/` | Per-tool install instructions + an honest coverage table each: `claude.md` · `cursor.md` · `codex.md`. Deploy stack: `github-azure.md` (IF-AVAILABLE). |
| `templates/` | What gets installed into a project: `HARNESS.project.md`, the `CLAUDE.project.md` / `AGENTS.project.md` / `START-HERE.project.md` pointer stubs, the wiki skeleton (including `HANDOFF.md` and `operating-model.md`), the PR template. |
| `tests/` | The portable guard contract tests (stdlib + pytest). Run `python -m pytest tests/ reference/keeping-current/tests/` in this repo. Guard tests copy into every stamp; keeping-current tests copy only when that chassis is installed. |
| `kit-files.txt` / `kit-manifest.json` | The kit's membership (a decision, not a glob) and its checksummed fingerprint (`kit_version`). |
| `CHANGELOG.md` | The poll surface: what changed after a given `kit_version`, who it applies to, lane. |
| `TODO.md` | Known gaps, honestly. Not a release log. |
| `inbox/` / `outbox/` | Owner drop-boxes (files in / files out). Gitignored; not kit membership. |

## Origin

Extracted from a working two-repo venture (a private brain repo + a public-trajectory body
repo) that ran this harness live: ~5 weeks of operation, dozens of PRs through the review
loop, three guards graduated from real incidents (see `spec/graduation.md`), and a 4-day
hardening pass in which an external reviewer, a contract-test suite, and a cold-start
audit each found real defects the harness then encoded. The failure histories quoted in
`spec/` and in the guards' docstrings are that record — they are the part of the kit that
took five weeks to earn and five minutes to copy.

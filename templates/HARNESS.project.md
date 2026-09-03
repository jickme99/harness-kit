<!-- harness-kit 2026.09 — project HARNESS template. Fill every {{...}} placeholder and
     delete instruction comments like this one. This file is the project's tool-neutral
     CONSTITUTION: tool entry points (CLAUDE.md, AGENTS.md, .cursor rules) POINT here. -->

# HARNESS — the rules this repo runs under, for any agent on any tooling

**Read this before acting in this repo from anything other than {{THE PROVEN TOOL, e.g.
"Claude Code on the owner's workstation"}}.** This file is the tool-neutral constitution
for `{{repo-name}}`: the rules stated as rules, the mechanical enforcement that exists for
some of them, and — honestly — which protections a given harness actually has. The
acceptance test this file must pass: an agent that has never seen this project, opening
only this repo, can answer *"what harness does this project run, what does each
tool-specific piece do, and what must I honor even though I cannot execute it?"*

**What this repo is:** {{one paragraph: the repo's role; if two-repo shape, name the
sibling and which half this is, and note that the sibling carries its own HARNESS.md — do
not assume the two are identical.}}

---

## 1. The rules

<!-- Each rule stated AS A RULE, with one line of why. The guards' own docstrings carry
     the full failure history. Keep the kit's core rules that apply; add the project's
     own. Number them — the tables below refer back by number. -->

1. **Every `az` invocation pins `--subscription` explicitly — every one, including
   chained, substituted, or wrapped invocations.** {{Why, in one line — e.g. the
   workstation's default subscription may point at an unrelated tenant.}} Enforced by
   `scripts/az_guard.py`. <!-- Delete if the project touches no Azure; keep the pattern
   for whatever cloud CLI carries the same cross-context hazard. -->
2. **Every git command that can destroy, discard, rewrite, relocate, or delete work names
   its repository: `git -C <ABSOLUTE path> ...`.** Ambient working directory is unreliable
   state. Enforced by `scripts/git_scope_guard.py`.
3. **`gh pr merge` only when the PR's checks are green.** A red branch does not merge.
   Enforced by `scripts/merge_green_check.py`. (A repo/branch with no workflow runs at all
   is allowed — the guard gates repos that have CI; it does not invent CI.)
4. **Wiki protocol: `wiki/decisions.md` and `wiki/log.md` are append-only; wiki updates
   are written automatically as work progresses, without asking permission.** Asking
   creates staleness; git makes corrections trivial. Doctrine; spec in the kit's
   `spec/wiki-protocol.md`, house specifics in {{pointer}}.
5. **Commit protocol: auto-commit + push when a logical unit of work is complete; never
   auto force-push, rewrite history, or delete branches.** Format
   `<type>: <one-line summary>` + bullets. Doctrine. Note: force-push is governed here,
   not by the git scope guard — that guard asks only "did you name the repo".
6. {{Two-repo shape only: **the firewall rule** — nothing that could never be public
   leaves the brain repo; public-safe pages are promoted deliberately, one at a time,
   never bulk-synced. Deny-terms and mechanics: {{pointer to the brain repo's firewall
   runbook}}.}}
7. {{The project's own hard rules, each with its one-line why.}}

## 2. The guards — spec per guard

All guards share one contract, so any harness can use them:

- **Input:** a JSON document on stdin:
  `{"tool_name": "Bash", "tool_input": {"command": "<the command about to run>"}}`.
- **Output:** on refusal, a JSON document on stdout carrying
  `hookSpecificOutput.permissionDecision: "deny"` and a human-readable
  `permissionDecisionReason`. On allow: **silence**. Exit code 0 either way —
  deliberately, because a *crashed* hook is treated as no-decision (an allow), so the
  guards never signal through exit codes; internal errors become denials, not crashes.
- **Standalone fallback for harnesses without hooks:** pipe the payload in and treat any
  stdout as a refusal:

  ```sh
  echo '{"tool_name":"Bash","tool_input":{"command":"az group list"}}' \
    | python scripts/az_guard.py
  # non-empty stdout => refused (the JSON says why); empty stdout => allowed
  ```

  A harness that cannot even do that must honor the rules in §1 as doctrine.
- **Scope:** mistake-preventers for an agent trying to comply, not sandboxes. Deliberate
  obfuscation defeats them; the residual holes are named in each file's docstring.

| Guard | Rule enforced | {{Tool}} wiring | Timeout |
|---|---|---|---|
| `scripts/az_guard.py` | §1.1 | PreToolUse on `Bash\|PowerShell` in `.claude/settings.json` | 15s |
| `scripts/git_scope_guard.py` | §1.2 | same | 15s |
| `scripts/merge_green_check.py` | §1.3 | same | 45s (calls `gh`) |

**How to verify:** `python scripts/harness_probes.py --probe guard_wiring`, then a live
negative test — ask the harness to run a command a guard must refuse but which touches
nothing if it runs, and confirm the refusal.

## 3. Coverage — what a given harness actually has

<!-- Fill honestly per this project. The kit's adapters/ files carry per-tool starting
     tables. Read the doctrine-only column as the promises an agent personally holds when
     working here from a harness without hooks. -->

| Guarantee | Mechanical in {{proven tool}} | Standalone-checkable on any harness | Doctrine-only |
|---|---|---|---|
| az pins `--subscription` | {{yes/no + how}} | yes — pipe payload to `az_guard.py` | fallback |
| Destructive git names its repo | {{...}} | yes | fallback |
| Merge only on green checks | {{...}} | yes (needs `gh` auth) | fallback |
| {{CI gates, if any}} | {{server-side — list the workflows}} | n/a | — |
| Wiki append-only + auto-write | no | partially — probe pack | **yes** |
| Commit protocol | no | no | **yes** |
| {{firewall row, two-repo shape}} | {{...}} | {{...}} | **yes** |

## 4. Pointers, not copies

<!-- The operating model is specified once, in the wiki — this file points, it does not
     restate. A rule written twice is a rule that will drift. -->

- `wiki/{{operating-model page}}` — the agent operating model: one master, disposable
  role-cast agents, worktree isolation, the two owner gates (Merge may be delegated to
  the master when green; Publish is never delegated).
- `wiki/{{review page}}` — the review-lens roster and loop caps.
- `.claude/agents/*.md` — the role roster; each `fence:` frontmatter block is the
  machine-readable list of paths that role owns.
- `CLAUDE.md` — the Claude Code entry point (points back here).
- {{other tool entry points and house pages}}

## 5. The honest promise

This file is a **head start, not a turnkey harness**. On {{the proven tool}}, every
mechanical row above is live. On anything else, you get exactly what §3 says you get:
guards you can consult but that nothing forces you through, plus doctrine you must carry
yourself. If a guard refuses something you believe is correct, stop and surface it — do
not restructure the command to slip past the guard.

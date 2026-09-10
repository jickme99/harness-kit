# Spec: the guards

Three mistake-preventers, one shared contract. This page is the enforcement layer's spec:
the invariants any implementation MUST hold, the failure history behind each, the reference
mechanics, and what a re-implementation on another harness must achieve. The reference
implementations are `reference/guards/`; the portable contract tests are `tests/` — **the
portable part is the TEST, not the hook.**

## The shared contract (MUST)

- **Input:** one JSON document on stdin:
  `{"tool_name": "Bash", "tool_input": {"command": "<the command about to run>"}}`.
- **Output on refusal:** a JSON document on stdout carrying
  `hookSpecificOutput.permissionDecision: "deny"` and a human-readable
  `permissionDecisionReason` that says exactly what to fix. On allow: **silence** — no
  output at all.
- **Exit code 0 either way — deliberately.** In Claude Code a *crashed* hook is treated as
  no-decision, i.e. an ALLOW. A guard that signaled refusal through a nonzero exit would
  therefore fail OPEN on its own bugs. So the deny path is the JSON document, nothing
  escapes `main()`, and internal errors are converted into denials rather than crashes.
- **Fail-closed on unparseable input, stated precisely.** A command that mentions the
  guarded program as a WORD and cannot be parsed is DENIED with a reason naming the parse
  failure. Unparseable input WITHOUT such a mention is passed over in silence — refusing
  `echo don't` is the usability failure that gets a guard switched off, and a switched-off
  guard protects nothing. **Usability is a security property.**
- **A payload the guard cannot read lands on the deny side.** `-EncodedCommand`'s base64,
  `-File`'s path, a flag nobody has thought of: absence of the guarded string proves
  nothing inside an opaque payload.
- **Scope: mistake-preventers, not sandboxes.** Deliberate obfuscation defeats them
  (`$AZ_BIN`, a script file the guard cannot read, `ssh host '...'`). Each residual hole is
  named at its site in the source; an implementation must be equally honest about its own.

## The three guards, each with its safe direction

| Guard | Rule | Safe direction | Born from |
|---|---|---|---|
| `az_guard.py` | every `az` invocation pins `--subscription` — every one, including chained, substituted, wrapped | **deny** | a workstation whose default subscription points at an unrelated tenant; the danger is highest exactly when switching contexts |
| `git_scope_guard.py` | a git command that can destroy/discard/rewrite/relocate/delete work names its repository: `git -C <ABSOLUTE path>` | **deny** — and the refusal is never "you may not", only "say which repository" | three incidents in one hour, all one shape: a command whose meaning depended on ambient state nobody restated; one `reset --hard` destroyed two commits (reflog recovered them) |
| `merge_green_check.py` | `gh pr merge` only when the PR's checks are green | **deny** on unparseable merge commands and non-green/running checks; a repo with NO workflow runs at all is allowed (the guard gates repos that have CI; it does not invent CI) | ten merges sailed past a red main in week one |

## Why the safe set is the enumerated one (the load-bearing design rule)

The defect class the origin hand-fixed most — nine times — is **fail-open enumeration**: a
finite list standing in for an infinite one, where a value not in the list is treated as
safe. So: *where a class must be recognised, enumerate the members the guard can PROVE it
handles and refuse the rest* — a missing spelling lands on the deny side. The git guard
enumerates the provably-SAFE subcommands and forms; a subcommand git grows next year is
refused until someone proves it safe. This inversion is affordable exactly because the
remedy is one flag, always available and always correct. The az guard, whose refusal CAN
block an operation outright, instead enumerates its local-only groups — a deliberate
enumeration that fails toward DENIAL (a missing entry is an annoying false denial, a wrong
entry would be a hole).

Its twin rule: **a false denial's severity is how often the blocked thing is done, not how
exotic the construct looks.** The az guard's first live act was a false denial of the most
routine write in the project (a here-doc wiki entry whose PROSE mentioned the CLI) — filed
`later` by an external reviewer because the construct looked exotic. A guard that refuses
routine work gets switched off.

## The parsing history (why the guards are ~800 lines and not a regex)

Every earlier version reasoned about the command as TEXT, or as structure recognised by
SPELLING, and each one leaked: the pin found anywhere in the whole string (v1 — a chained
second command inherited a flag it never carried); regex splitting that failed open through
`bash -c`/`$(...)`/`xargs` and failed closed on prose mentioning the CLI (v2); enumerations
anchored at the wrong end (`bash -xc` vs `bash -cx`), `eval` recognised only at token 0
(v3). The surviving design: lift here-doc bodies FIRST and judge them by their CONSUMER
(a body fed to a shell is code; fed to `cat` it is text the guard never reads); lift
command substitutions quote-aware; tokenize POSIX with punctuation split out; follow shell
`-c` payloads, `eval` arguments, and pipelines into stdin-reading shells to any depth;
decide command position without a wrapper whitelist. Read the module docstrings — they are
the annotated failure ledger, and they are part of the extracted value.

**Guards are scripts with tests, never inline one-liners.** The az guard's bypass survived
as long as it did because the guard lived as escaped JSON inside `settings.json`, where
nothing could exercise it. Any guard whose logic exceeds a literal path comparison lives in
a file with a test module carrying BOTH controls: the case it must block, and the cases it
must not.

## Wiring in the reference (Claude Code)

`reference/claude/settings.json` wires all three as PreToolUse hooks on `Bash|PowerShell`
at PROJECT level via `${CLAUDE_PROJECT_DIR}` — this travels with every clone. The origin
also wires them at USER level (`~/.claude/settings.json`, machine-absolute paths) because a
project-level settings file lives in the checked-out COMMIT: a worktree branched before it
landed is silently unguarded — measured, that gap let 23 deniable commands through with 0
denials. Wire a guard where the MISTAKE can happen, not where the project is: the az and
git hazards are cross-project (ambient state is machine-wide), the merge guard is
per-repo. Both layers firing on one machine is deliberate defense-in-depth; the guards are
read-only and idempotent, and a doubled denial costs nothing.

Known residual, recorded rather than hidden: the hooks invoke bare `python`. A missing
SCRIPT exits 2 and blocks (loud, safe); a missing INTERPRETER exits 127, which Claude Code
treats as non-blocking — the silent failure mode. The mitigations are the wiring probe
(`harness_probes.py --probe guard_wiring`, which reports Claude and Cursor layers
separately — a missing unused adapter is a fact, not a fail — and reports the
interpreter rather than assuming it) and a live negative test. Cursor's extra
`hooks/` directory is load-bearing: `hooks.json` calls `.cursor/hooks/bridge.cmd`,
and the `.cmd` only resolves `scripts/` from that folder.

## What an implementing agent must achieve on another harness

1. **If your harness has pre-execution hooks:** wire each guard so the command about to run
   reaches its stdin in the contract shape, a refusal blocks execution, and — critically —
   determine what your harness does with a CRASHED hook. If a crash is an allow (as in
   Claude Code), keep the exit-0/deny-JSON discipline; if a crash blocks, say so in your
   adapter's coverage table, but never rely on it.
2. **If it has no hooks:** the guards still work as pre-flight CHECKS — pipe the payload in
   and treat ANY stdout as a refusal:
   ```sh
   echo '{"tool_name":"Bash","tool_input":{"command":"az group list"}}' \
     | python scripts/az_guard.py
   # non-empty stdout => refused (the JSON says why); empty stdout => allowed
   ```
   Doctrine then carries the obligation to actually run the check before running the
   command.
3. **Pass the contract tests.** `tests/test_guard_contracts.py` drives each guard over
   GENERATED novel input — composed shell wrappers, invented subcommands, unparseable
   fragments — and requires the declared safe verdict every time. A re-implementation in
   any language passes the same tests by honoring the same stdin/stdout contract. A
   port that passes only a list of literal strings has re-created the failure the
   generators exist to prevent (a 104-literal suite once stayed green through four
   separate bypasses).
4. **Prove the wiring live.** Ask the harness to run a probe command the guard must refuse
   but which touches nothing if it runs (`az vt-probe-does-not-exist` — NOT `az group
   list`), and confirm the refusal. A guard that cannot be shown to fire is decoration.
5. **If a guard refuses something you believe is correct: stop and surface it.** Never
   restructure the command to slip past the guard — a refusing guard is a finding, one way
   or the other.

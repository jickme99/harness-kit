<!-- harness-kit 2026.09 — AGENTS.md pointer stub. Cursor and Codex read this file
     natively. The constitution is HARNESS.md; tool entry points point at it rather than
     restating it (a rule written twice will drift). Add ONLY what is genuinely
     tool-specific here. If this path already exists in the repo, read it first — do not
     overwrite an install runbook or other job with this stub. -->

# {{Project name}}

**The constitution for this repo is `HARNESS.md` — read it first.** It states the rules,
the guards that enforce some of them, and the honest coverage table for what this harness
actually holds.

## Session start protocol

Read in order:

1. `START-HERE.md` — last decision, next task, kit version, what is not in this repo
2. `HARNESS.md`
3. `wiki/HANDOFF.md` then `wiki/status.md` — where things stand
4. `wiki/feedback.md` — owner preferences (prevents repeat mistakes)
5. For {{strategy/content}} work: `wiki/{{strategy page}}` · for build work:
   `wiki/{{roadmap page}}` and the relevant plan page

## Tool-specific wiring (what this file exists for)

- Cursor: project rules in `.cursor/rules/`; enforcement hooks in `.cursor/hooks.json`
  (bridge at `.cursor/hooks/bridge.cmd` — that extra `hooks/` directory is load-bearing).
- Codex: until a hook surface is verified, run the guards as pre-flight checks
  (`spec/guards.md`) before any command they cover.
- {{Anything else genuinely tool-specific.}}

## Wiki + commit protocols

Defined in `HARNESS.md` §1 (rules 4–5) and the kit spec they came from. Short form:
update the wiki automatically as work progresses — decisions/log are append-only;
auto-commit + push at each logical unit; never auto force-push, rewrite history, or
delete branches.

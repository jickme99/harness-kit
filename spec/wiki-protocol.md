# Spec: the wiki protocol

The project's brain: a plain-markdown wiki that is the durable record of decisions,
findings, lessons, and state. The skeleton ships in `templates/wiki/`. It works on any
harness because it is only markdown + git + discipline — which also means every invariant
here is doctrine unless a probe or gate is wired to check it.

## The invariants (MUST)

1. **`decisions.md` and `log.md` are append-only.** A decision is superseded by a NEW dated
   entry that names what it supersedes — never by rewriting the old one. History that can
   be edited is not a record.
2. **Auto-write, without asking.** Wiki updates land as work progresses: decisions with
   date + rationale, findings, feedback, log entries, status. **Asking permission creates
   staleness; git makes corrections trivial.** The failure mode this prevents is a status
   page describing last week while the log describes today.
3. **Snapshot pages carry honest frontmatter.** Every page has YAML frontmatter (`title`,
   `type`, `created`, `updated`, optional `tags`, `related`); snapshot pages (status, the
   operating-model page) are measured against the append-only log — both what the
   frontmatter CLAIMS (`updated:`) and what the body SAYS (its newest non-future date).
   The distinction exists because bumping `updated:` without rewriting the page scored
   clean until an audit found a status page claiming currency while its body described a
   fleet three versions old.
4. **Log entries have a fixed shape:** `## [YYYY-MM-DD] <type> | <one-line summary>` +
   bullets; one entry per logical chunk of work. The shape is what makes the log
   machine-readable enough for the staleness probe.
5. **Lessons land as diffs, not paragraphs.** Every feedback/lessons entry ends with a
   fixed machine-parseable marker on its own line — `→ encoded: <path>` (what the lesson
   changed: a role file, a check, a hook, a brief template) or `→ noted-only: <reason>`.
   A lesson's terminal state is a diff; wiki prose is the intermediate form. The
   disposition probe flags unmarked in-scope entries as OPEN LOOPS at every close-out,
   with the window anchored at the RULE'S epoch, not the last audit — a since-last-audit
   window would let an ignored flag silently expire when the next audit ran.
6. **Close-out is a protocol, not a habit.** When the owner ends a session: (1) the
   session narrative — wins, friction, decisions, feedback patterns, confidence flags,
   direction not yet acted on; (2) quick fixes with confirmation; (3) the completeness
   check — every decision/finding/feedback/log entry captured, gaps filled explicitly
   ("no lessons this session" must be SAID, not implied) — and the harness audit runs
   here; (4) poll the kit (`python scripts/kit_poll.py --project . --kit <clone>`) and
   record "caught up" or the worklist headings in `wiki/log.md` — never self-apply;
   harvest (`python scripts/kit_harvest.py --project . --kit <clone>`) is the offer
   path when this tree customized kit files — also never copy;
   (5) parking lot, next-session priming (`wiki/HANDOFF.md`), light lint, commit + push.
7. **Cross-references use `[[Page Title]]`**, and the index page is updated whenever a
   page is added, renamed or removed.

## Why

- **Append-only + auto-write** exist because the wiki is the substitute for memory in a
  model where workers are disposable and chats get compressed: durability lives in files,
  not conversations. A fresh session + the pages = the same project, nothing lost.
- **The disposition rule** exists because written-down is not learned: the origin found
  lessons repeating precisely because their terminal state was prose. The rule's closing
  principle: *every loop is judgment at the ends and machinery in the middle — an agent
  decides what a lesson means, code verifies the loop closed, the owner's gate decides
  what activates.*
- **The hedge-collapse lesson (carry it into every summarizing edit of this wiki):** a
  report that honestly writes a disjunction — "either A or B" — gets collapsed by
  downstream readers into one branch with no new evidence, and by the third retelling the
  surviving branch reads as fact. Nothing is fabricated at any step; the UNCERTAINTY is
  what fails to survive. **Repetition is not corroboration when every telling has the same
  single source.** When a wiki page summarizes a prior page, the hedge travels with the
  claim; a reader who resolves it without new evidence has manufactured a finding.

## Mechanics (reference)

- `reference/guards/harness_probes.py` carries the mechanical readers: `snapshot_staleness`
  (frontmatter AND body vs the log's newest entry) and `lesson_dispositions` (unmarked
  in-scope entries as open loops). Facts to machines, judgment to agents: the probes only
  count; the auditor reads.
- The harness-auditor role (`reference/claude/harness-auditor.md`) is the standing READER
  of these instruments — T1 (fix bookkeeping silently), T2 (dispatch, never touch),
  T3 (flag to the owner; the report LEADS with T3).

## What an implementing agent must achieve on another harness

Everything here is markdown and a Python script: it runs anywhere. What another harness
must supply is the HABIT — the auto-write triggers wired into its own session protocol
(constitution text), and the close-out run of the probes. Where nothing can run the
probes, the close-out checklist is executed by hand; "checked and clean" must still be
said per item, because silence and health are indistinguishable otherwise.

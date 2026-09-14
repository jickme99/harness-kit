# Spec: the operating model

One master conversation, many disposable role-cast agents, two owner gates. This page is the
subsystem's contract: what any implementation MUST hold, why each invariant exists (the real
failure that taught it), how the reference implements it, and what an implementing agent on
another harness must achieve.

## The invariants (MUST)

1. **Exactly one master.** One standing control-room session holds the roadmap, decomposes
   direction into jobs, dispatches workers, runs the review loop, opens PRs, and pings the
   owner at gates. The master does not edit product code — it briefs a worker instead.
   Never two concurrent masters: two dispatchers with no shared fence table break the
   one-writer rule at the root rather than at a path.
2. **Every other agent is disposable and role-cast.** A role is a definition on disk
   (see `reference/claude/role-template.md`), not a chat. A fresh agent is spawned into a
   role, works in an isolated worktree, reports, and vanishes. The owner never talks to
   workers directly.
3. **Two owner gates — Merge and Publish — and everything between them is autonomous.**
   Merge: the owner accepts a finished change into the default branch, **or** explicitly
   delegates routine Merge to the standing master, who squash-merges when checks are
   success / skipped / neutral. On a project that installed the keeping-current chassis
   (`spec/keeping-current.md`), a machine may also merge and deploy a *routine* change
   when live records prove it (bot-only verified range, hashed lock, canary). That is
   still the Merge gate, exercised by records — not a third gate and not a skipped one.
   Publish: anything public-facing stops for a human. The gates never loosen; narration
   between them loosens as chains prove clean. Workers never merge. The Publish gate is
   never delegated.
4. **Fences are real paths.** Each role file declares `owns` and `forbidden_notable` in
   machine-parseable frontmatter. Prose is for humans; the frontmatter IS the contract.
5. **One writer per path — and the rule is tool-agnostic.** The master never runs two jobs
   whose fences overlap; overlapping work queues. A writer the master does not control (a
   person in an editor, a second tool's lane) holds a fence exactly like a worker does,
   and the master refuses to dispatch into a held path.
6. **A worker that hits a fence STOPS — and that is a good outcome.** A stop-and-ask is the
   system working, never obstruction. Two fence hits on one job = the seam is wrong; the
   master pulls the job back and redraws it. A fence that is too narrow is the MASTER's
   error, widened on the record.
7. **The capped review loop.** Round 1 labels every finding must-fix / later / ignore;
   round 2 is must-fix only, on new commits; **max 2 rounds**; later/ignore residue goes to
   a recorded nits note, never a third round. A branch under review is frozen except
   must-fix responses.
8. **The report contract.** The report is the only artifact that crosses the worker/master
   boundary — the worktree is removed, the context is gone; what is not in the report did
   not happen as far as the record is concerned. Finishing means reporting the RESULT, not
   that a result is pending; a worker whose own CI is still running waits for it, and one
   that truly cannot says exactly what it left and where.
9. **Briefs carry what was UNCERTAIN, not just conclusions.** When a brief passes along a
   prior conclusion, it passes along the open disjunction with it, and instructs the worker
   that overturning the conclusion is an acceptable outcome. Repetition is not
   corroboration when every telling has the same single source.
10. **One tool per working copy.** Two agent tools on the same checkout share the git
    index, user-level hooks, and the `gh` account — those are machine-global, not
    session-local. Two masters on two dirty copies of one repo is two writers without a
    fence table. Memory that is not in the repo is tool-local; name it (which product's
    chat) and do not assume the other tool can see it. Fan-out ceiling is machine-local
    (CPU, RAM, API rate); do not hardcode a number.
11. **The work map is inferred and written; the owner never authors it.** The master
    decomposes direction into jobs (invariant 1) onto a project wiki snapshot
    (`wiki/operating-model.md`, or the house path `HARNESS.md` §4 points at), from
    STANDUP answers and the tree. The owner confirms the *outcome* once, in plain
    language, and is never asked to name jobs. Decomposition that is not on that page
    is chat, and does not survive the session. The report is the record of a job
    (invariant 8); the map is the record of a kind; dest files are products of a job
    and never a record of it; only the master writes the map.

## Why (the failures that taught these)

- **v1 of the model had the owner switching between standing sessions** — the exact burden
  the model exists to remove. Hence: one master, roles-not-chats, owner at gates only.
- **The fence-widening rule** came from three fences too narrow in one session — a roll
  authorized for jobs but not the surface that needed it, an env-var prohibition
  contradicting a documented deploy procedure, and a two-file guard registry split by a
  one-file fence. All three were caught by workers STOPPING rather than reading generously,
  which is the behavior to reward.
- **The report contract** came from two workers in one session returning "waiting on CI"
  with complete, correct work behind them — and the master reconstructing it from the repo,
  which is precisely the labor the report exists to prevent.
- **The uncertainty rule** came from a near-miss: an honest report wrote *"either the
  manifest is stale or the job is misconfigured"*; two downstream retellings collapsed the
  hedge to one branch, and a third queued a deletion that would have permanently broken an
  instrument. The counter that worked cost one paragraph in a brief: establish the facts,
  do not inherit the recommendation.
- **The capped loop** encodes the endless-nit lesson: an uncapped review loop converges on
  taste, not correctness, and burns the whole schedule doing it.
- **Spawn inherit** priced every worker at the master's cost the first time a costly
  control-room model dispatched a Task without a pin.
- **One tool per working copy** is the one-writer rule at machine scope: user-level
  hooks fire for every tool on the box, `gh` is whichever account is active, and two
  dirty checkouts of one repo have no shared fence table. Name tool-local memory
  rather than assuming the other product's session can see it.
- **Workshop invoke and mailbox** were measured on Cursor-as-master: asking the owner to
  paste a starting card was friction the spoken invoke already covered; the vendor cannot
  post from one Agent chat into another, so the durable mailbox is a dated Inbox on the
  notebook page, not a cross-chat write.
- **Unwritten decomposition** left `wiki/{{operating-model page}}` as a pointer with no
  template after extraction. The kit contract lives in this spec (kit-repo-only); a
  cold start on the project repo alone cannot read it. The next master then invented a
  new team or collapsed into one blob. Hence invariant 11 and the snapshot page.

## Mechanics (how the reference implements it)

- Role files live in the project's `.claude/agents/`; the master fills a per-job brief
  (goal, fence, done-looks-like, assumptions — the assumption sentence is the owner's
  ten-second catch-point) and spawns a subagent into the role in an isolated git worktree.
- **Spawn: pin a slug, never inherit.** If the harness's spawn API can inherit the parent
  chat's model, do not use it — a costly master then prices every worker the same. Pin a
  slug from the consuming project's vendor adapter table. Do not write those vendor names
  into Claude role-file `model:` fields (the model-policy CI still checks Claude tokens).
- **The dispatch-or-workshop test:** count conversations, not tasks. Work the owner does
  not need to steer is a dispatch (background, master pings at the Merge gate); work that
  is a conversation gets its own workshop chat pinned to one deliverable, whose durability
  lives in files, not the chat.
  - **Invoke:** the owner saying "this thread is a workshop" / "workshop on X" / `/workshop`
    **is** the invoke. Do not ask them to paste a card.
  - **The master chat does not convert itself into that workshop.** Open (or ask the owner
    to open) a separate chat; the control room stays the control room.
  - **Mailbox:** some harnesses cannot post from one agent chat into another (Cursor cannot).
    The mailbox is a dated Inbox on the workshop's notebook page; the owner pastes a
    one-line nudge. Shape: `- [YYYY-MM-DD] owner nudge: <one line>`.
  - **Two chats on the same deliverable are forbidden** — the one-writer rule applied to
    conversations.
- Three agent classes: the control room (exactly one, standing) · workshops (few, durable,
  one deliverable each, may spawn their own ephemeral helpers) · ephemeral role agents
  (many, one job each).
- Escalation is on evidence only: the same task failing detectably twice (tests red /
  verification rejects) re-runs exactly one model tier up, noted in the ledger. Never
  pre-emptive, never permanent.
- Fence hits, stop-and-asks and escalations each get one line in an events ledger
  (JSONL), whose reader is run at close-out — it surfaces the slow patterns no single
  session sees. Seam names are the CLASS, not the instance, or recurrences never collide.
- **Work map** (`wiki/operating-model.md` unless HARNESS §4 points at a house name):
  - **Page.** Stated outcome, stand-up constraints, roster pointers (not a copy of
    `owns:`), and Kinds of work. First fill: exactly one kind — the stated outcome —
    plus a pointer row for keeping-current if Question 3 said yes. A second kind only
    after that ask appears twice in `wiki/log.md`, unless the owner's words already
    named two independent expensive outputs. Infer from the outcome and the tree, not
    from the presence of `.git`. Checking is a different job from writing
    (`spec/review.md`).
  - **First session.** If this session is the standing master and a Kinds of work
    **heading** is still `{{KIND_PLACEHOLDER}}`, filling it is the first task —
    before product edits. The runnable STANDUP gate does **not** check this
    (empty tree). Confirm the outcome in the one sentence the template comment
    allows; never name jobs, workers, lanes, checkers, models, or counts of
    those to the owner. Workers and the Cursor lane beside a master do not
    write the map.
  - **Precedence.** The report is the record of a job; the map is the record of a
    kind; dest files are products of a job and never a record of it; only the master
    writes the map. Workers do not author `wiki/operating-model.md`.
  - **Fence hits.** A fence hit is a roster event (role file, invariant 6). It touches
    the map only when the fix splits or merges a job; then one `wiki/decisions.md`
    entry names both files. Otherwise the widening is recorded where it is today.
  - **Role backing.** Every job on the map names its role file, or says `master
    brief, fence: <paths>`. Do not invent empty product roles so a wiki-only tree can
    satisfy the map.
  - **Shape.** Record `dispatch` or `workshop` per kind (count conversations, not
    tasks). A kind the owner must steer is a workshop with one deliverable. Parallel
    jobs are for independent sources with an expensive check. Gate `none` only while
    the output stays in the brain; a body-repo default branch is Merge; leaving the
    house is Publish. A `redrawn:` date on the kinds section matches a decisions
    entry that names what it supersedes.

## What an implementing agent must achieve on another harness

- A way to cast a fresh agent into a role definition it did not write, with the role's
  fence stated in machine-readable form the agent can be checked against.
- Physical isolation per worker (worktrees or equivalent) so two writers cannot collide.
- One tool per working copy; user-level hooks and `gh` are machine-global; tool-local
  memory is named and not assumed visible to another product.
- Spawn pins a slug from the project's vendor adapter table and never inherits the parent
  chat's model. Vendor names stay in that table, not in Claude role-file `model:` fields.
- The two gates: opening a PR is automation. Publish is always a human click the owner
  makes and is never delegated. Merge may be delegated to the standing master, who
  squash-merges when checks are success / skipped / neutral; workers never merge.
- The stop-and-ask path: a worker outside its fence must have a cheaper move than
  improvising — and the culture (briefs, reviews) must treat a stop as success.
- The report and uncertainty contracts are doctrine on every harness: they are prose in
  briefs and role files, testable only by audit. Carry them even where nothing enforces
  them.
- A durable project page the next master reads before dispatching (`wiki/operating-model.md`
  or the house path HARNESS points at). The owner never authors it. Kinds of work are
  inferred and written. Dest files do not replace the report.

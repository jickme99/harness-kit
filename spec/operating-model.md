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
   Merge: the owner accepts a finished change into the default branch. Publish: anything
   public-facing stops for a human. The gates never loosen; narration between them loosens
   as chains prove clean. (The owner may delegate routine Merge clicks explicitly; the
   Publish gate is never delegated.)
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

## Mechanics (how the reference implements it)

- Role files live in the project's `.claude/agents/`; the master fills a per-job brief
  (goal, fence, done-looks-like, assumptions — the assumption sentence is the owner's
  ten-second catch-point) and spawns a subagent into the role in an isolated git worktree.
- **The dispatch-or-workshop test:** count conversations, not tasks. Work the owner does
  not need to steer is a dispatch (background, master pings at the Merge gate); work that
  is a conversation gets its own workshop chat pinned to one deliverable, whose durability
  lives in files, not the chat.
- Three agent classes: the control room (exactly one, standing) · workshops (few, durable,
  one deliverable each, may spawn their own ephemeral helpers) · ephemeral role agents
  (many, one job each).
- Escalation is on evidence only: the same task failing detectably twice (tests red /
  verification rejects) re-runs exactly one model tier up, noted in the ledger. Never
  pre-emptive, never permanent.
- Fence hits, stop-and-asks and escalations each get one line in an events ledger
  (JSONL), whose reader is run at close-out — it surfaces the slow patterns no single
  session sees. Seam names are the CLASS, not the instance, or recurrences never collide.

## What an implementing agent must achieve on another harness

- A way to cast a fresh agent into a role definition it did not write, with the role's
  fence stated in machine-readable form the agent can be checked against.
- Physical isolation per worker (worktrees or equivalent) so two writers cannot collide.
- The two gates as HUMAN actions your harness cannot perform: opening a PR is automation;
  merging and publishing are clicks the owner makes.
- The stop-and-ask path: a worker outside its fence must have a cheaper move than
  improvising — and the culture (briefs, reviews) must treat a stop as success.
- The report and uncertainty contracts are doctrine on every harness: they are prose in
  briefs and role files, testable only by audit. Carry them even where nothing enforces
  them.

# Spec: review

Multi-lens panel review, an append-only measurement ledger, and the discipline that keeps
both honest. Reference tools: `reference/tools/review_stamp.py` (the configuration stamper)
and `reference/tools/review_rates.py` (the rate rollup); the CI legs that enforce the
ledger are in `reference/ci/docs-gate.yml`.

## The invariants (MUST)

1. **Fresh-context lenses, never shown the writer's reasoning.** Fan out reviewer agents in
   parallel, each given only the diff, the task, and its lens question. The writer
   self-attests and always misses; a lens must not share the writer's blind spots.
2. **Every finding is verified before it drives anything** — in BOTH directions. A finding
   needs a reproduction, not a plausible reading; and a real finding's SEVERITY is measured
   too (one reviewer's real regression claim was inflated sixfold; unmeasured, it would
   have mis-ranked the whole fix list).
3. **Findings land as failing tests, guards, or same-pass fixes — never report-only.** A
   review whose output is prose grows a queue.
4. **The capped loop** (also in `spec/operating-model.md`): round 1 buckets everything
   must-fix / later / ignore; round 2 must-fix only; max 2 rounds; residue is recorded,
   not re-litigated. External reviewers do not buy extra rounds.
5. **Dispatch from the structured findings ledger, never from a narrative summary** — the
   narrative is how confirmed findings go undispatched.
6. **Every review run writes one ledger line, and its configuration is STAMPED, never
   self-reported.** A session's own account of which model it ran on is exactly the claim
   that cannot be checked later.
7. **Lens rosters change on measurement, not appetite.** Assignments move two ways only —
   a bake-off demotes, a measured regression promotes — and a bake-off is pre-registered
   (metric, single variable, sample floor, and the conclusion each outcome dictates)
   BEFORE the data exists, so the result cannot be rationalised afterwards.

## The lens roster (the reference's seven, as a starting shape)

Diversity of QUESTION-KINDS is the point — one lens missed the same measurement trap three
times; the countermeasure is different kinds of attention, not more of one kind. The
reference panel: Numbers (every figure traces; denominators named) · Silence (what fails
without going red; every guard has a positive control; freshness derived from the artifact,
never the job that wrote it) · Determinism & provenance · Publishing & firewall · Cyber
(secrets, authn/authz, exposure, injection, dependency risk — a lens on the same panel,
never a separate process) · Docs-drift (diff vs the role's docs contract; a gap is
must-fix at the severity of a failing test) · **Completeness**.

The Completeness lens owns: *every set is a claim that the list is finished — name the
value NOT in it and say what happens to it.* "Treated as fine" = fail-open enumeration =
must-fix, repaired by INVERSION (enumerate terminal/known-safe, refuse the rest), never by
adding the missing value. Also: is the upstream vocabulary documented as EXTENSIBLE (then
no exhaustive list can be correct)? do paired rules get equal strictness? can the
docstring's promised fallback be REACHED? Born from four-of-five external findings being
one class the panel had no owner for — and recorded as UNPROVEN at birth: the escape
ledger is its judge, and if the next class-level defect is again found by an outsider
first, the lens did not work and the answer is not to reword it.

## The ledger (JSONL, append-only — the schema is the contract)

One JSON object per line; unknown `type` is a hard error, never a skipped row (a typo must
not quietly leave a review out of the denominator).

**`review`** — one panel run on one PR:

```json
{"type":"review","pr":20,"date":"2026-08-30","config":{...},"findings":{"must_fix":14,"later":null,"ignore":null},"verified_surviving":14}
```

- `config` comes from the stamper, which reads role-file `model:` frontmatter and the
  policy page's assignments table and FAILS CLOSED on any disagreement — a configuration
  that cannot be stated unambiguously must not be recorded as if it could.
- `must_fix` minus `verified_surviving` is the panel's own false-positive load — the number
  that keeps "more findings" from reading as "better review".
- **`null` vs `0` is a distinction with teeth:** `null` means *not recorded* and is legal
  only in a back-filled line; `0` means *counted, and it was zero*. Conflating them lets a
  gap in the record read as a clean run. Rate rollups must tally unrecorded counts in
  their own column, never add them in as zeros.
- Findings carry their SOURCE (panel / external bot / CI) so an external reviewer's
  catches are not attributed to the panel's configuration, and so a reviewer bake-off
  (what only each source catches; full-overlap lenses are retirement candidates) is
  possible at all.

**`escape`** — a defect that got through a review, written when its fix lands:

```json
{"type":"escape","fix_pr":31,"introducing_commit":"abc1234","reviewed_and_missed":true,"attributed_config":{...}}
```

- `introducing_commit` is established (`git log -S` / bisect), not guessed.
- `reviewed_and_missed: false` lines are kept deliberately — they show an escape rate that
  rose because more work skipped review, not because a tier got worse.
- **`fix_pr: null` is the PENDING marker:** an escape may be recorded the moment it is
  confirmed, before its fix exists; the line is completed when the fix lands. A `null`
  here means "known, unfixed" — it is never a zero and never dropped from counts.

**CI teeth:** a PR touching declared code paths must ADD a ledger line whose `pr` is its
own number, or carry a PR-body line `review-exempt: <reason>` — read only OUTSIDE HTML
comments, so the template's commented placeholder never counts.

## Review-exempt discipline

**Judgment-shaped exemptions are OK; fence-shaped ones are a bias.** The exemption exists
for changes no panel read — a dependency bump, a lockfile, a rename sweep — where the
reason is a judgment about the change's nature. It is NOT for changes that happen to sit
on paths someone considers low-risk: an exemption keyed to a path class quietly converts
"we decided not to review this one" into "this kind of thing is never reviewed", which is
a fence nobody drew on purpose. An exemption on a change a panel actually reviewed is
worse still: it saves no work and deletes the evidence the review produced. Reasons are
printed in the check output either way, so an exemption habit is visible rather than
silent.

## External automated reviewers

Input, never an author. The origin's measured hit rate for its external reviewer: four
real defects of five, and in THREE of the four the correct fix was NOT the one the finding
implied (a whitelist missing one value is fixed by inversion, not by adding the value).
Good detection, poor repair: reproduce before fixing, write a test that fails against the
pre-fix code, and keep autofix OFF. External findings join the PR's own review package —
deduped against panel findings (two reviewers naming one defect is ONE finding; counting
it twice inflates both catch rates with the same catch), bucketed by the lead on the same
evidence standard, inside the same two-round cap. Fix findings IN the PR that raised
them: separate follow-up PRs pay for every finding twice and read to the reviewer as
nothing ever being fixed.

## What an implementing agent must achieve on another harness

- Parallel fresh-context review with per-lens prompts — any harness that can run isolated
  agent calls can do this; what matters is the isolation (no writer reasoning in context)
  and the roster of question-kinds.
- The ledger is plain JSONL in the repo: fully portable. Keep the stamper's property —
  configuration read from files, refused on ambiguity — even if your "configuration" is
  just a model name per lens.
- The CI legs (ledger-presence gate, config-consistency check) are ordinary CI: portable
  to any provider. Keep them fail-closed and keep the exemption outside HTML comments.
- The two-round cap and the verification standard are doctrine: prose in the constitution,
  audited after the fact. Carry them even unenforced.

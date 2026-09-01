<!-- harness-kit 2026.09 — PR template pattern. Install as
     .github/pull_request_template.md with placeholders filled. The commented-out
     exemption placeholders are load-bearing: the CI gates honor an exemption line only
     OUTSIDE an HTML comment, so the template as shipped exempts nothing. -->

# Summary

<!-- Plain-English: what changed and why, written for the operator (a non-coder).
     One paragraph. Lead with the consequence, not the machinery. -->

## Role & fence

- Dispatched role: <!-- one of the roles in .claude/agents/, or "master-dispatched {{shared-kernel}} job" -->
- [ ] Every changed file is inside the role's owned paths (fence questions were
      stop-and-asked, not improvised)

## Docs contract (required — an unchecked box that should be checked is a defect)

- [ ] **Generated docs regenerated** — {{registry/manifest}} changed → {{the regeneration
      command}} ran and {{the generated doc}} moved with it
- [ ] **{{Operator handbook}} current** — any new/changed command, flag, job, schedule,
      or state file is reflected there
- [ ] **`docs/*.md` current** — any behavior described in a docs page still reads true
- [ ] {{The project's own required statements — e.g. an extension story, a surfacing
      check}}

<!-- If a docs box is legitimately not applicable AND the mechanical docs gate should not
     block, UNCOMMENT the line below and give a real reason. The gate only honors the
     line OUTSIDE an HTML comment — this placeholder, left as-is, exempts nothing: -->
<!-- docs-exempt: <reason> -->

## Verification

<!-- The interpreter is part of the check, not a detail of it: a bare `python` that
     resolves to the wrong interpreter has produced both false greens and false reds.
     Name the project's exact suite command with the interpreter pinned. -->

- [ ] Full suite green: `{{.venv/Scripts/python -m pytest  (or .venv/bin/python)}}`
      (paste the summary line)
- [ ] Guards/checks added here have a positive control (a test that watches them fire)

## Review

- [ ] Review panel ran on the diff (all lenses); must-fixes applied; later/ignore residue
      recorded in the nits note
- [ ] **Review recorded** — panel ran → a `reviews/ledger.jsonl` line for THIS PR number,
      its config from `python scripts/review_stamp.py`; or no panel ran → the
      `review-exempt:` line below is uncommented with a real reason

<!-- The review-ledger gate requires a ledger line from any PR touching the declared code
     paths. If NO panel ran because the change is mechanical or config-only, UNCOMMENT the
     line below and say so. The exemption is judgment-shaped ("no panel read this"), never
     fence-shaped ("this path class never gets reviewed") — see the kit's spec/review.md.
     Like docs-exempt, it only counts OUTSIDE an HTML comment: -->
<!-- review-exempt: <reason> -->

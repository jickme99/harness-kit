<!-- harness-kit 2026.09 — START-HERE. An agent that has never seen this project
     reads this file, then HARNESS.md. Fill the placeholders. Do not paste origin
     paths, env names, or a next-project's domain into this stub. -->

# Start here

**The constitution is `HARNESS.md`.** This file answers four succession questions so a
cold start does not depend on chat memory.

## The four answers

1. **Last decision** — newest dated heading in `wiki/decisions.md`. Session detail is
   `wiki/HANDOFF.md`.
2. **Next task** — `wiki/HANDOFF.md` (Next) and `wiki/status.md` (Pending / blocking).
3. **Kit version** — `kit-manifest.json` field `kit_version`. Poll with
   `python scripts/kit_poll.py --project . --kit {{path to a harness-kit clone}}`.
   Offer local kit-file customizations back with
   `python scripts/kit_harvest.py --project . --kit {{path to a harness-kit clone}}`.
   Never self-apply: propose a project PR (poll) or a kit PR (harvest).
4. **What is not in this repo** — `wiki/HANDOFF.md` (Not in this repo). If this is the
   body half of a two-repo shape, the brain is a sibling checkout, not this tree.

If any answer is empty, stand-up is incomplete: fill `wiki/HANDOFF.md` before real work.
If `wiki/operating-model.md` still carries `{{KIND_PLACEHOLDER}}` under Kinds of work,
filling that page is the first task — before product edits. The STANDUP gate does not
check this (empty tree). Do not ask the owner to name jobs.

## Session start

Read in order: this file → `HARNESS.md` → `wiki/HANDOFF.md` → `wiki/status.md` →
`wiki/operating-model.md` → `wiki/feedback.md`.

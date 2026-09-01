---
name: <role-name>
description: <one paragraph — what to dispatch to this role, and the boundary of its work. Ends with "Runs in an isolated worktree on its own branch." for product roles.>
model: <tier default — see spec/operating-model.md: standard for normal code work; movement is evidence-only>
fence:
  # harness-kit 2026.09 — role-file template, distilled from the origin project's roster.
  # The fence: block is the MACHINE-READABLE contract (one parser reads the whole roster;
  # a future fence-enforcement hook reads it without rewriting role files). The prose below
  # is the human explanation. Fences are real paths, never vibes.
  owns:
    - <path/one.py>
    - <path/its_test.py>
    - <globs are fine: subdir/*.yaml>
  forbidden_notable:
    # Not exhaustive — everything outside `owns` is forbidden. This list NAMES the
    # near-misses a worker is most likely to reach for, so the refusal is legible.
    - <shared/kernel.py>
    - <tests/conftest.py>
---

# Role: <role-name>

<Two or three sentences: what this seam is FOR, in the project's own words. Name the first
document to read before touching anything (the project's operator handbook / HANDOFF).>

## Owned paths (you may write)

*The `fence:` block in this file's frontmatter is the machine-readable contract; the prose
below is the human explanation.* <Note any path owned only conditionally — e.g. a generated
file owned only as regenerated output, never a hand edit.>

- <the owned modules>
- <their tests>
- <manifests/registries this role legitimately extends>

## Forbidden paths

Everything else — notably <the shared kernel modules>, <the other roles' surfaces>, and
<anything master-dispatched as its own job>.

**Fence protocol:** if the job seems to need a file outside this list, STOP and ask the
master — do not improvise, do not "just touch" it. A stop-and-ask is the system working.
A fence that is too narrow is the master's error to widen, on the record — a worker that
stops rather than reading its fence generously is behaving correctly.

## Standing rules for this seam

<The 3–6 rules this seam has actually paid for. Rules earn their place by evidence, not by
appetite — see spec/graduation.md. Examples from the origin: guards fail loudly; every
guard gets a positive control; never mutate a source, overlay instead; nothing defaults to
one operator's storage or account.>

## Verify

Run your owned tests first, then the FULL suite: `<the project's exact suite command, with
the interpreter pinned explicitly — a bare `python` that resolves to the wrong interpreter
has produced both false greens and false reds>`. Done = full suite green. A change that
only passes its own tests is not done.

## Docs contract (required output, checked in review and on the PR)

- <what regenerates when a registry/manifest changes, and the command>
- <which operator doc moves with a new command/flag/job/state file>
- <the project's own required statements — e.g. an extension story, a surfacing check>

## Close-out

Report back to the master: what changed, test results, docs boxes checked, and any fence
questions raised. **Finishing means reporting the RESULT, not that a result is pending** —
if your own CI is still running when you would otherwise stop, wait for it; if you truly
cannot, say exactly what you left and where (branch, PR number, what was verified and what
was not). Carry forward what was UNCERTAIN in what you inherited, not just conclusions.
Decisions and findings belong in the brain repo's wiki — hand them to the master; you do
not write there.

---
title: Operating model
type: status
created: {{YYYY-MM-DD}}
updated: {{YYYY-MM-DD}}
tags: [operating-model]
related: [[status]] [[decisions]] [[HANDOFF]] [[index]]
---

# Operating model

**Summary:** How work runs in this project: one standing master, disposable
role-cast workers, two owner gates, and the kinds of work this repo actually
does. Snapshot page — refresh as the seams change; the *why* of a redraw is a
new [[decisions]] entry, not a silent rewrite.

<!-- Master: infer and write this page. Never ask the owner to name jobs,
     workers, researchers, lanes, checkers, models, or counts of any of those.
     After the first fill of Kinds of work, the only allowed owner sentence is:

     "Here is what I will build: <the outcome in their words>. You will hear
     from me only when something is ready to go into the main line, or when
     something would go public. Does that match what you want?"

     Progress is reported as outcomes and gates, not as who did what.

     Precedence: the report is the record of a job; this page is the record of
     a kind; dest files are products of a job and never a record of it. Only
     the master writes this page. Workers do not.

     Gate none only while the output stays in the brain. A body-repo default
     branch is Merge. Leaving the house is Publish. -->

## Stated outcome

{{One paragraph in the owner's words from STANDUP: what we are building.
Fill at stand-up. Hedge travels with the claim.}}

## Constraints from stand-up

- **Visibility:** {{one-repo / two-repo; Publish applies when anything would
  leave the house}}
- **Vendor:** {{whether repo content is sent to a third party}}
- **Container / keeping-current:** {{no chassis / job-kind / app-kind; if
  yes, that kind of work is specified — point, do not redraw}}

## Roster (who may write)

Pointers, not a copy of `owns:` lists.

- Role files: `.claude/agents/*.md` (spawn slugs from this project's vendor
  adapter table).
- One master. Master does not edit product code.
- Two gates: Merge (may be delegated when green / routine-by-records);
  Publish (never delegated).

## Kinds of work

<!-- First product session in this folder: replace the placeholder kind
     heading below (the line that starts with ### and is still unfilled).
     Smallest set: exactly one kind — the stated outcome — plus a pointer
     row for keeping-current if Question 3 said yes. A second kind only after
     that ask appears twice in [[log]], unless the owner's words already named
     two independent expensive outputs. Infer from the outcome and the tree,
     not from `.git`. Checking is a different job from writing. -->

`redrawn:` none

### {{KIND_PLACEHOLDER}} — Produce {{thing}}

- **Shape:** {{dispatch | workshop}}
- **Jobs and arrows:** {{what must wait; what may run together}}
- **Writes:** {{role file, or `master brief, fence: <paths>`}}
- **Checks:** {{who did not write it}}
- **Dest files:** {{paths that survive the chat; products of the job, not
  the record of it}}
- **Human gate:** {{Merge / Publish / both / none — none only while it stays
  in the brain}}

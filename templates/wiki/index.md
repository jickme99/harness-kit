---
title: {{Project}} Wiki Index
type: index
created: {{YYYY-MM-DD}}
updated: {{YYYY-MM-DD}}
tags: [meta, index]
---

# {{Project}} Wiki Index

**Summary:** Catalog of every page in this wiki. Update whenever a page is added, renamed,
or removed — that update is one of the auto-write triggers, not a favor.

## Conventions (harness-kit 2026.09 — keep this block)

- Every page carries YAML frontmatter: `title`, `type`, `created`, `updated`, optional
  `tags`, `related`.
- Cross-references are `[[Page Title]]`.
- `decisions.md` and `log.md` are **append-only**: supersede via a new dated entry, never
  rewrite an old one.
- Snapshot pages (this one, [[status]]) keep `updated:` honest — the probe pack measures
  both the frontmatter's claim and the body's newest date against [[log]].

## Pages

- [[index]] — this page
- [[status]] — where things stand
- [[decisions]] — dated decisions with rationale (append-only)
- [[log]] — the work log (append-only)
- [[feedback]] — owner preferences and lessons, with disposition markers

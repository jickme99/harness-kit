---
title: Decisions
type: decisions
created: {{YYYY-MM-DD}}
updated: {{YYYY-MM-DD}}
tags: [decisions]
related: [[log]] [[status]]
---

# Decisions

**Summary:** Every decision, dated, with rationale — the record that stops re-litigation.
**APPEND-ONLY:** a decision is superseded by a NEW dated entry that names what it
supersedes, never by rewriting the old one. Entries land automatically as decisions are
made (auto-write trigger), each as:

`## [YYYY-MM-DD] <one-line decision>` + rationale bullets, naming who decided (owner /
master-recommended-owner-approved / delegated).

When an entry passes along a prior conclusion, it passes along **what was uncertain about
it** too — a hedge is load-bearing, and a reader who resolves it without new evidence has
manufactured a finding.

---

## [{{YYYY-MM-DD}}] Stand-up: shape and vendor answers (the kit's two questions)

- **Visibility:** {{"never public → one-repo shape" / "may be public → two-repo shape;
  the brain is {{repo}}, the body is {{repo}}"}}.
- **Vendor question:** {{which adapters send repo content to third parties, and the
  recorded approval or the owner's call}}.
- Stamped from harness-kit {{version}}; `kit-manifest.json` is the stamp. Poll later
  against the kit's `CHANGELOG.md` (`spec/versioning.md`); never self-apply.

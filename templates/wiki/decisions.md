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

## [{{YYYY-MM-DD}}] Stand-up: where things stand today

- **Visibility (today):** {{"not shared → one-repo" / "public or shared now →
  two-repo; the brain is {{repo}}, the body is {{repo}}"}}. A later published
  page is not two-repo. Re-open when: {{sentence}}.
- **Vendor (today):** {{no tool sends the repo out / which tool, and the
  recorded approval or the owner's call}}. Later is not a yes.
- **Where it runs (today):** {{this machine / image definition already in the
  tree, app or job}}. Chassis copied only in the second case. Re-open when:
  {{sentence}}.
- **Product data:** {{no / what the product sends out}}. Not the vendor
  question. Re-open when a spec adds an outside call.
- Stamped from harness-kit {{version}}; `kit-manifest.json` is the stamp. Poll later
  against the kit's `CHANGELOG.md` (`spec/versioning.md`); never self-apply.

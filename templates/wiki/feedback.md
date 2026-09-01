---
title: Feedback & Lessons
type: feedback
created: {{YYYY-MM-DD}}
updated: {{YYYY-MM-DD}}
tags: [feedback, preferences, lessons]
related: [[decisions]]
---

# Feedback & Lessons

**Summary:** Owner preferences that should change future behavior, and lessons learned.
Read early, every session — this page exists to prevent repeat mistakes.

**Disposition rule (harness-kit doctrine — "lessons land as diffs, not paragraphs"):**
every entry dated **{{the epoch — set it to stand-up day}}** or later ends with a
disposition marker in fixed syntax on its own line —
`→ encoded: <path>` (the role file, protocol page, check, hook, or brief template this
lesson changed) or `→ noted-only: <reason>`. A lesson's terminal state is a diff; the
prose here is the intermediate form. `scripts/harness_probes.py --probe
lesson_dispositions` flags unmarked entries as open loops at every close-out until
closed. **The boundary:** capture is automatic, proposal is automatic, ACTIVATION passes
a gate — lessons touching strategy, gates, or the firewall never self-apply.

---

## [{{YYYY-MM-DD}}] {{First owner preference or lesson}}

- {{the pattern, framed so a future session acts differently}}
→ encoded: {{path}} <!-- or: → noted-only: {{reason}} -->

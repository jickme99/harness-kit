---
title: Log
type: log
created: {{YYYY-MM-DD}}
updated: {{YYYY-MM-DD}}
tags: [log]
related: [[decisions]] [[status]]
---

# Log

**Summary:** The append-only work log — the record snapshot pages are measured against.
One entry per logical chunk of work, written as the work lands (auto-write trigger), in
the fixed shape the staleness probe parses:

`## [YYYY-MM-DD] <type> | <one-line summary>` + bullets.

Types: `setup`, `decision`, `ingest`, `milestone`, `iteration`, `lint` {{— extend for the
project, but keep the shape}}.

---

## [{{YYYY-MM-DD}}] setup | Project stood up from harness-kit {{version}}

- Shape and vendor answers recorded in [[decisions]].
- STANDUP gate: {{"passed — tests green, wiring probe clean, live negative test refused"
  / what failed and what was recorded about it}}.

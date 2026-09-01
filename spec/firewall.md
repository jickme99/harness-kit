# Spec: the publication firewall (the PATTERN)

A CI tripwire that scans what ENTERS a repository with a public trajectory, so "assume it
goes public someday" is physics rather than discipline. **This kit ships the pattern only.**
No scanner, no denylist, no origin-project terms — a committed list of the words you must
never publish is a published list of them, and that logic applies to this kit too. The two
workflow files in `reference/ci/` show the wiring; the scanner itself is project-authored
against this spec.

## The two-layer design (MUST)

1. **A committed generic layer** — credential SHAPES: key headers, GUID shapes, token
   prefixes. Safe to publish because it names shapes, not secrets. Lives in the repo
   (e.g. `.github/firewall-patterns.yml`) where it is reviewable and testable.
2. **A secret-delivered denylist layer** — the SENSITIVE TERMS: employer names, tenant
   domains, persona-linking strings. Lives ONLY in the private brain repo (one entry per
   line, `id<TAB>regex`, `#` comments), and reaches CI as an Actions secret. The split is
   the whole design: the one list that would be a leak if committed is never committed.
   - The **id is printed; the regex is not.** Name the CLASS (`employer-name`), never the
     term — a blocked PR's annotation is a public-ish artifact.
   - Word-boundary short terms, or a name that substrings an ordinary word blocks every PR
     using the word — and a firewall that cries wolf gets its patterns deleted.
   - **The file and the secret can drift silently** (nothing connects them but a person
     re-running one sync command), so the sync is recorded: a committed hash of what was
     last pushed, and a probe (`firewall_denylist_sync`) with three distinct answers —
     `match` / `mismatch` (the secret is STALE) / `never_synced`. A mismatch is an
     owner-level finding: only the owner has the admin to re-sync.

## Triggers (MUST)

- **Every pull request** — added lines only (`-U0`, three-dot against the merge base;
  a term already on main is a remediation job, not a gate failure) and touched PATHS
  (a matching path is reported without printing it — the path IS the match).
  `--no-renames` is load-bearing: with rename detection on, a byte-identical rename INTO a
  sensitive filename emits no `+++` header and no hunk, and scans clean.
- **Every push to the default branch** — the event the PR gates cannot see. On this
  trigger the gate can only ALARM (the push has landed), but a leak detected in a minute
  is a rotate-and-purge; a leak nobody detects is a publication. Every unusable range
  (all-zeros before-commit, unreachable endpoints, no merge base) is a LOUD refusal,
  never a silent empty scan.

## Fail-closed (MUST)

A missing or empty denylist secret FAILS the gate, naming the sync runbook — a firewall
running on half its patterns does not fail, it passes. An unparseable patterns file is
exit-2, never a traceback and never a pass. A hit blocks naming the pattern id, file and
line NUMBER — never echoing the matched text.

## Exceptions: reviewed, never self-served (MUST)

The gate takes NO waiver the blocked change can write for itself — an escape hatch a
blocked PR can add to its own body is not a firewall. Two reviewed paths only:

1. **Narrow the pattern** — the default remedy for a false positive; for a denylist term
   that means editing the private file AND re-syncing the secret.
2. **Fingerprint one exact string** — a committed allowlist of SHA-256 fingerprints of the
   matched span. Content-addressed: one exact string, forever, unusable for smuggling
   anything else, and a permanent audit ledger of every exception granted. Fail-closed on
   the allowlist's own integrity (a malformed hash blocks). For short guessable denylist
   terms, prefer path 1 — a dictionary of candidate names is cheap to hash.

## Known limits (state them in your implementation too)

Endpoint-to-endpoint diffs police what the TREE gains, not git HISTORY: content added and
removed within one range is invisible, and the objects survive either way until the flip.
The gate raises the floor against ACCIDENT; a deliberate smuggler is the review panel's and
the human Merge gate's problem. Solo-operator caveat: with one human, "reviewed path" is
review by the same machinery that produces everything — what the mechanism still buys solo
is content-addressing and the friction asymmetry (an exception is a deliberate SEPARATE
change, never a line typed into the blocked PR in frustration). The day a second human
exists, firewall-file changes get owner-only approval mechanically (CODEOWNERS).

**A second surface, easy to miss:** investigative work over LOCAL state (transcript greps,
control-plane queries, log sweeps) is outside every diff-scanning gate and more likely to
contain out-of-scope identifiers than the repo is. Scope forensic reads before running
them; sensitive strings seen that way go to the owner, never into any repo — except as a
new denylist PATTERN, which is that file's entire purpose.

## What an implementing agent must achieve

Author the scanner fresh in your project (this spec + the workflow patterns are the head
start), with tests carrying positive controls: a seeded hit MUST block, the matched text
MUST appear nowhere in the output, a missing secret MUST fail, and the rename/empty-file/
binary-add diff shapes MUST be caught (each of those was a real bypass — a file named for
a sensitive term once scanned clean on the day the gate armed). Then seed the denylist
from your own brain repo's hard constraints, sync the secret, and record the hash.

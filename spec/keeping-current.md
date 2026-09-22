# Spec: keeping current

Software that is not deliberately kept current goes stale in four places at once: the
base image, the packages the image installs, the libraries the app named, and the
actions that build it. Each layer has its own fix path; none of them fixes the others.
This page is the contract. The GitHub + Azure Container Apps method is
`adapters/github-azure.md`. The tested rule modules are `reference/keeping-current/`.

Stand-up does not install the chassis. Copy it later, when an image definition
is already in the project and the work is to keep that image current
(`STANDUP.md`). A plan to host later is not that moment. A container file with
no such work is not that moment. A wiki, a library, or a brain repo honors the
invariants as doctrine and does not receive `deploy.yml`. A job-only stamp copies
the chassis except `deploy.yml` (no ingress to split; the job refresh workflow stays
per-project). This clone is the factory; the daily job lives in the stamped project.

## The invariants (MUST)

1. **Two lanes, decided by what the change IS.** A change is *routine* when a machine
   can prove it safe from live records: the same code rebuilt on a patched base with a
   clean scan, or a patch/minor library update that touched only the manifest and the
   hashed lock, passed the required check, and waited out its cooling-off. Everything
   else is *judgement* and waits for a person: features, major versions, the base-image
   line, workflows, identities, permissions, sign-in, trust rules, ownership. The
   owner's click is kept where it adds judgement, not latency.
2. **Routine Merge is still the Merge gate.** It is not a third gate and not a skipped
   gate. When — and only when — the project has installed this chassis and the
   preconditions in §Mechanics hold, a machine may merge and deploy a routine change
   because the system of record attributes every commit since the deployed one to the
   dependency bot and marks them verified. One human commit in the range and the deploy
   is judgement-lane, whoever asked. Projects that have not installed the chassis keep
   `spec/versioning.md` as written: lane 2 is a monthly bundle through the (possibly
   delegated) Merge gate; nothing auto-merges. **Publish is never routine.**
3. **Every deploy is a canary.** The new version starts beside the old one with no
   traffic, proves itself with its own self-test inside the new version (one real call
   per dependency, and the version it runs), takes traffic only on a pass, is checked
   through the public name afterwards, and rolls back by itself if anything fails; the
   old version is kept as a restore point. A workload that serves no traffic (a
   scheduled job) replaces the traffic split with one real execution of the candidate;
   the image switches only if that execution succeeded.
4. **Three outcomes, never two.** Every check answers PASS, FAIL, or COULD NOT RUN. A
   check that could not run is neither green nor red, and it never moves traffic.
   Silence is never a pass; "the tool exited 0" is never a pass — the thing checked is
   read back.
5. **Trust records, not text.** An unattended lane trusts only what a system of record
   verifies: who authored a commit, whether it is signed, whether the required check
   passed, what image the app is actually running. It never trusts the caller's claim,
   a file anyone can edit, or the local copy of history. It re-checks the claim inside
   the job.
6. **Each automated identity does exactly its job.** The deploy lane can pull an image
   and update one app. The rebuild job can build, scan, and promote in the registry,
   not deploy. New rights are added when a live run refuses for want of one, not in
   advance "just in case".
7. **Pin every installed byte.** The image installs from a lock that names every
   package by version and fingerprint. A required check must exercise the artifact the
   change alters: a lock change must build the image.
8. **Refuse rather than guess, and hand off rather than drop.** Ambiguity, a truncated
   read, an unreadable answer, a tag that names no commit: each is a refusal with the
   reason in words. The kill switch fails to OFF, and OFF hands the request to a person
   instead of losing it.
9. **A record instead of a click.** A weekly note, assigned to the owner, lists what
   shipped itself, what waited for a click, what was held, what the daily job decided,
   any open red issue, and when the next drill is due. Red issues are the only
   interruption; an open red issue closes the routine lane until a person closes it
   with the cause. Closure is earned by the check that opened the finding, never by a
   quiet day.
10. **Drill before trusting, and keep drilling.** A flag drill (the self-test told to
    fail) proves the wiring reacts; a real-dependency drill on a non-production
    environment proves the canary survives a container that is unhealthy for a real
    reason. Both before the lane is trusted; the flag drill again each quarter, its
    due date printed in the note.
11. **The first live run is `dry`.** Every mechanism computes and prints everything and
    changes nothing until a dry run has been read. Records name the run that proved
    each claim. A scanner finding is a file path before it is a version.

## Who clicks

| Change | Lane | What proves it is safe |
|---|---|---|
| A rebuild of the deployed code on a patched base, scan clean | routine | same code and library versions by construction; the scan; the canary; rollback |
| A patch or minor library update touching only the manifest and the lock | routine | cooling-off; tests green *and the image built*; the canary |
| A feature; a major version; the base-image line; a build tool or action | judgement | tested by a person; then the gate |
| Workflows, identities, permissions, sign-in, trust rules, ownership | judgement | reviewed; then the gate |
| A rollback after a failed routine deploy | automatic | the canary's own failure; an issue to the owner the same minute |

## Why (the failures that taught these)

- Left to a person, four stale layers become a stream of small approvals nobody wants
  to give, so they stop being given, until an incident makes it urgent.
- A scanner's "package X" was pip's vendored copy, not a pin the app could move
  (lesson 183). Resolve to a file path first.
- A success-path close would have closed a RED issue on a quiet weekday with the
  package still in the image (lesson 184). Closure is earned by the check that opened
  it.
- A commit message that said "closed #3" closed issue 3 on push (lesson 185). Write
  "issue 3" unless the close is meant.
- The first automatic dependency merge was green on unit tests and unbuildable: one
  pin bumped, the package that pins it exactly left behind (lesson 189). The required
  check must build the image on a lock change.
- `az containerapp exec` returns 0 whatever the remote command did. The transcript is
  the evidence. Three outcomes, never two.
- A kill switch that drops the request loses a promotion. Fail to OFF and hand off.
- A copied workflow that looked up its own runs by a literal file name refused two
  deploys before the canary. Derive the name from the workflow reference; strip the
  `@ref` first.
- A template guard that matched its own error message would have stopped every
  filled-in copy at its first step.

The numbered stories live with the apps that earned them. This page keeps the rule.

## Mechanics (how the reference implements it)

**Preconditions, without which no automatic merge is allowed** — the whole suite as the
required check named `tests`; on a pull request touching a Dockerfile, a lock, or the
manifest it also builds the image; a hashed lock the image installs from with
`--require-hashes`; a canary (or one real job execution) on every production deploy;
a kill switch that fails to OFF.

**The GitHub + Azure method** (`adapters/github-azure.md`, files under
`reference/keeping-current/`):

| Function | Reference |
|---|---|
| Tests as the required check | `templates/tests.yml` |
| Deploy, both lanes, kill switch | `templates/deploy.yml` |
| Canary + three-outcome verdict | `infra/canary.sh`, `infra/canary_rules.py`, `app/selftest.py` |
| Daily freshness | `templates/freshness.yml`, `infra/freshness/` |
| Registry retention | `infra/registry-retention.sh`, `infra/registry_retention_plan.py` |
| Narrowed dependency bot | `templates/dependabot.yml`, `templates/dependabot-automerge.yml`, `templates/CODEOWNERS` |
| Weekly note | `templates/weekly-note.yml`, `infra/weekly_note.py` |
| Job-kind refresh (no traffic to split) | `infra/refresh_rules.py` (workflow still per-project; not a filled-in template yet) |
| Proof | `tests/test_freshness_*.py` and siblings — RED-first, fictional data, stdlib only |

Placeholders are `__PLACEHOLDER__` (and `__OWNER_GITHUB_LOGIN__`). Scripts and
workflows refuse to run while one remains. The kit ships no registry, subscription,
or workload name.

**The version-steward** (`spec/versioning.md`) is the named reader of the weekly note
and the red issues once the chassis is installed. It does not bump pins by hand on
that project. The harness-auditor still checks that the steward ran and that no lane
is backing up.

**The owner's explainer** is a deliverable of adoption, the same idea as
`WHAT-YOU-GET.md`: a plain-language page that says what runs by itself, what waits
for a click, and what to do when something is red. The kit does not ship a filled
example from another app.

## The swap table

| Piece | This method | Elsewhere | What changes |
|---|---|---|---|
| CI | GitHub Actions | GitLab CI, Azure Pipelines | The YAML skeleton and `gh` calls. The rule modules do not. |
| Registry | ACR | ECR, GAR, GHCR | List manifests, show a tag's digest, import/retag by digest, delete by digest. |
| Scanner of record | Defender for Cloud | ECR scanning, Wiz, Prisma | One parser that yields the same `Finding` shape. |
| Rebuild scanner | Trivy | Grype, Snyk | `inventory` reads one JSON shape. |
| Dependency bot | Dependabot | Renovate; a scheduled audit job that opens a PR | The manifest file. The range rule still reads the forge's compare answer. |
| The gate | GitHub environment approval | Any identity-bound manual approval | Must record who shipped what. |
| The issue | GitHub issue, label + assignee | Any ticket with a fixed owner | The two issue steps. Closure earned by a clean scan does not change. |

The first non-GitHub or non-Azure app writes the adapter. The tests on the rules are
the bar.

## What an implementing agent must achieve

- Four stale layers, each with a named mechanism; none pretending to fix another.
- Three outcomes on every check that can move traffic or close an issue.
- A routine lane that re-checks live records and refuses a mixed range.
- A kill switch that hands off rather than drops.
- Dry mode, then named live runs, before the lane is trusted.
- Drills with a printed due date.
- A weekly record the owner actually sees.
- Portable tests on the rules (stdlib + pytest, fictional data) that fail when a
  rule is reverted.

## Open in this kit

- A second adapter for a non-Azure host or a non-GitHub forge is not written.
- The job-kind refresh workflow is not yet a placeholder template; the rules are.
- A weekly note that spans every repository of an owner is not built.
- The note's home outside the issue tracker is not built.

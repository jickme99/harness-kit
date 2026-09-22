# Adapter: GitHub Actions + Azure Container Apps

**Status: PROVEN 2026-09-08..12** on three production workloads (a web app, a
second container app, a Container Apps job). This is one method for `spec/keeping-current.md`,
not a second kit. Claude / Cursor / Codex adapters still decide how the *agent*
is wired. This page is how a stamped project that **ships a container** stays
current.

Install when the work is to keep an image that already exists current
(`STANDUP.md`). Not at stand-up. A plan to host later is not that moment. Fill every `__PLACEHOLDER__` /
`__OWNER_GITHUB_LOGIN__`. First two runs of every job are `dry`. A job-only
stamp skips `deploy.yml` (no ingress to split). Do not copy
`dependabot-automerge.yml` until adoption D.

## Coverage

**IF-AVAILABLE** — only when the project ships a container image or a scheduled
job image. A wiki, a library, or a brain repo skips this page. REQUIRED rows
in `adapters/claude.md` / `cursor.md` / `codex.md` are unchanged.

| Guarantee | Gate | Mechanical (this method) | Standalone-checkable | Doctrine-only |
|---|---|---|---|---|
| Tests as the required check; lock change builds the image | IF-AVAILABLE | **yes** — `templates/tests.yml`, job named `tests` | the workflow | — |
| Hashed lock; no package manager in the runtime image | IF-AVAILABLE | **yes** — Dockerfile recipe in this page; `tests/test_dockerfile_policy.py` | that test (skips in the kit factory; fails after stamp if there is no Dockerfile) | — |
| Canary on every deploy; three outcomes | IF-AVAILABLE | **yes** — `infra/canary.sh` + `infra/canary_rules.py` | the rule tests | health + self-test contracts |
| Routine lane (bot-only verified range; kill switch fails to OFF) | IF-AVAILABLE | **yes** — `templates/deploy.yml` + `infra/freshness/range_rule.py` | the range-rule tests | starts OFF until drills pass |
| Daily freshness; scanned bytes are the shipped bytes | IF-AVAILABLE | **yes** — `templates/freshness.yml` + `infra/freshness/` | the freshness tests | — |
| Weekly note to the owner | IF-AVAILABLE | **yes** — `templates/weekly-note.yml` | `tests/test_weekly_note.py` | the owner actually reads it |
| Publish | REQUIRED (operating model) | no — never this chassis | n/a | **yes** — still a human |

## Copy (when the work keeps an image current)

Arrows are in `STANDUP.md` (the membership map). After copy, fill placeholders,
then stamp so the new dests are fingerprinted.

## Identities and rights

| Identity | Federated to | Rights |
|---|---|---|
| `<repo>-cicd` (gated deploy) | `repo:<org>/<repo>:ref:refs/heads/main` and `…:environment:prod` | build on the registry, pull, update the one app, read its environment |
| `<repo>-routine` | `…:ref:refs/heads/main` only (no environment: no click) | AcrPull; Container Apps Contributor on the one app; Reader on its environment. Cannot build or prune. |
| `<repo>-freshness` | `…:ref:refs/heads/main` | AcrPull, AcrDelete, Container Registry Tasks Contributor, Data Importer/Reader, Reader on the registry; Reader on the app. Cannot deploy. |
| a job's refresh identity | `…:ref:refs/heads/main` | the registry roles above; Container Apps Jobs Contributor on the one job; Reader on its environment |

**Two forms of the OIDC subject.** Newer repositories present `repo:<org>@<id>/<repo>@<id>:ref:refs/heads/main`;
older ones present the classic form. A credential in the wrong form fails with
`AADSTS700213`. Create both forms, or read the presented subject from the first
failed run.

**Secrets and variables:** `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`,
`AZURE_CLIENT_ID` (gated) as secrets; `AZURE_FRESHNESS_CLIENT_ID`,
`AZURE_ROUTINE_CLIENT_ID`, `ROUTINE_LANE`, `FRESHNESS_APPLY` as variables.
`FRESHNESS_APPLY` is exactly `on` before a scheduled freshness run prunes or
promotes; unset is dry. The workflow token needs
`issues: write`, `actions: read`, and for the routine job `actions: write` (the
hand-off). It can never approve a review.

**Repository settings:** branch protection on `main` with required check `tests`,
"require review from code owners", 0 required approvals, conversation resolution;
`prod` environment with the owner as reviewer; labels
`deploy`, `freshness`, `needs-a-look`, `weekly-note`. Turn "allow auto-merge" on
at adoption D, when `dependabot-automerge.yml` is copied.

## Contracts an app must meet

- **Health:** `GET /health` answers `{"status": "ok", "version": <APP_VERSION>, …}`
  with 200. The canary reads it three times over fresh connections after the switch.
- **Self-test:** `python3 -m <module>` (no quotes: it crosses shell → az → container)
  prints a first line `AZURE_CRED_MODE = …`, a line `APP_VERSION = …`, one row per
  probe `name  PASS|FAIL  detail`, and closes with `all N configured service(s)
  reachable` on success; exit 0/1. `APP_SELFTEST_FAIL=1` adds one deliberate
  failure (the drill). One REAL call per configured service; a config read is not
  proof. The shipped `app/selftest.py` is the contract skeleton — add the project's
  probes.
- **Served bytes are opt-in:** an app with a portal names the one static file
  (`CANARY_ASSET_FILE` / `CANARY_ASSET_URL`); an app without one sets the file to
  the empty string.
- **Tags:** a deploy tag is the commit's first eight hex characters; a promoted
  rebuild is `<sha8>-rYYYYMMDD`; every reader strips the suffix before treating it
  as a commit. A job deployed by hand tags the commit it was built from
  (`git tag vNN <commit>`); the refresh refuses to guess.

## Dockerfile recipe (no pip in the runtime image)

After the app's own install, in this order: take the base's security updates at
build time; upgrade the build toolchain; uninstall pip and prove it is gone
(`import pip` fails, no launcher on PATH, no `pip-*.dist-info`). Scanners read
pip's vendored libraries as packages of *your* image, and no dependency of yours
can move them. `tests/test_dockerfile_policy.py` refuses a Dockerfile whose last
`pip install` is not followed by that block.

## Adoption sequence

1. **A.** Tests in GitHub + the required check; the hashed lock; then held
   dependency updates merged one at a time, each proven by a deploy.
2. **B.** The canary: Multiple revision mode with traffic pinned by NAME (never
   "latest"); probes by a template-only ARM patch; the self-test with the drill
   lever. Rehearse on a non-prod environment, then on prod through the owner's
   gate: one drilled failure that rolls back, one ordinary success watched end to
   end.
3. **C.** The routine lane: its identity, the `lane` input, the kill switch.
   Proofs: switch off handing to the gate; an inadmissible tag refused after the
   identity signs in; a same-bytes promotion with no click.
4. **D.** The dependency bot narrowed: cooldown, ownership narrowed by the
   owner's decision, auto-merge for patch/minor on manifest + lock only.
   Copy `templates/dependabot-automerge.yml` now; turn "allow auto-merge" on.
   Proof: the first automatic merge watched open to merged; the first bot-only
   main shipped by the daily job. The workflow no-ops while `ROUTINE_LANE` is
   not `on`.
5. **E.** Other workloads: a job by rebuild → execution → switch; a second app
   by A–C again in its own repository.
6. **F.** The weekly note; the real-dependency drill; the owner's explainer.

`ROUTINE_LANE` starts unset (OFF). Turn it on only after the drills.

## Quirks that cost a run each (already in the templates)

- A step that runs before the checkout has no git tree: every `gh` call there
  names the repository (`-R "$GITHUB_REPOSITORY"`).
- A summary step ending on `[ -f file ] && { … }` goes red when the file is
  absent: end it on `true`.
- A GitHub Actions step runs under `bash -e`: a loop whose exit codes are data
  says `set +e`.
- A copied workflow must not look up its own runs by a literal file name: derive
  it from `GITHUB_WORKFLOW_REF`, stripping the `@ref` BEFORE taking the basename.
- A merge enabled by the workflow token starts no `push` workflow: the deploy of
  a merged update belongs to the daily job.
- A dependency bot bumps one pin at a time; a pin another package fixes exactly
  no longer resolves. Name exact-pinned pairs in the bot config; let the image
  build hold the line.
- `az rest --body @file` from Git Bash on Windows needs the Windows-form path
  (`cygpath -m`).
- The exec door (`az containerapp exec`) wants a terminal on stdin: on a Linux
  runner run it under `script -qec`; its exit code is never the command's —
  parse the transcript.
- The container-app template on read carries fields the stable ARM API refuses
  on write (`imageType`): patch a whitelist.
- A template's placeholder guard must not match its own error message.
- GitHub Actions has no cooldown for the `github-actions` ecosystem; those
  updates are judgement-lane anyway.

## Evidence

Named production runs, 2026-09-08 to 2026-09-12: a drill refused before traffic;
an ordinary canary end to end; the kill switch handing to the gate; an
inadmissible tag refused; a same-bytes promotion with no click; the first
automatic dependency merge and the check that caught the update that could not
build; a job switched to a refreshed image after a real execution; a platform
MCP canary after refused attempts that each fixed a template defect, then its
own daily rebuild and a routine deploy with no click; the first weekly note.
The stories stay with those apps. The rules are this spec.

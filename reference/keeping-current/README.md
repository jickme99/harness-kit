# reference/keeping-current — the keeping-current chassis

Harvested into harness-kit as the reference implementation of
`spec/keeping-current.md`. The GitHub + Azure method is `adapters/github-azure.md`.
Install only when STANDUP Question 3 is yes. This directory is not copied into
the kit's own root: the factory does not run a freshness job against itself.

| Path | Project dest (STANDUP arrow) |
|---|---|
| `infra/` | `infra/` |
| `app/` | `app/` |
| `tests/` | `tests/` |
| `templates/tests.yml` | `.github/workflows/tests.yml` |
| `templates/deploy.yml` | `.github/workflows/deploy.yml` (apps that serve traffic; job-only skips) |
| `templates/freshness.yml` | `.github/workflows/freshness.yml` |
| `templates/dependabot-automerge.yml` | `.github/workflows/dependabot-automerge.yml` (adoption D, not stand-up) |
| `templates/weekly-note.yml` | `.github/workflows/weekly-note.yml` |
| `templates/dependabot.yml` | `.github/dependabot.yml` |
| `templates/CODEOWNERS` | `.github/CODEOWNERS` |

Every `__PLACEHOLDER__` and `__OWNER_GITHUB_LOGIN__` must be filled. The scripts
and workflows refuse to run while one remains.

The job-kind refresh *rules* are `infra/refresh_rules.py`. A filled-in
`image-refresh.yml` is still per-project (live resource names); do not copy one
from another app.

Run the rule tests from this kit:

```sh
python -m pytest tests/ reference/keeping-current/tests/ -q
```

"""The job-kind image refresh — the rules, so tests can reach them.

A Container App JOB serves no traffic, so there is no canary. Instead: rebuild the commit the job's
image was built from, scan it, run ONE real execution of the candidate, and switch the job's image
only if that execution succeeded. The next scheduled execution's own result is read the next morning;
a failure opens an issue naming the rollback (the previous tag). Nothing decides here but text:
no `az`, no `gh`. Spec: spec/keeping-current.md.

House rules: REJECT, NEVER GUESS — an image tag that does not name a git tag is refused, not resolved
by proximity. SMOKE_ARGS is the one real, read-only command the candidate must survive; replace it
per job (the default is a stand-in, not a product CLI).
"""
import dataclasses
import datetime
import re

TAG = re.compile(r"^(?P<base>v\d+)(?:-r(?P<stamp>\d{8}))?$")     # v41, or a promoted rebuild v41-r20260912
SMOKE_ARGS = ("jobs", "status")  # replace with the job's one real, read-only command


def base_tag(image_tag):
    """`v41` and `v41-r20260912` both come from the commit tagged `v41`. Anything else is refused."""
    m = TAG.match(str(image_tag or "").strip())
    if not m:
        raise ValueError(f"REFUSED: the job's image tag {image_tag!r} is not vNN or vNN-rYYYYMMDD; "
                         "tag the commit that built it (git tag vNN <commit>) and deploy with that tag.")
    return m.group("base")


def refresh_tag(image_tag, stamp):
    return f"{base_tag(image_tag)}-r{stamp}"


def candidate_tag(image_tag, stamp):
    return f"{base_tag(image_tag)}-cand-{stamp}"


@dataclasses.dataclass(frozen=True)
class RebuildPlan:
    rebuild: bool
    why: str


def rebuild_plan(*, rebuild_input, weekday, open_issue):
    """`auto` rebuilds on Mondays; `force` always; `skip` never; an open `freshness` issue holds everything —
    a person looks first (the image refresh is the routine lane's, and a red issue closes that lane)."""
    if open_issue:
        return RebuildPlan(False, f"freshness issue #{open_issue} is open — a person closes it first")
    if rebuild_input == "skip":
        return RebuildPlan(False, "rebuild=skip")
    if rebuild_input == "force":
        return RebuildPlan(True, "the run was dispatched with rebuild=force")
    if weekday == 1:
        return RebuildPlan(True, "it is Monday")
    return RebuildPlan(False, "no rebuild today (not Monday)")


def execution_verdict(status):
    """A Container App Job execution's `properties.status` -> SUCCEEDED / FAILED / UNKNOWN. Three states: an execution
    that never reported (Running past the deadline, an unreadable answer) is neither green nor red, and it never switches."""
    s = str(status or "").strip().lower()
    if s == "succeeded":
        return "SUCCEEDED"
    if s in ("failed", "stopped", "degraded"):
        return "FAILED"
    return "UNKNOWN"


def last_scheduled_verdict(executions, *, refreshed_tag):
    """The newest FINISHED execution and what it means for the switch made yesterday.

    `executions` is the job's execution list (name, status, start time); `refreshed_tag` is the tag the job runs now
    when this workflow put it there (a `-r` tag), else "". Returns (verdict, name, sentence)."""
    finished = [e for e in executions if execution_verdict(e.get("status")) != "UNKNOWN" and e.get("start")]
    if not finished:
        return "UNKNOWN", "", "no finished execution to read"
    newest = max(finished, key=lambda e: str(e["start"]))
    v = execution_verdict(newest.get("status"))
    if v == "FAILED":
        what = f"on the refreshed image `{refreshed_tag}`" if refreshed_tag else "on the job's own image"
        return v, newest.get("name", ""), f"the latest execution {newest.get('name', '?')} FAILED {what} — see the issue"
    return v, newest.get("name", ""), f"the latest execution {newest.get('name', '?')} succeeded ({newest.get('start', '')})"


def rollback_command(*, registry, repository, previous_tag, job, resource_group):
    return (f"az containerapp job update -n {job} -g {resource_group} "
            f"--image {registry}/{repository}:{previous_tag}")


def stamp(now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y%m%d")

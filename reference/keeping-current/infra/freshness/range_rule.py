"""The rule that keeps the lanes apart (spec/keeping-current.md, "The rule that keeps the lanes apart").

A deploy of `main` may take the routine lane only if EVERY commit between the deployed commit and `main` is one
GitHub itself records as authored by Dependabot (user id 49699333) AND marks as verified. Anything else — one
feature commit, a commit whose author GitHub cannot name, an unsigned commit, an empty or unreadable range, a
`main` that no longer descends from the deployed commit — is the judgement lane's, and the routine lane refuses.

The input is GitHub's own compare answer (`GET /repos/{owner}/{repo}/compare/{deployed}...{head}`), never a local
`git log`: the routine lane never trusts `main`'s text, only what GitHub verified (the plan's section G). Two
callers: the daily job, before it builds `main` instead of the deployed commit; and the routine deploy job, which
re-checks the claim for the tag it was handed and never takes the caller's word for it.

House rules: REJECT, NEVER TRUNCATE — a compare page that lists fewer commits than it counts is refused. EMPTY
BEATS WRONG — an identical range is not "routine", it is nothing to ship.
"""
import dataclasses

DEPENDABOT_ID = 49699333            # GitHub's own id for the `dependabot[bot]` user
DEPENDABOT_LOGIN = "dependabot[bot]"


@dataclasses.dataclass(frozen=True)
class RangeVerdict:
    routine: bool
    reason: str
    count: int = 0
    head: str = ""

    def line(self):
        return ("ROUTINE — " if self.routine else "NOT ROUTINE — ") + self.reason


def judge(compare):
    """GitHub's compare answer -> may the routine lane ship its head? Refuses on any doubt."""
    if not isinstance(compare, dict):
        return RangeVerdict(False, "the compare answer is not an object")
    status = compare.get("status")
    if status == "identical":
        return RangeVerdict(False, "main is the deployed commit — nothing to ship")
    if status != "ahead":
        return RangeVerdict(False, f"main is '{status or 'unreadable'}' relative to the deployed commit, not ahead of it — "
                                   "the deployed commit must be an ancestor of main")
    commits = compare.get("commits")
    if not isinstance(commits, list) or not commits:
        return RangeVerdict(False, "the compare answer lists no commits")
    total = compare.get("total_commits")
    if total != len(commits):
        return RangeVerdict(False, f"the compare answer lists {len(commits)} of {total} commits — truncated, refusing")
    for c in commits:
        if not isinstance(c, dict):
            return RangeVerdict(False, "a commit entry is not an object")
        sha = str(c.get("sha") or "")[:7] or "?"
        author = c.get("author")
        if not isinstance(author, dict) or author.get("id") != DEPENDABOT_ID:
            who = author.get("login") if isinstance(author, dict) and author.get("login") else "an author GitHub does not name"
            return RangeVerdict(False, f"commit {sha} is by {who}, not {DEPENDABOT_LOGIN} — a person's change, the judgement lane's")
        verification = (c.get("commit") or {}).get("verification") or {}
        if not isinstance(verification, dict) or verification.get("verified") is not True:
            reason = verification.get("reason") if isinstance(verification, dict) else None
            return RangeVerdict(False, f"commit {sha} is by {DEPENDABOT_LOGIN} but GitHub does not mark it verified "
                                       f"({reason or 'no reason given'})")
    n = len(commits)
    return RangeVerdict(True, f"{n} commit{'s' if n != 1 else ''} since the deployed commit, every one authored by "
                              f"{DEPENDABOT_LOGIN} and verified by GitHub", count=n, head=str(commits[-1].get("sha") or ""))

"""The one decision the daily job makes, and the two things it is never allowed to do.

Phase 2 of `spec/keeping-current.md` (design B, steps 4 and 6). Five arms:

    GREEN_SILENT   nothing moved, nothing found. The candidate tag is deleted; no click, no issue.
    PROMOTE(tag)   packages moved and the scan is clean -> import THAT digest and ask for the gate.
    RED(pkg, fix)  a fixable CVE the rebuild did not fix. The job fails; the owner hears it first.
    HOLD(since)    a prod approval is already waiting, or a `deploy` issue is open (`held_by`). One
                   thing waiting for the owner, always.
    INCONCLUSIVE   a side could not be read. Neither green nor a trigger.

Two rules with teeth:

  * A PENDING DISPATCH NEVER YIELDS PROMOTE (security lens F6, failure lens F5). Two pending "Review
    deployments" entries against the same environment is how a one-click gate becomes a pile nobody
    can tell apart, and approving the older of two queued runs ships the older image over the newer.
  * `dry` COMPUTES BUT NEVER ACTS. `will_promote` is the single flag the workflow reads before it
    imports a digest, deletes a tag or dispatches `deploy.yml`. The kind is the same in both modes —
    what a dry run is allowed to DO is the only difference — so the two can never drift apart.
"""
import dataclasses

from infra.freshness.inventory import INCONCLUSIVE as _INCONCLUSIVE
from infra.freshness.inventory import MOVED, worst_first

GREEN_SILENT, PROMOTE, RED, HOLD = "GREEN_SILENT", "PROMOTE", "RED", "HOLD"
INCONCLUSIVE = _INCONCLUSIVE          # the same word the compare uses, deliberately
DRY, FULL = "dry", "full"
MODES = (DRY, FULL)


@dataclasses.dataclass(frozen=True)
class Decision:
    kind: str
    mode: str = FULL
    tag: str = ""
    package: str = ""
    fix: str = ""
    installed: str = ""
    cve: str = ""
    reason: str = ""
    moved: tuple = ()
    where: str = ""            # "target: path" from the scan, so RED says where — or "" when it cannot

    @property
    def will_promote(self):
        """The gate on every side effect. `dry` computes the promotion and is not permitted to act."""
        return self.kind == PROMOTE and self.mode == FULL

    @property
    def is_red(self):
        return self.kind == RED

    def moved_line(self):
        return "; ".join(f"{n} {old or '(absent)'} -> {new or '(absent)'}" for n, old, new in self.moved)

    def sentence(self):
        """One line, the same one the summary prints and the dispatch carries as its `reason`."""
        if self.kind == PROMOTE:
            verb = "promote" if self.will_promote else "would promote"
            return f"{verb} `{self.tag}` — {self.moved_line()}"
        if self.kind == RED:
            # The first live run (2026-09-11) said "msgpack 1.1.2 is fixable in 1.2.1" and it took a
            # probe of the running container to learn that it was pip's VENDORED copy. Trivy knew.
            where = f" — found in {self.where}" if self.where else ""
            return (f"RED — {self.package} {self.installed or '(installed)'} is fixable in "
                    f"{self.fix} ({self.cve}) and the rebuild did not fix it{where}")
        if self.kind == HOLD:
            return f"hold — {self.reason}"
        if self.kind == INCONCLUSIVE:
            return f"inconclusive — {self.reason}"
        return "green — nothing moved and nothing fixable was found; the candidate tag is deleted"


def _where(finding):
    """Trivy's target and the package's own file path, joined when both are known, else whichever is."""
    target, path = getattr(finding, "target", ""), getattr(finding, "path", "")
    return f"{target}: {path}" if target and path else (target or path)


def decide(verdict, trivy_findings, pending_dispatch, mode, *, tag="", held_by=""):
    """Turn the compare verdict, the (post-allowlist) scan findings and the gate's state into one act.

    `pending_dispatch` is empty when no prod run is waiting, and otherwise the time the waiting run
    was created — it goes into the HOLD sentence so the summary says since when. `held_by` is a
    second reason to hold, in words ("deploy issue #12 is open (since ...)"): Phase C's routine lane
    refuses while a `deploy` issue is open, so a PROMOTE would only dispatch a run that says no.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, not {mode!r}")

    # RED first: a fixable CVE still present after the rebuild is the news, whatever else is true.
    # A waiting gate means "do not file a second one" — never "say nothing today".
    blocking = worst_first(f for f in trivy_findings if f.fixable)
    if blocking:
        worst = blocking[0]
        return Decision(RED, mode, tag=tag, package=worst.package, fix=worst.fixed,
                        installed=worst.installed, cve=worst.cve, where=_where(worst))

    if verdict.kind == INCONCLUSIVE:
        return Decision(INCONCLUSIVE, mode, tag=tag, reason=verdict.reason)

    if verdict.kind == MOVED:
        # F5/F6 — one thing waiting for the owner at a time.
        if pending_dispatch: return Decision(HOLD, mode, tag=tag, moved=verdict.moved, reason=f"a prod approval is already waiting since {pending_dispatch}")
        if held_by: return Decision(HOLD, mode, tag=tag, moved=verdict.moved, reason=f"{held_by} — the routine lane is closed until a person closes it")
        if not tag:
            raise ValueError("PROMOTE needs the candidate tag it would import; none was given")
        return Decision(PROMOTE, mode, tag=tag, moved=verdict.moved)

    return Decision(GREEN_SILENT, mode, tag=tag)

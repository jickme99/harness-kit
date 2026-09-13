"""What a registry retention run would delete, decided as a pure function.

Lifted out of the heredoc inside `infra/registry-retention.sh` on 2026-09-10 (Phase 1 of
`spec/keeping-current.md`). The bash stays the thin shell around `az` — it reads the live
deployed image, lists the manifests, and does the deleting and the re-read verification. Everything
that DECIDES lives here, where `tests/test_registry_retention_plan.py` can reach it.

Why the move was worth doing rather than tidy: two of these rules had been wrong for weeks with
nothing to notice. The clock was the newest manifest's own timestamp, which freezes every age the
moment a registry goes quiet (plan review, failure lens F2) — the exact condition the plan is written
for. And nothing checked whether the listing had been TRUNCATED at `--top`, so a keep set computed
from half a registry was indistinguishable from one computed from all of it. Neither could be tested
while it lived inside a heredoc that only ran against a live registry.

House rules, in the order they get applied:
  * REJECT, NEVER TRUNCATE — every guard raises `RetentionRefused`, which the caller turns into an
    ABORT for that repository. A partial answer is never returned.
  * EMPTY BEATS WRONG — a listing whose dates cannot be read yields no protected tag, and therefore a
    refusal, not a delete set computed against nothing.
  * The `assert`s these guards replaced would be stripped by `python -O`. A guard that can be
    optimised out of the build is not a guard.
"""
import dataclasses
import datetime
import json
import os
import pathlib
import sys

FULL_SIZE = 20_000_000     # bytes: a real image here is 60-260 MB, an attestation referrer 0.6-35 KB
TOP = 1000                 # must match the `--top` the caller passed to `az acr manifest list-metadata`


class RetentionRefused(Exception):
    """A rule could not be proven from the rows given. Nothing is deleted; the caller aborts."""


@dataclasses.dataclass(frozen=True)
class Plan:
    keep: list                 # the manifest rows that stay, newest first
    delete_tags: list          # tag strings -> delete.txt
    delete_digests: list       # `sha256:...` strings -> delete-digests.txt
    untagged_small_kept: int   # the referrers; they go when their image goes, never on their own
    deployed_digest: str
    total: int                 # rows with a readable timestamp — the population every rule ran against
    days: int
    floor: int
    untagged_days: int
    delete_rows: list = dataclasses.field(default_factory=list, repr=False)
    untagged_rows: list = dataclasses.field(default_factory=list, repr=False)
    missing_protected: list = dataclasses.field(default_factory=list)   # restore points whose image is gone

    def summary(self):
        """The one line a maintainer reads on a dry run. Byte-for-byte what the heredoc printed."""
        return (f"  total {self.total}  keep {len(self.keep)}  delete-by-tag {len(self.delete_tags)}  "
                f"untagged-full-size-to-delete {len(self.delete_digests)} "
                f"(older than {self.untagged_days}d)  untagged-small-kept {self.untagged_small_kept}")

    def detail_lines(self):
        """Which images, by name and date — so a dry run is checkable, not just countable."""
        out = []
        for t in self.missing_protected:
            out.append(f"  WARNING: restore point image {t} is no longer in the registry — that revision "
                       "cannot be reactivated; a rollback must use a newer restore point")
        if self.delete_rows:
            out.append(f"  oldest to go: {self.delete_rows[-1]['tag']} ({_ts(self.delete_rows[-1]):%Y-%m-%d})"
                       f"   newest to go: {self.delete_rows[0]['tag']} ({_ts(self.delete_rows[0]):%Y-%m-%d})")
        for r in self.untagged_rows:
            out.append(f"  untagged image to go: {r['digest'][:19]}  built {_ts(r):%Y-%m-%d}  "
                       f"{(r.get('size') or 0) // 1_000_000} MB")
        return out


def _ts(r):
    """The manifest's creation time, or None if this row cannot be dated at all.

    A row we cannot date is dropped rather than guessed at — and if that row was the deployed one, the
    keep-set guard below refuses the whole plan. The non-ValueError arms are defensive: ACR always
    returns a string here, and a row that came back as a number should refuse, not raise a traceback
    out of the middle of the rule.
    """
    try:
        return datetime.datetime.fromisoformat((r.get("created") or "").replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return None


def _guard(ok, message):
    if not ok:
        raise RetentionRefused(message)


def plan(rows, *, deployed_tag, days, floor, untagged_days, now, full_size=FULL_SIZE, top=TOP, protected=()):
    """Decide the keep set and the two delete sets. Pure: same rows in, same Plan out, nothing touched.

    `rows` is `az acr manifest list-metadata`'s answer projected to {tag, created, digest, size};
    `deployed_tag` is read LIVE from the Container App or Job by the caller, never assumed; `now` is
    passed in rather than read here, which is what makes the quiet-period case testable.
    """
    dep = deployed_tag
    # 2026-09-11 (two-lanes plan B5, failure lens F7) — RESTORE POINTS. The canary keeps the last revisions
    # as restore points; each runs an image tag of its own, and a restore point whose image is gone cannot
    # be reactivated. The caller reads those tags from the Container App's revisions and passes them here;
    # they are kept whatever their age or rank, and a tag that is not in the registry at all is refused
    # rather than silently accepted — the caller must see that a restore point has already lost its image.
    protected = frozenset(t for t in protected if t)
    rows = sorted((r for r in rows if _ts(r)), key=_ts, reverse=True)
    _tags_present = {r.get("tag") for r in rows if r.get("tag")}
    _missing = sorted(protected - _tags_present)      # reported below, never a refusal
    _guard(len(rows) < top, "GUARD: the manifest listing hit --top; raise it before trusting the keep set")
    # 2026-09-10 (plan review, failure lens F2) — THE CLOCK IS THE WALL CLOCK, handed in by the caller.
    # It used to be `rows[0]`'s own timestamp, which freezes every age the moment nothing new is built:
    # in a quiet month an untagged image three days younger than the newest build stayed "three days
    # old" forever, was never pruned, and Defender re-scanned it every night.
    cutoff, ucutoff = [now - datetime.timedelta(days=d) for d in (days, untagged_days)]

    keep, dele = [], []
    for i, r in enumerate(rows):
        if r.get("tag") == dep or r.get("tag") in protected or i < floor or _ts(r) >= cutoff: keep.append(r)
        elif r.get("tag"): dele.append(r)

    # 2026-09-10 — the untagged FULL-SIZE rule (findings log G3/G4): a superseded build
    # nothing can deploy by tag, judged on its OWN age — not the floor, which protects rollback TAGS —
    # deleted by digest, never the deployed digest.
    dep_digest = next((r.get("digest") for r in rows if r.get("tag") == dep), None)
    udele = []
    for r in rows:
        if r.get("tag") or not r.get("digest"): continue
        if (r.get("size") or 0) < full_size: continue        # a referrer; it goes with its image
        if _ts(r) >= ucutoff: continue
        if r["digest"] == dep_digest: continue               # never the running image, by digest
        udele.append(r)

    _guard(dep in [r.get("tag") for r in keep], "GUARD: deployed tag is not in the keep set")
    _guard(dep not in [r.get("tag") for r in dele], "GUARD: deployed tag is in the delete set")
    _guard(not (protected & {r.get("tag") for r in dele}), "GUARD: a protected restore-point tag is in the delete set")
    _guard(bool(dep_digest), "GUARD: the deployed tag has no manifest in the listing")
    _guard(dep_digest not in [r["digest"] for r in udele], "GUARD: deployed digest is in the untagged delete set")
    _guard(all(not r.get("tag") for r in udele), "GUARD: a tagged manifest reached the untagged delete set")

    return Plan(
        keep=keep,
        delete_tags=[r["tag"] for r in dele],
        delete_digests=[r["digest"] for r in udele],
        untagged_small_kept=sum(1 for r in rows if not r.get("tag") and (r.get("size") or 0) < full_size),
        deployed_digest=dep_digest,
        total=len(rows), days=days, floor=floor, untagged_days=untagged_days,
        delete_rows=dele, untagged_rows=udele, missing_protected=_missing,
    )


def main():
    """The shell's entry point: read $WORK/all.json, print the plan, write the two delete lists."""
    w = pathlib.Path(os.environ["WORK"])
    rows = json.loads((w / "all.json").read_text(encoding="utf-8"))
    try:
        p = plan(rows,
                 deployed_tag=os.environ["DEPLOYED"],
                 protected=[t.strip() for t in os.environ.get("PROTECTED", "").split(",") if t.strip()],
                 days=int(os.environ["DAYS"]), floor=int(os.environ["FLOOR"]),
                 untagged_days=int(os.environ["UDAYS"]),
                 now=datetime.datetime.now(datetime.timezone.utc),
                 top=int(os.environ.get("TOP", TOP)))
    except RetentionRefused as e:
        print(e, file=sys.stderr)
        return 1
    print(p.summary())
    for line in p.detail_lines():
        print(line)
    # newline='\n' on purpose: the default on Windows is CRLF, and `read` would keep the \r (bash note 1)
    for name, values in (("delete.txt", p.delete_tags), ("delete-digests.txt", p.delete_digests)):
        with open(w / name, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("".join(v + "\n" for v in values))
    return 0


if __name__ == "__main__":
    sys.exit(main())

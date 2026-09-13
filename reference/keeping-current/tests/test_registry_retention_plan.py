"""Phase 1 — the registry keep/delete rules, lifted out of the bash and pinned by tests (2026-09-10).

Until today every rule below lived in a heredoc inside `infra/registry-retention.sh`, which means the
only way to exercise one was to point it at a live registry and read what it said it would delete. Two
of the rules had already been wrong in production for weeks without anything noticing:

  * the CLOCK was the newest manifest's own timestamp, so a quiet registry froze every age and an
    untagged image that Defender kept re-scanning was kept forever (plan review, failure lens F2);
  * nothing asserted the listing had not been TRUNCATED at `--top`, so a keep set computed from a
    partial listing would have looked exactly like a keep set computed from the whole one.

Every row here is fictional. The timestamps are relative to a fixed `NOW` that the module takes as a
parameter — that is the whole point of the wall-clock test: `now` is an input, so the quiet-period case
is something a test can state rather than something you wait a month to see.

The house rules these tests encode: REJECT, NEVER TRUNCATE (a listing we cannot read is a refusal, not
a smaller delete set); EMPTY BEATS WRONG; and every deletion has to be provable from the rows given.
"""
import copy
import datetime

import pytest

from infra.registry_retention_plan import RetentionRefused, plan

NOW = datetime.datetime(2026, 9, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)
FULL = 121_000_000          # a real image here is 60-260 MB
REFERRER = 11_000           # the attestation-sized manifests every build leaves beside its image

# Fictional digests: 64 hex characters, distinct in their first bytes so a failure message is readable.
def _digest(seed):
    return "sha256:" + (f"{seed:02x}" * 32)


def row(tag, age_days, seed, size=FULL):
    """One manifest as `az acr manifest list-metadata` returns it (tag / created / digest / size)."""
    created = (NOW - datetime.timedelta(days=age_days)).isoformat().replace("+00:00", "Z")
    return {"tag": tag, "created": created, "digest": _digest(seed), "size": size}


def ladder(n, start_age=1, prefix="tag", seed0=1):
    """`n` tagged manifests, one per day, newest first — the shape a real repository has."""
    return [row(f"{prefix}{i:04x}", start_age + i, seed=seed0 + i) for i in range(n)]


def call(rows, deployed_tag, *, days=30, floor=10, untagged_days=7, now=NOW, **kw):
    return plan(rows, deployed_tag=deployed_tag, days=days, floor=floor,
                untagged_days=untagged_days, now=now, **kw)


# --------------------------------------------------------------------------------------------------
# the keep rules
# --------------------------------------------------------------------------------------------------

def test_floor_keeps_the_newest_regardless_of_age():
    """The floor protects ROLLBACK TAGS: the N newest survive even when every one of them is ancient.

    Fails if the floor is dropped, or is applied by age instead of by position — a registry that has
    not been built in a year would then empty itself down to the deployed tag on the next run.
    """
    rows = ladder(12, start_age=300)          # every single one is far beyond the 30-day window
    p = call(rows, deployed_tag=rows[0]["tag"], floor=10)

    assert [r["tag"] for r in p.keep] == [r["tag"] for r in rows[:10]]
    assert p.delete_tags == [rows[10]["tag"], rows[11]["tag"]]


def test_the_deployed_tag_is_kept_even_when_it_is_the_oldest_thing_in_the_registry():
    """A rollback parks prod on an old tag; the next run must not delete the image prod is running.

    Fails if the `r.get("tag") == dep` arm of the classifier is dropped: the deployed tag is the
    oldest row here and outside both the floor and the window, so it would land in delete_tags — and
    the guard would then refuse rather than delete, which is also a failure of this assertion.
    """
    rows = ladder(15, start_age=200)
    deployed = rows[-1]["tag"]                # the oldest manifest in the listing

    p = call(rows, deployed_tag=deployed)

    assert deployed in [r["tag"] for r in p.keep]
    assert deployed not in p.delete_tags
    assert p.deployed_digest == rows[-1]["digest"]


def test_an_old_tagged_image_beyond_the_floor_is_deleted():
    """The ordinary case: past the floor and past the window, a tagged image goes by tag."""
    rows = ladder(3, start_age=1) + ladder(2, start_age=90, prefix="old", seed0=50)
    p = call(rows, deployed_tag=rows[0]["tag"], floor=3)

    assert p.delete_tags == ["old0000", "old0001"]
    assert p.delete_digests == []


def test_a_tagged_image_inside_the_window_is_kept_even_past_the_floor():
    """`--days` and `--floor` are OR, not AND — this is the rule that makes the keep set generous."""
    rows = ladder(20, start_age=1)
    p = call(rows, deployed_tag=rows[0]["tag"], floor=3, days=30)

    assert p.delete_tags == []
    assert len(p.keep) == 20


# --------------------------------------------------------------------------------------------------
# the untagged full-size rule (the G3/G4 rule, 2026-09-10)
# --------------------------------------------------------------------------------------------------

def test_an_old_untagged_full_size_image_is_deleted_by_digest_and_a_young_one_is_kept():
    """The rule that closes G3: nothing can deploy these by tag, but Defender re-scans them daily.

    Fails if the rule is judged on the floor instead of on the image's own age (both untagged rows
    sit inside floor=10 here), or if the age comparison is inverted.
    """
    rows = ladder(4, start_age=1)
    old_untagged = row(None, 30, seed=0xa1)
    young_untagged = row(None, 3, seed=0xa2)
    p = call(rows + [old_untagged, young_untagged], deployed_tag=rows[0]["tag"],
             floor=10, untagged_days=7)

    assert p.delete_digests == [old_untagged["digest"]]
    assert young_untagged["digest"] not in p.delete_digests
    assert p.delete_tags == []                 # an untagged manifest never goes by tag


def test_a_small_untagged_manifest_is_never_deleted_at_any_age():
    """The referrers (634 B - 35 KB) every build leaves beside its image go WITH their image.

    Fails if the size threshold is dropped or inverted: deleting a referrer out from under a live
    image is a way to corrupt an image that is still deployable, for no benefit at all.
    """
    rows = ladder(4, start_age=1)
    referrer = row(None, 3650, seed=0xb1, size=REFERRER)     # ten years old
    p = call(rows + [referrer], deployed_tag=rows[0]["tag"], untagged_days=7)

    assert p.delete_digests == []
    assert p.untagged_small_kept == 1


def test_the_deployed_digest_is_never_in_the_untagged_delete_set():
    """Belt and braces: the same digest carrying the live tag AND sitting untagged and old.

    ACR lists one row per manifest, so this shape is defensive rather than routine — but the
    `r["digest"] == dep_digest` skip is the last thing standing between an odd listing and deleting
    the running image by digest. Removing that skip does not merely delete it: the guard downstream
    refuses the whole plan, so this test fails either way (wrong delete set, or a raised refusal).
    """
    rows = ladder(4, start_age=1)
    deployed = rows[0]["tag"]
    shadow = dict(row(None, 40, seed=0xc1), digest=rows[0]["digest"])   # same digest, untagged, old

    p = call(rows + [shadow], deployed_tag=deployed, untagged_days=7)

    assert p.deployed_digest == rows[0]["digest"]
    assert p.delete_digests == []
    assert p.deployed_digest not in p.delete_digests


def test_a_digest_pinned_deployment_refuses_rather_than_guessing():
    """An app pointed at `registry/repo@sha256:...` — the bash reduces that to the trailing hex.

    That hex can never equal a TAG in the listing, so the keep-set guard fires and nothing is
    deleted. The failure lens traced this case and found it already closed; this pins it, because
    the quiet alternative (a deployed tag that matches nothing, treated as "no protected tag") would
    delete the running image's tag neighbours with no guard left standing.
    """
    rows = ladder(15, start_age=90)
    pinned_hex = rows[0]["digest"].split(":")[1]          # what `sed 's/.*://'` leaves behind

    with pytest.raises(RetentionRefused) as e:
        call(rows, deployed_tag=pinned_hex)

    assert str(e.value) == "GUARD: deployed tag is not in the keep set"


# --------------------------------------------------------------------------------------------------
# the clock
# --------------------------------------------------------------------------------------------------

def test_the_wall_clock_prunes_a_registry_that_has_been_quiet_for_forty_days():
    """F2, the quiet-period bug, stated as a test instead of waited for.

    Every manifest here is older than 40 days, so the OLD clock (`now = newest manifest`) put the
    tagged cutoff at 70 days and the untagged cutoff at 47 days — under which this registry has
    nothing to delete at all, forever, and reports "nothing to prune" every single day while
    Defender keeps re-scanning the untagged image.

    Fails the moment the reference point goes back to `rows[0]`: delete_tags becomes [] and
    delete_digests becomes [].
    """
    tagged = ladder(12, start_age=40)                      # 40d .. 51d old
    stale_untagged = row(None, 45.5, seed=0xd1)            # older than 7d, younger than 47d
    rows = tagged + [stale_untagged]

    p = call(rows, deployed_tag=tagged[0]["tag"], days=30, floor=10, untagged_days=7)

    assert p.delete_tags == [tagged[9]["tag"], tagged[10]["tag"], tagged[11]["tag"]]
    assert p.delete_digests == [stale_untagged["digest"]]
    # and the floor does NOT shelter it: the row sorts to index 6, well inside floor=10, so the
    # classifier files it under `keep` — and the untagged rule, judged on the image's own age,
    # deletes it anyway. That split is deliberate: the floor protects rollback TAGS, not orphans.
    assert stale_untagged["digest"] in [r["digest"] for r in p.keep]


def test_the_clock_is_an_input_not_a_read_inside_the_rule():
    """The clock is passed in, not read inside — which is what makes the rule testable at all."""
    rows = ladder(12, start_age=40)
    later = call(rows, deployed_tag=rows[0]["tag"], now=NOW + datetime.timedelta(days=365))

    assert len(later.delete_tags) == 2          # the floor still holds; everything else has aged out


# --------------------------------------------------------------------------------------------------
# the refusals — reject, never truncate
# --------------------------------------------------------------------------------------------------

def test_a_listing_that_hit_top_is_refused_not_truncated():
    """A keep set computed from a partial listing looks exactly like one computed from the whole.

    Fails if the `top` assertion is dropped: the plan would return happily, having decided what to
    delete from a listing that stopped early — the deleted rows would be real, the kept rows would be
    a guess, and there is no output that would tell them apart.
    """
    rows = ladder(5, start_age=1)
    with pytest.raises(RetentionRefused) as e:
        call(rows, deployed_tag=rows[0]["tag"], top=5)

    assert str(e.value) == "GUARD: the manifest listing hit --top; raise it before trusting the keep set"


def test_a_listing_just_under_top_is_allowed():
    """The boundary in the other direction — `< top` is fine, `>= top` is the refusal."""
    rows = ladder(5, start_age=1)
    p = call(rows, deployed_tag=rows[0]["tag"], top=6)
    assert len(p.keep) == 5


def test_a_listing_with_no_usable_timestamps_refuses_rather_than_deleting_everything():
    """EMPTY BEATS WRONG. Undateable rows are dropped; with none left, nothing protects the live tag.

    Fails if the refusal is dropped: an empty delete set would be the *lucky* outcome here, and a
    delete set computed against `now` with no rows to compare is a coin toss on the running image.
    """
    rows = [
        {"tag": "aa000001", "created": None, "digest": _digest(1), "size": FULL},
        {"tag": "aa000002", "created": "", "digest": _digest(2), "size": FULL},
        {"tag": "aa000003", "created": "not-a-date", "digest": _digest(3), "size": FULL},
        {"tag": "aa000004", "created": 1757505600, "digest": _digest(4), "size": FULL},
    ]
    with pytest.raises(RetentionRefused) as e:
        call(rows, deployed_tag="aa000001")

    assert str(e.value) == "GUARD: deployed tag is not in the keep set"


def test_a_deployed_tag_whose_manifest_carries_no_digest_is_refused():
    """The listing named the tag but gave no digest — the untagged rule would then have nothing to
    compare against, and every untagged full-size row would look like "not the deployed one"."""
    rows = ladder(4, start_age=1)
    rows[0] = dict(rows[0], digest=None)
    old_untagged = row(None, 40, seed=0xe1)

    with pytest.raises(RetentionRefused) as e:
        call(rows + [old_untagged], deployed_tag=rows[0]["tag"])

    assert str(e.value) == "GUARD: the deployed tag has no manifest in the listing"


def test_the_two_belt_and_braces_guards_hold_as_properties_of_every_plan():
    """`deployed tag is in the delete set` and `a tagged manifest reached the untagged delete set`
    are both unreachable from a valid listing by construction — the classifier puts the deployed tag
    in `keep` and the untagged loop skips anything with a tag. They exist so that a future edit to
    either loop cannot silently produce the thing they name. What a test CAN pin is the property
    itself, on a listing rich enough to exercise both loops at once."""
    rows = ladder(15, start_age=90) + [row(None, 40, seed=0xf1), row(None, 2, seed=0xf2),
                                       row(None, 400, seed=0xf3, size=REFERRER)]
    deployed = rows[12]["tag"]

    p = call(rows, deployed_tag=deployed, floor=5, days=30, untagged_days=7)

    assert deployed not in p.delete_tags
    assert deployed in [r["tag"] for r in p.keep]
    tags_by_digest = {r["digest"]: r["tag"] for r in rows}
    assert all(tags_by_digest[d] is None for d in p.delete_digests)


# --------------------------------------------------------------------------------------------------
# the shape of the answer
# --------------------------------------------------------------------------------------------------

def test_plan_is_a_no_op_on_its_input_and_identical_when_run_twice():
    """A dry run and the apply run that follows it must decide the same thing, and the caller's rows
    must come back untouched — today's code sorts the caller's list in place, which is invisible
    until something else reads it after the plan."""
    rows = ladder(14, start_age=20) + [row(None, 40, seed=0x11), row(None, 400, seed=0x12,
                                                                    size=REFERRER)]
    before = copy.deepcopy(rows)

    first = call(rows, deployed_tag=rows[0]["tag"], floor=5, days=10, untagged_days=7)
    second = call(rows, deployed_tag=rows[0]["tag"], floor=5, days=10, untagged_days=7)

    assert rows == before                       # the input list is not reordered under the caller
    assert first.delete_tags == second.delete_tags
    assert first.delete_digests == second.delete_digests
    assert first.deployed_digest == second.deployed_digest
    assert first.untagged_small_kept == second.untagged_small_kept
    assert first.summary() == second.summary()
    assert first.detail_lines() == second.detail_lines()


def test_the_summary_line_says_what_was_decided():
    """The summary is the only thing a maintainer reads on a dry run, so it carries every count."""
    rows = ladder(14, start_age=20) + [row(None, 40, seed=0x21), row(None, 400, seed=0x22,
                                                                    size=REFERRER)]
    p = call(rows, deployed_tag=rows[0]["tag"], floor=5, days=10, untagged_days=7)

    line = p.summary()
    assert line.startswith("  total 16  keep 5  delete-by-tag 9  ")
    assert "untagged-full-size-to-delete 1 (older than 7d)" in line
    assert "untagged-small-kept 1" in line
    assert any("untagged image to go:" in d for d in p.detail_lines())

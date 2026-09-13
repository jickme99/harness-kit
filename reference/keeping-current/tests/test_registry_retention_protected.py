"""Restore points are protected from the registry prune — RED-first (spec/keeping-current.md B5; the two-lanes
panel's failure lens F7).

The prune's only guard used to be the ONE tag the live Container App template names. The canary keeps the
last revisions as restore points (a deactivated revision can be reactivated in about a minute) and each of
those revisions runs an image tag of its own; nothing told the prune those tags were special, so a burst
of deploys — or a tighter retention policy one day — could delete the image a restore point needs.
Now the caller passes the restore points' tags as `protected`, the plan keeps them whatever their age or
rank, and a guard refuses a plan that would delete one.
"""
import datetime

import pytest

from infra.registry_retention_plan import RetentionRefused, plan

NOW = datetime.datetime(2026, 9, 11, 12, 0, tzinfo=datetime.timezone.utc)


def row(tag, days_old, digest=None, size=50_000_000):
    return {"tag": tag, "digest": digest or f"sha256:{tag or 'untagged'}{days_old:04d}",
            "created": (NOW - datetime.timedelta(days=days_old)).isoformat().replace("+00:00", "Z"), "size": size}


def test_a_protected_tag_is_kept_even_when_old_and_beyond_the_floor():
    rows = [row("newest00", 0), row("recent01", 1), row("deployed", 2), row("restore1", 40), row("restore2", 45), row("ancient9", 90)]
    p = plan(rows, deployed_tag="deployed", days=30, floor=3, untagged_days=7, now=NOW, protected={"restore1", "restore2"})
    kept = {r["tag"] for r in p.keep}
    assert {"restore1", "restore2", "deployed"} <= kept
    assert "ancient9" in p.delete_tags                      # protection is by name, not a blanket "keep old"
    assert "restore1" not in p.delete_tags and "restore2" not in p.delete_tags


def test_without_protection_the_same_old_tags_would_go():
    """The test above is only meaningful if the floor and the age would otherwise delete them."""
    rows = [row("newest00", 0), row("recent01", 1), row("deployed", 2), row("restore1", 40), row("restore2", 45)]
    p = plan(rows, deployed_tag="deployed", days=30, floor=3, untagged_days=7, now=NOW)
    assert {"restore1", "restore2"} <= set(p.delete_tags)


def test_a_protected_tag_missing_from_the_registry_is_reported_not_invented_and_not_a_refusal():
    """A restore point whose image is already gone is a fact the caller must see (the revision cannot be
    reactivated), never silently accepted — and never a refusal either: refusing would stop every future
    prune of the repository over an image nothing can bring back (measured 2026-09-11 on the MCP's v1)."""
    rows = [row("newest00", 0), row("deployed", 2)]
    p = plan(rows, deployed_tag="deployed", days=30, floor=3, untagged_days=7, now=NOW, protected={"vanished"})
    assert p.missing_protected == ["vanished"]
    assert any("vanished" in ln and "WARNING" in ln for ln in p.detail_lines())
    assert [r["tag"] for r in p.keep] == ["newest00", "deployed"]

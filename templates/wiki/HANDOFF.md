---
title: Handoff
type: status
created: {{YYYY-MM-DD}}
updated: {{YYYY-MM-DD}}
tags: [handoff, succession]
related: [[status]] [[decisions]] [[log]]
---

# Handoff

**Summary:** What the last session left so the next one does not reconstruct it from
git. Snapshot page — refresh as work ends, not as a chore afterward. Kit-neutral: name
this project's facts, not another repo's.

## Last decision

{{Newest dated heading from wiki/decisions.md, one line. Hedge travels with the claim.}}

## Next

{{The next concrete task. One sentence. Pointers to the plan page if one exists.}}

## Kit version

Stamped `{{kit_version from kit-manifest.json}}`. Poll before close-out:

```sh
python scripts/kit_poll.py --project . --kit {{path to a harness-kit clone}}
```

Never self-apply. Record "caught up" or the worklist heading in [[log]].

## Not in this repo

{{What a cold-start agent must not look for here: sibling brain/body checkout, owner
drop-box, credentials, vendor UIs, machine-local memory of another tool. If one-repo
shape and everything is here, say so.}}

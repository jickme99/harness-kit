#!/usr/bin/env bash
# Registry retention — delete old container images, keep anything that could be needed.
#
#   bash infra/registry-retention.sh dev              # DRY RUN (default) — shows what it would delete
#   bash infra/registry-retention.sh dev --apply      # actually delete
#   bash infra/registry-retention.sh prod --apply --days 60
#   RETENTION_APPLY=1 bash infra/registry-retention.sh prod   # same as --apply, without a flag
#
# WHY THIS EXISTS: the registry SKU is Basic, which has no automatic retention policy (that needs
# Premium, a recurring cost). Without it, every image ever built is stored and RE-SCANNED forever, and
# each old image keeps reporting the CVEs that were fixed in later builds. A registry that has never
# been pruned will show findings dominated by images nobody can ever deploy.
#
# WHAT DECIDES, AND WHAT ACTS. This script is the thin shell around `az`: it reads the live deployed
# image, lists the manifests, deletes, and verifies by re-reading the registry. The keep/delete RULES
# live in infra/registry_retention_plan.py, where tests/test_registry_retention_plan.py can reach them
# (2026-09-10, Phase 1 of spec/keeping-current.md). They used to be a heredoc in this file, which
# is how two of them stayed wrong for weeks: nothing could exercise a rule without a live registry.
#
# KEEP RULE (deliberately generous — images are only recoverable by rebuilding):
#   * the tag currently deployed, read LIVE from the Container App or Container App JOB (never assumed)
#   * everything built within --days
#   * a floor of the --floor newest, whatever their age
#   * every SMALL untagged manifest (under 20 MB: the attestation-sized referrers every build leaves
#     beside its image; they go when their image goes)
#
# DELETE RULE added 2026-09-10 (findings log G3/G4): an UNTAGGED FULL-SIZE image (20 MB or
# more) older than --untagged-days is deleted BY DIGEST. Nothing can deploy it by tag, but Defender
# re-scans it and keeps reporting the CVEs later builds fixed — the two "Update expat" findings of
# 2026-09-10 sat on two such images from 2026-08-25. The deployed image's own digest is guarded, and
# the rule is judged on the image's own age, not the floor (the floor protects rollback TAGS).
#
# PER-ENVIRONMENT DEFAULTS (spec/keeping-current.md §C; the flags remain, for a one-off):
#
#     env  | tagged: --days / --floor | untagged full-size: --untagged-days
#     prod |        30 / 10           |          7
#     dev  |         7 /  5           |          2
#
# ONE MECHANISM PER REPOSITORY (2026-09-10). The vendor's stock purge task has no deployed-tag
# guard at all — `acr purge --ago 7d --keep 5` would happily delete the image the app is running if a
# rollback parked prod on an older tag through a quiet week. This script replaces that task. Each
# repository is pruned against ITS OWN live workload, and a repository with no live reader configured
# is SKIPPED and never pruned — an unread repository must never be guessed at.
#
# SAFETY NOTES, 1-3 learned the hard way on 2026-08-06, 4 added with the loop on 2026-09-10:
#   1. CRLF. A tag list written by a Windows tool carries \r, `read` keeps it, and Azure answers
#      "The requested data does not exist" — which reads like the image is already gone rather than
#      like a broken argument. Every list here is passed through `tr -d '\r'` and hex-checked.
#   2. Guards validate themselves first. `grep -qF "$X"` with an empty $X matches EVERYTHING. The
#      deployed-tag guard asserts non-empty and well-formed before it is trusted. So does the
#      CROSS-CHECK below: the live image must literally begin with this registry and this repository,
#      or that repository aborts — a roster row copied from another and half-edited has to be caught
#      by design, not by the coincidence of the wrong tag also being absent from the right repository.
#   3. Exit codes lie. `az acr` prints preview warnings, and `cmd | head` reports head's status. The
#      only honest check is re-listing the registry afterward, which this script always does — per
#      repository. The run's own exit code is non-zero if ANY repository failed to verify.
#   4. The roster loop owns stdin. It is fed by a here-doc (not a pipe, so `FAILED` survives into the
#      parent shell), and every `az` and `python` call inside it keeps its `< /dev/null` so nothing
#      swallows the next repository's line.
set -uo pipefail

ENV="${1:-}"; shift || true

# Subscriptions BY GUID, never by name (plan review, security lens): a name is a display string that
# an account rename can quietly repoint; a GUID cannot be repointed at someone else's subscription.
#   (`az account show --subscription <name> --query id -o tsv` on each, once, then paste the GUID)
#
# The roster is `repository|kind|workload|resource-group`, kind = app | job | none. `none` means NO
# LIVE READER: printed as SKIPPED, never pruned. List EVERY repository the registry holds, one row
# each — a repository absent from the roster is invisible to this script, and a row with kind `none`
# is the honest form for an image nothing in this subscription runs: skipped, never pruned, until
# somebody names the workload that would say what is live.
#
# THE KIT SHIPS PLACEHOLDERS, NOT DEFAULTS. Fill in both environments before the first run; the guard
# under the block refuses to run while any `__PLACEHOLDER__` is left (a template that carries one
# project's registry names is how the next project prunes the wrong registry — kit audit finding #13).
case "$ENV" in
  dev)
    REG=__DEV_REGISTRY__;  SUB=__DEV_SUBSCRIPTION_GUID__;  DAYS=7;  FLOOR=5;  UDAYS=2
    ROSTER="__APP_REPOSITORY__|app|__DEV_CONTAINER_APP__|__DEV_RESOURCE_GROUP__" ;;
  prod)
    REG=__PROD_REGISTRY__; SUB=__PROD_SUBSCRIPTION_GUID__;  DAYS=30; FLOOR=10; UDAYS=7
    ROSTER="__APP_REPOSITORY__|app|__PROD_CONTAINER_APP__|__PROD_RESOURCE_GROUP__" ;;
  *) echo "usage: $0 <dev|prod> [--apply] [--days N] [--floor N] [--untagged-days N]" >&2; exit 2 ;;
esac
case "$REG$SUB$ROSTER" in
  *__*) echo "ABORT: the roster block at the top of $0 still carries __PLACEHOLDERS__ — fill in the registry, the subscription GUID and one row per repository before the first run." >&2; exit 2 ;;
esac

APPLY=0; APPLY_VIA=""
# RETENTION_APPLY=1 is the same as --apply, for callers that cannot pass flags (a guarded shell that
# refuses an opaque script invocation carrying options — the case on the maintainer's workstation).
# The startup line names WHICH mechanism armed it: an `export RETENTION_APPLY=1` left behind in a shell
# is the way this script deletes something nobody asked it to, and the line is what makes that visible.
[ "${RETENTION_APPLY:-0}" = "1" ] && { APPLY=1; APPLY_VIA="RETENTION_APPLY=1"; }
while [ $# -gt 0 ]; do
  case "$1" in
    --apply) APPLY=1; APPLY_VIA="--apply" ;;
    --days)  DAYS="$2"; shift ;;
    --floor) FLOOR="$2"; shift ;;
    --untagged-days) UDAYS="$2"; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"   # Git Bash rewrites /subscriptions/... otherwise
TOPN=1000                                           # `--top` and the truncation guard, from one place

RUNDIR="$(mktemp -d)"; trap 'rm -rf "$RUNDIR"' EXIT

# Git Bash on Windows ships `python`, most CI images ship `python3`. Resolve rather than assume.
PY=""
for c in python3 python py; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
[ -n "$PY" ] || { echo "ABORT: no python interpreter on PATH." >&2; exit 1; }

# The rules module is found relative to THIS FILE, never to the caller's directory — a build run from
# another clone of the same tree must not pick up a neighbour's copy.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAN_PY="$HERE/registry_retention_plan.py"
[ -f "$PLAN_PY" ] || { echo "ABORT: $PLAN_PY is missing — refusing to delete anything." >&2; exit 1; }
# Git Bash's /tmp/... and /d/... are not the paths a Windows-native python sees; cygpath -m bridges
# them. On Linux there is no cygpath and the paths are already correct.
command -v cygpath >/dev/null 2>&1 && PLAN_PY="$(cygpath -m "$PLAN_PY")"

prune_repo() {
  local REPO="$1" KIND="$2" RNAME="$3" RRG="$4"
  local WORK="$RUNDIR/$REPO"; mkdir -p "$WORK"
  local WORK_PY="$WORK"
  command -v cygpath >/dev/null 2>&1 && WORK_PY="$(cygpath -m "$WORK")"

  # --- the deployed image, read live from the running workload (guard 1: never assume it) ----------
  local SHOW=(az containerapp show)
  [ "$KIND" = "job" ] && SHOW=(az containerapp job show)
  local IMAGE
  IMAGE=$("${SHOW[@]}" -n "$RNAME" -g "$RRG" --subscription "$SUB" \
    --query "properties.template.containers[0].image" -o tsv < /dev/null 2>/dev/null | tr -d '\r')
  [ -n "$IMAGE" ] || { echo "  ABORT: could not read the live image from $KIND $RNAME ($RRG)." >&2; return 1; }

  # --- the cross-check (safety note 2): registry, repository and live workload must agree ----------
  if [ "${IMAGE#"$REG.azurecr.io/$REPO:"}" = "$IMAGE" ]; then
    echo "  ABORT: the live image does not name this registry and repository — nothing pruned." >&2
    echo "    live image:      $IMAGE" >&2
    echo "    expected prefix: $REG.azurecr.io/$REPO:" >&2
    return 1
  fi

  local DEPLOYED="${IMAGE##*:}"
  case "$DEPLOYED" in
    *[!a-zA-Z0-9._-]* ) echo "  ABORT: deployed tag '$DEPLOYED' is not a plausible tag." >&2; return 1 ;;
  esac
  echo "  deployed tag (live): $DEPLOYED   <- $KIND $RNAME ($RRG)"

  az acr manifest list-metadata -r "$REG" -n "$REPO" --subscription "$SUB" --orderby time_desc \
    --top "$TOPN" --query "[].{tag:tags[0],created:createdTime,digest:digest,size:imageSize}" -o json \
    < /dev/null 2>/dev/null > "$WORK/all.json"
  [ -s "$WORK/all.json" ] || { echo "  ABORT: the manifest listing came back empty." >&2; return 1; }

  # Restore points (the canary keeps the newest revisions, active or retired; each runs an image tag of
  # its own; the prune must never delete one of those — the revision could not be reactivated). Jobs have
  # no revisions: empty. A restore point whose image is already gone is reported by the rules as a
  # WARNING, never a refusal (a refusal would stop every future prune over an image nothing brings back).
  local PROTECTED=""
  if [ "$KIND" = "app" ]; then
    PROTECTED=$(az containerapp revision list -n "$RNAME" -g "$RRG" --subscription "$SUB" --all \
      --query "reverse(sort_by([], &properties.createdTime))[:3].properties.template.containers[0].image" -o tsv < /dev/null 2>/dev/null \
      | tr -d '\r' | sed -E 's#^.*:##' | paste -sd, -)
    echo "  restore points (newest 3 revisions): ${PROTECTED:-none}"
  fi
  DEPLOYED="$DEPLOYED" PROTECTED="$PROTECTED" DAYS="$DAYS" FLOOR="$FLOOR" UDAYS="$UDAYS" TOP="$TOPN" WORK="$WORK_PY" \
    "$PY" "$PLAN_PY" < /dev/null \
    || { echo "  ABORT: the keep/delete plan refused — nothing deleted for $REPO." >&2; return 1; }

  tr -d '\r' < "$WORK/delete.txt" > "$WORK/delete.lf"   # note 1: belt and braces
  tr -d '\r' < "$WORK/delete-digests.txt" > "$WORK/digests.lf"
  local COUNT UCOUNT
  COUNT=$(grep -c . "$WORK/delete.lf" || true)
  UCOUNT=$(grep -c . "$WORK/digests.lf" || true)
  [ "$COUNT" = "0" ] && [ "$UCOUNT" = "0" ] && { echo "  nothing to delete."; return 0; }

  if [ "$APPLY" != "1" ]; then
    echo "  DRY RUN — would delete $COUNT tagged image(s) and $UCOUNT untagged full-size image(s)."
    return 0
  fi

  local n=0 un=0 t d
  while read -r t; do
    [ -z "$t" ] && continue
    [ "$t" = "$DEPLOYED" ] && { echo "  REFUSED (deployed): $t"; continue; }   # guard 2, belt and braces
    n=$((n + 1))
    az acr repository delete -n "$REG" --image "$REPO:$t" --yes --subscription "$SUB" < /dev/null >/dev/null 2>&1
  done < "$WORK/delete.lf"
  while read -r d; do
    [ -z "$d" ] && continue
    un=$((un + 1))
    az acr repository delete -n "$REG" --image "$REPO@$d" --yes --subscription "$SUB" < /dev/null >/dev/null 2>&1
  done < "$WORK/digests.lf"

  # --- note 3: verify against the registry, NOT against the exit codes above -----------------------
  az acr repository show-tags -n "$REG" --repository "$REPO" --subscription "$SUB" -o tsv \
    < /dev/null 2>/dev/null | tr -d '\r' > "$WORK/after.txt"
  local STILL GONE USTILL UGONE
  STILL=$(grep -Fxf "$WORK/delete.lf" "$WORK/after.txt" | grep -c . || true)
  GONE=$((COUNT - STILL))
  echo "  tags: attempted $n; CONFIRMED GONE $GONE of $COUNT; still present $STILL"
  az acr manifest list-metadata -r "$REG" -n "$REPO" --subscription "$SUB" --top "$TOPN" \
    --query "[].digest" -o tsv < /dev/null 2>/dev/null | tr -d '\r' > "$WORK/after-digests.txt"
  USTILL=$(grep -Fxf "$WORK/digests.lf" "$WORK/after-digests.txt" | grep -c . || true)
  UGONE=$((UCOUNT - USTILL))
  echo "  untagged images: attempted $un; CONFIRMED GONE $UGONE of $UCOUNT; still present $USTILL"
  if ! grep -qFx "$DEPLOYED" "$WORK/after.txt"; then
    echo "  *** ALARM: the deployed tag $DEPLOYED is no longer in $REPO ***" >&2; return 1
  fi
  echo "  deployed tag $DEPLOYED still present. remaining: $(grep -c . "$WORK/after.txt") tagged image(s), $(grep -c . "$WORK/after-digests.txt") manifest(s)"
  [ "$STILL" = "0" ] && [ "$USTILL" = "0" ] && return 0
  return 1
}

echo "registry=$REG env=$ENV  keep=<deployed> + <${DAYS}d> + <${FLOOR} newest>  untagged-images-older-than=<${UDAYS}d>  mode=$([ "$APPLY" = 1 ] && echo "APPLY (armed by $APPLY_VIA)" || echo DRY-RUN)"

FAILED=0
while IFS='|' read -r REPO KIND RNAME RRG; do
  [ -z "$REPO" ] && continue
  [ "$KIND" = "none" ] && { echo "repo $REPO: SKIPPED (no live reader configured)"; continue; }
  echo "repo $REPO:"
  prune_repo "$REPO" "$KIND" "$RNAME" "$RRG" || FAILED=1
done <<ROSTER
$ROSTER
ROSTER

[ "$FAILED" = "0" ] || { echo "one or more repositories did not verify — see the ABORT lines above." >&2; exit 1; }
exit 0

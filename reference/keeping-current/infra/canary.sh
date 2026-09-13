#!/usr/bin/env bash
# TEMPLATE — fill in the environment table below (the guard under it refuses to run while a __PLACEHOLDER__
# is left) and the portal asset if yours differs. Doctrine: spec/keeping-current.md ("Who clicks"); the
# verdict rules: infra/canary_rules.py; the probe it runs inside the new revision: `python3 -m app.selftest`
# (app/selftest.py — extend it with one real call per service your domain uses). Harvested
# from a live script, 2026-09-11, with its names removed; the comments still tell its story.
# -----------------------------------------------------------------------------------------------------
# canary.sh — the canary deploy with automatic rollback (spec/keeping-current.md, design B).
#
#   bash infra/canary.sh setup    <dev|prod>                          # once: probes, revision mode Multiple,
#                                                                     #       traffic pinned to the live revision BY NAME
#   bash infra/canary.sh deploy   <dev|prod> <image-tag> <drill 0|1> [<checkout dir>]
#   bash infra/canary.sh rollback <dev|prod> <to-revision> [<from-revision>]
#   bash infra/canary.sh status   <dev|prod>
#
# The order of a deploy is the whole point (failure lens F2/F5/F9, security lens F7):
#   1. read the revision that has the traffic — by NAME, never "latest";
#   2. create the new revision at 0 % traffic (Multiple mode + pinned traffic make that the default),
#      with APP_VERSION=<tag>, APP_SELFTEST_FAIL=<0|1> stated EXPLICITLY on every deploy (an inherited
#      template value is how a stray drill lever would reach a real deploy), and at least one replica;
#   3. wait until the platform calls it Provisioned + Running + Healthy (the probes), with a deadline;
#   4. run the app's own self-test INSIDE it through the exec door, keep the transcript, and let
#      infra/canary_rules.py read it — three outcomes: PASS, FAIL, COULD_NOT_RUN (retry once after the
#      door's lockout, then fail closed with "the check could not run");
#   5. only then move traffic — 100 % to the new revision, 0 % to the previous, read back;
#   6. check through the public name: /health three times over fresh connections, and (judgement lane,
#      when a checkout is given) the served bytes of the portal asset against the checkout's copy;
#   7. success: after a grace period deactivate the previous revision (it stays a restore point: an
#      inactive revision can be reactivated — a cold start, not seconds);
#      failure after the switch: traffic back to the previous revision by name, verified, the new
#      revision deactivated, exit 1 with the exact command to run by hand.
# A drill (`deploy ... 1`) must be refused at step 4 by the lever and nothing else: then the script
# exits 0 ("DRILL PASSED") — the proof that a bad revision never receives traffic.
#
# Positional arguments only, never flags (the maintainer's guarded shell), every `az` call carries its
# subscription BY GUID, and nothing here reads a value it can also verify by a read-back.
# -----------------------------------------------------------------------------------------------------
set -euo pipefail
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"
# Strict mode must never fail silently: name the line and the command that stopped the script.
trap 'echo "ABORT: canary.sh stopped at line $LINENO: $BASH_COMMAND" >&2' ERR

CMD="${1:-}"; ENV="${2:-}"
case "$ENV" in
  # Fill the table in for a cloned app, OR set CANARY_<ENV>_SUB / _RG / _APP / _REG (and CANARY_IMG, CANARY_SELFTEST_MODULE)
  # in the caller's environment — a filled-in workflow does the latter from its env block.
  dev)  SUB=${CANARY_DEV_SUB:-__DEV_SUBSCRIPTION_GUID__};   RG=${CANARY_DEV_RG:-__DEV_RESOURCE_GROUP__};   APP=${CANARY_DEV_APP:-__DEV_CONTAINER_APP__};   REG=${CANARY_DEV_REG:-__DEV_REGISTRY__}.azurecr.io;   APP_ENV=Development ;;
  prod) SUB=${CANARY_PROD_SUB:-__PROD_SUBSCRIPTION_GUID__}; RG=${CANARY_PROD_RG:-__PROD_RESOURCE_GROUP__}; APP=${CANARY_PROD_APP:-__PROD_CONTAINER_APP__}; REG=${CANARY_PROD_REG:-__PROD_REGISTRY__}.azurecr.io; APP_ENV=Production ;;
  *) echo "usage: $0 setup|deploy|rollback|status <dev|prod> ..." >&2; exit 2 ;;
esac
IMG=${CANARY_IMG:-__APP_REPOSITORY__}
SELFTEST_MODULE=${CANARY_SELFTEST_MODULE:-app.selftest}     # the probe run inside the new revision
# THE TEMPLATE GUARD (kit audit finding #13): no defaults, only placeholders; refuse to run while one is left.
case "$SUB$RG$APP$REG$IMG" in
  *__*) echo "ABORT: infra/canary.sh still carries __PLACEHOLDERS__ for '$ENV' — fill in the environment table first." >&2; exit 2 ;;
esac
# The one static file whose bytes prove which build the public name is serving (judgement lane only; the
# check is skipped when the file is absent from the checkout). An app with a portal names one file.
# An app that serves no such file sets CANARY_ASSET_FILE to the empty string: the check is skipped.
ASSET_FILE="${CANARY_ASSET_FILE-app/static/portal.html}"
ASSET_URL="${CANARY_ASSET_URL-/ui/portal.html}"
PORT=8000
GRACE="${CANARY_GRACE_SECONDS:-60}"
READY_DEADLINE="${CANARY_READY_SECONDS:-420}"
DOOR_LOCKOUT_WAIT="${CANARY_DOOR_WAIT_SECONDS:-130}"

PY=""; for c in python3 python py; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
[ -n "$PY" ] || { echo "ABORT: no python interpreter on PATH." >&2; exit 1; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
OUT="${CANARY_OUT:-$(mktemp -d)}"; mkdir -p "$OUT"
ROOT_PY="$ROOT"; OUT_PY="$OUT"
command -v cygpath >/dev/null 2>&1 && { ROOT_PY="$(cygpath -m "$ROOT")"; OUT_PY="$(cygpath -m "$OUT")"; }

say() { printf '%s\n' "$*"; }
azq() {   # every READ retried three times: a transient CLI failure must not abort a canary mid-flight
          # (measured 2026-09-11: one did, right after the new revision was created)
  local i out
  for i in 1 2 3; do
    if out=$(az "$@" --subscription "$SUB" -o tsv < /dev/null 2>/dev/null); then printf '%s' "$out" | tr -d '\r'; return 0; fi
    sleep 5
  done
  return 1
}
app_q() { azq containerapp show -n "$APP" -g "$RG" --query "$1"; }
rev_q() { azq containerapp revision show -n "$APP" -g "$RG" --revision "$1" --query "$2"; }

# The revision that HAS the traffic, by name. Refuses a "latest" rule (that is what setup removes) and
# refuses anything but exactly one 100 % rule — the canary's whole safety rests on knowing this name.
traffic_holder() {
  local rules; rules=$(app_q "properties.configuration.ingress.traffic[].[revisionName, weight, latestRevision]")
  local holder="" n=0
  while IFS=$'\t' read -r name weight latest; do
    [ -z "${name}${weight}${latest}" ] && continue
    n=$((n + 1))
    if [ "$latest" = "true" ] || [ "$latest" = "True" ]; then say "ABORT: traffic still follows 'latest' — run: bash infra/canary.sh setup $ENV" >&2; return 1; fi
    if [ "$weight" = "100" ]; then holder="$name"; fi
  done <<< "$rules"
  [ -n "$holder" ] || { say "ABORT: no revision holds 100 % of the traffic (rules: $n) — refusing to guess." >&2; return 1; }
  printf '%s' "$holder"
}

wait_ready() {   # $1 revision; Provisioned + Running/RunningAtMaxScale + Healthy, within the deadline
  local rev="$1" t=0 p r h
  while [ $t -lt "$READY_DEADLINE" ]; do
    p=$(rev_q "$rev" properties.provisioningState); r=$(rev_q "$rev" properties.runningState); h=$(rev_q "$rev" properties.healthState)
    say "  $rev: provisioning=$p running=$r health=$h (${t}s)"
    case "$p/$r" in
      Provisioned/Running|Provisioned/RunningAtMaxScale) [ "$h" = "Healthy" ] && return 0 ;;
      *Failed*|*/Failed|*/Degraded) return 1 ;;
    esac
    sleep 15; t=$((t + 15))
  done
  return 1
}

health_ok() {   # stdin: GET /health body; 0 only when status is the string ok
  PYTHONPATH="$ROOT_PY" "$PY" -c \
    'import sys; from infra.canary_rules import health_body_ok; raise SystemExit(0 if health_body_ok(sys.stdin.read()) else 1)'
}

health_x3() {   # the public name, three fresh connections, every one must say status ok
  local fqdn="$1" i body
  for i in 1 2 3; do
    body=$(curl -s --max-time 45 "https://$fqdn/health" || true)
    if ! printf '%s' "$body" | health_ok; then
      say "  /health #$i: NOT ok: ${body:0:120}"; return 1
    fi
  done
  say "  /health ok x3 over fresh connections"
}

served_bytes_match() {   # judgement lane: the bytes the public name serves are the checkout's bytes, three times
  local fqdn="$1" checkout="$2" want got i
  [ -f "$checkout/$ASSET_FILE" ] || { say "  served-bytes check skipped: no $ASSET_FILE in $checkout"; return 0; }
  want=$(tr -d '\r' < "$checkout/$ASSET_FILE" | sha256sum | cut -c1-64)
  for i in 1 2 3; do
    got=$(curl -s --max-time 60 "https://$fqdn$ASSET_URL" | tr -d '\r' | sha256sum | cut -c1-64)
    [ "$got" = "$want" ] || { say "  served bytes #$i: $got != checkout $want"; return 1; }
  done
  say "  served bytes of $ASSET_URL match the checkout x3"
}

set_traffic() {   # $1 revision=100, $2 revision=0 (optional); read back and refuse a mismatch
  local to="$1" from="${2:-}" got
  if [ -n "$from" ]; then az containerapp ingress traffic set -n "$APP" -g "$RG" --subscription "$SUB" --revision-weight "$to=100" "$from=0" -o none < /dev/null
  else az containerapp ingress traffic set -n "$APP" -g "$RG" --subscription "$SUB" --revision-weight "$to=100" -o none < /dev/null; fi
  got=$(traffic_holder) || return 1
  [ "$got" = "$to" ] || { say "ABORT: traffic read-back says $got holds 100 %, not $to" >&2; return 1; }
  say "  traffic: 100 % -> $to (read back)"
}

deactivate() { az containerapp revision deactivate -n "$APP" -g "$RG" --subscription "$SUB" --revision "$1" -o none < /dev/null && say "  deactivated $1"; }

case "$CMD" in
# ------------------------------------------------------------------------------------------- setup
setup)
  say "== canary setup on $ENV ($APP) =="
  MODE=$(app_q properties.configuration.activeRevisionsMode)
  TARGET_PORT=$(app_q properties.configuration.ingress.targetPort); [ -n "$TARGET_PORT" ] && PORT="$TARGET_PORT"
  say "mode=$MODE targetPort=$PORT latest=$(app_q properties.latestReadyRevisionName)"
  # 1. probes on /health (a floor, not a dependency check — the self-test carries the weight), added while
  #    still in Single mode, where the platform itself moves traffic only when the new revision is ready.
  HAVE=$(app_q 'length(properties.template.containers[0].probes || `[]`)')
  if [ "${HAVE:-0}" = "0" ]; then
    # A PATCH of the TEMPLATE only, through the ARM API: the request never carries the app's secrets or
    # ingress (a YAML round-trip of the whole definition would), and the template is the revision-scope
    # section, so this creates one new revision with the probes and nothing else changed.
    APP_ID=$(app_q id)
    az containerapp show -n "$APP" -g "$RG" --subscription "$SUB" -o json < /dev/null | tr -d '\r' > "$OUT/app.json"
    "$PY" - "$OUT_PY/app.json" "$PORT" "$OUT_PY/patch.json" <<'PYEOF'
import json, sys
app, port, out = json.load(open(sys.argv[1], encoding="utf-8")), int(sys.argv[2]), sys.argv[3]
t = app["properties"]["template"]
http = {"path": "/health", "port": port, "scheme": "HTTP"}
t["containers"][0]["probes"] = [
    {"type": "Startup",   "httpGet": dict(http), "initialDelaySeconds": 5,  "periodSeconds": 5,  "failureThreshold": 30, "timeoutSeconds": 5},
    {"type": "Readiness", "httpGet": dict(http), "initialDelaySeconds": 5,  "periodSeconds": 10, "failureThreshold": 3,  "timeoutSeconds": 5},
    {"type": "Liveness",  "httpGet": dict(http), "initialDelaySeconds": 10, "periodSeconds": 30, "failureThreshold": 3,  "timeoutSeconds": 5},
]
# Only the template fields the stable API defines: the CLI's own output carries newer ones (imageType, …)
# that a PATCH against 2025-01-01 refuses as "unknown properties" (measured on dev, 2026-09-11).
CONTAINER_KEYS = {"name", "image", "command", "args", "env", "resources", "probes", "volumeMounts"}
TEMPLATE_KEYS = {"containers", "initContainers", "scale", "volumes", "terminationGracePeriodSeconds", "serviceBinds"}
t["containers"] = [{k: v for k, v in c.items() if k in CONTAINER_KEYS} for c in t["containers"]]
if t.get("initContainers"):
    t["initContainers"] = [{k: v for k, v in c.items() if k in CONTAINER_KEYS} for c in t["initContainers"]]
t = {k: v for k, v in t.items() if k in TEMPLATE_KEYS and v is not None}
json.dump({"properties": {"template": t}}, open(out, "w", encoding="utf-8"))
print("probes: startup/readiness/liveness on /health:%d in the template patch" % port)
PYEOF
    az rest --method patch --subscription "$SUB" --url "https://management.azure.com${APP_ID}?api-version=2025-01-01" --body "@$OUT_PY/patch.json" -o none < /dev/null   # the Windows-side az cannot open an MSYS /tmp path (lesson #190)
    sleep 10
    NEWREV=$(app_q properties.latestRevisionName); say "probe revision: $NEWREV"; wait_ready "$NEWREV" || { say "ABORT: the probe revision never became ready." >&2; exit 1; }
    [ "$(app_q 'length(properties.template.containers[0].probes || `[]`)')" = "3" ] || { say "ABORT: probes not present on read-back." >&2; exit 1; }
    say "probes in place (read back: 3)"
  else
    say "probes already present"
  fi
  # 2. Multiple revision mode and, in the same breath, traffic pinned by name to the revision that is live
  #    now — in Multiple mode the default 'latest' rule would move traffic the instant a revision appeared.
  LIVE=$(app_q properties.latestReadyRevisionName)
  [ "$MODE" = "Multiple" ] || az containerapp revision set-mode -n "$APP" -g "$RG" --subscription "$SUB" --mode multiple -o none < /dev/null
  az containerapp ingress traffic set -n "$APP" -g "$RG" --subscription "$SUB" --revision-weight "$LIVE=100" -o none < /dev/null
  MODE2=$(app_q properties.configuration.activeRevisionsMode); HOLDER=$(traffic_holder)
  [ "$MODE2" = "Multiple" ] && [ "$HOLDER" = "$LIVE" ] || { say "ABORT: read-back mode=$MODE2 holder=$HOLDER (wanted Multiple / $LIVE)" >&2; exit 1; }
  say "setup done: mode=Multiple, traffic 100 % -> $LIVE by name (read back)"
  ;;
# ------------------------------------------------------------------------------------------ deploy
deploy)
  TAG="${3:-}"; DRILL="${4:-0}"; CHECKOUT="${5:-}"
  printf '%s' "$TAG" | grep -Eq '^[a-z0-9]{8}(-r[0-9]{8})?$' || { say "ABORT: image tag '$TAG' is not <sha8> or <sha8>-rYYYYMMDD." >&2; exit 2; }
  case "$DRILL" in 0|1) ;; *) say "ABORT: drill must be 0 or 1." >&2; exit 2 ;; esac
  say "== canary deploy on $ENV: $IMG:$TAG drill=$DRILL =="
  [ "$(app_q properties.configuration.activeRevisionsMode)" = "Multiple" ] || { say "ABORT: $APP is not in Multiple revision mode — run setup first." >&2; exit 1; }
  azq acr repository show -n "${REG%%.*}" --image "$IMG:$TAG" --query digest >/dev/null || { say "ABORT: $IMG:$TAG is not in ${REG%%.*}." >&2; exit 1; }
  PREV=$(traffic_holder); say "previous (holds traffic): $PREV"; printf '%s' "$PREV" > "$OUT/prev.txt"
  SUFFIX="$TAG-${CANARY_SUFFIX:-$(date -u +%d%H%M%S)}"; NEW="$APP--$SUFFIX"
  say "creating $NEW at 0 % traffic ..."
  az containerapp update -n "$APP" -g "$RG" --subscription "$SUB" --image "$REG/$IMG:$TAG" --revision-suffix "$SUFFIX" \
    --min-replicas 1 --set-env-vars "APP_VERSION=$TAG" "APP_ENV=$APP_ENV" "APP_SELFTEST_FAIL=$DRILL" -o none < /dev/null
  printf '%s' "$NEW" > "$OUT/new.txt"
  HOLDER=$(traffic_holder); [ "$HOLDER" = "$PREV" ] || { say "ABORT: traffic moved to $HOLDER on creation — pin it back by hand: az containerapp ingress traffic set -n $APP -g $RG --subscription $SUB --revision-weight $PREV=100" >&2; exit 1; }
  if ! wait_ready "$NEW"; then
    say "FAIL: $NEW never became ready; it has 0 % traffic. Deactivating it; $PREV keeps serving."
    deactivate "$NEW" || true; exit 1
  fi
  # the self-test inside the new revision; the transcript is the evidence, the rules decide
  # The exec door wants a TERMINAL on stdin (`tty.setcbreak(sys.stdin.fileno())` inside the CLI; with no tty it
  # dies with "Inappropriate ioctl for device" — measured on a GitHub runner). On Linux
  # `script` lends it a pseudo-terminal; on the maintainer's Git Bash the plain call works and `script` is absent.
  run_selftest() {
    if command -v script >/dev/null 2>&1; then
      timeout 300 script -qec "az containerapp exec -n $APP -g $RG --subscription $SUB --revision $NEW --command 'python3 -m $SELFTEST_MODULE'" /dev/null > "$OUT/selftest.txt" 2>&1 || true
    else
      timeout 300 az containerapp exec -n "$APP" -g "$RG" --subscription "$SUB" --revision "$NEW" --command "python3 -m $SELFTEST_MODULE" > "$OUT/selftest.txt" 2>&1 < /dev/null || true
    fi
  }
  # A verdict's exit code is DATA (0 pass, 1 fail, 3 could-not-run): read in an `|| VRC=$?` list, which
  # neither errexit nor the ERR trap treats as a failure (lesson #186).
  verdict() { VRC=0; TRANSCRIPT="$OUT_PY/selftest.txt" EXPECTED_VERSION="$TAG" DRILL="$DRILL" OUT="$OUT_PY" "$PY" -m infra.canary_rules > "$OUT/verdict.txt" || VRC=$?; }
  run_selftest; verdict
  if [ $VRC -eq 3 ]; then
    say "the exec door did not answer; waiting ${DOOR_LOCKOUT_WAIT}s past its lockout and trying once more ..."; sleep "$DOOR_LOCKOUT_WAIT"; run_selftest; verdict
  fi
  cat "$OUT/verdict.txt"
  if [ $VRC -eq 3 ]; then say "COULD NOT RUN: the self-test never ran inside $NEW. Refusing to move traffic; deactivating $NEW; $PREV keeps serving."; deactivate "$NEW" || true; exit 3; fi
  if [ $VRC -ne 0 ]; then
    if [ "$DRILL" = "1" ] && grep -q '"drill_fired": true' "$OUT/canary-verdict.json"; then
      deactivate "$NEW" || true
      say "DRILL PASSED: the lever fired inside $NEW, the revision was refused traffic and deactivated; $PREV never stopped serving."; exit 0
    fi
    say "FAIL before traffic: $NEW refused (see the verdict); deactivating it; $PREV keeps serving."; deactivate "$NEW" || true; exit 1
  fi
  [ "$DRILL" = "1" ] && { say "DRILL FAILED: a drill revision passed the self-test — the lever never reached it. Deactivating $NEW."; deactivate "$NEW" || true; exit 1; }
  # move the traffic, then prove it through the public name
  set_traffic "$NEW" "$PREV"
  FQDN=$(app_q properties.configuration.ingress.fqdn)
  if ! health_x3 "$FQDN" || { [ -n "$CHECKOUT" ] && ! served_bytes_match "$FQDN" "$CHECKOUT"; }; then
    say "FAIL after the switch: rolling traffic back to $PREV ..."
    set_traffic "$PREV" "$NEW" && health_x3 "$FQDN" && say "  rollback verified: $PREV serves again" || say "  ROLLBACK NOT VERIFIED — run by hand: az containerapp ingress traffic set -n $APP -g $RG --subscription $SUB --revision-weight $PREV=100 $NEW=0"
    deactivate "$NEW" || true; exit 1
  fi
  say "grace ${GRACE}s before deactivating $PREV ..."; sleep "$GRACE"
  health_x3 "$FQDN" || { say "FAIL during the grace period: rolling back ..."; set_traffic "$PREV" "$NEW"; deactivate "$NEW" || true; exit 1; }
  deactivate "$PREV"
  say "DEPLOYED: $NEW serves 100 % ($IMG:$TAG); previous $PREV deactivated (a restore point: bash infra/canary.sh rollback $ENV $PREV)."
  printf 'new=%s\nprev=%s\ntag=%s\n' "$NEW" "$PREV" "$TAG" > "$OUT/canary-summary.txt"
  ;;
# ---------------------------------------------------------------------------------------- rollback
rollback)
  TO="${3:-}"; FROM="${4:-}"
  [ -n "$TO" ] || { say "usage: $0 rollback <dev|prod> <to-revision> [<from-revision>]" >&2; exit 2; }
  say "== rollback on $ENV: traffic -> $TO =="
  if [ "$(rev_q "$TO" properties.active)" != "true" ] && [ "$(rev_q "$TO" properties.active)" != "True" ]; then
    say "$TO is inactive: reactivating (a cold start) ..."; az containerapp revision activate -n "$APP" -g "$RG" --subscription "$SUB" --revision "$TO" -o none < /dev/null
    wait_ready "$TO" || { say "ABORT: $TO did not become ready after reactivation." >&2; exit 1; }
  fi
  [ -z "$FROM" ] && FROM=$(traffic_holder)
  set_traffic "$TO" "$FROM"
  health_x3 "$(app_q properties.configuration.ingress.fqdn)" || { say "WARNING: $TO serves but /health is not ok x3" >&2; exit 1; }
  [ "$FROM" != "$TO" ] && deactivate "$FROM" || true
  say "ROLLED BACK: $TO serves 100 %."
  ;;
# ------------------------------------------------------------------------------------------ status
status)
  say "mode=$(app_q properties.configuration.activeRevisionsMode)  fqdn=$(app_q properties.configuration.ingress.fqdn)"
  say "traffic: $(app_q "properties.configuration.ingress.traffic[].[revisionName, weight, latestRevision]" | tr '\t' '=' | tr '\n' ' ')"
  az containerapp revision list -n "$APP" -g "$RG" --subscription "$SUB" --all --query "[].{name:name, active:properties.active, traffic:properties.trafficWeight, health:properties.healthState, state:properties.runningState, created:properties.createdTime}" -o table < /dev/null | tr -d '\r'
  ;;
*) echo "usage: $0 setup|deploy|rollback|status <dev|prod> ..." >&2; exit 2 ;;
esac

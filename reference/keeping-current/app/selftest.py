"""Self-test — the canary's probe inside a new revision.

Contract (`spec/keeping-current.md`, `adapters/github-azure.md`):
`python3 -m app.selftest` (no quotes: it crosses shell → az → container) prints a
first line `AZURE_CRED_MODE = …`, a line `APP_VERSION = …`, one row per probe
`name  PASS|FAIL  detail`, and closes with `all N configured service(s) reachable`
on success; exit 0/1. `APP_SELFTEST_FAIL=1` adds one deliberate failure (the drill).

This file is the skeleton. Add one REAL call per service the app uses; a config
read is not proof. Do not import a product module from this kit copy — the
project's version extends `_probes`.
"""
from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request


def _drill_lever(env):
    """The drill: fires only on the exact value "1", so a stray variable never turns every deploy red."""
    if env.get("APP_SELFTEST_FAIL") == "1":
        return ("drill (APP_SELFTEST_FAIL)", False,
                "APP_SELFTEST_FAIL=1 on this revision: one deliberate failure so the canary's rollback is exercised")
    return None


def _run(name, fn):
    try:
        return (name, True, str(fn()))
    except Exception as e:      # noqa: BLE001 — a probe reports, it never raises
        return (name, False, f"{type(e).__name__}: {e}")


def _health_url(env):
    return env.get("SELFTEST_HEALTH_URL", "http://127.0.0.1:8000/health")


def _probe_health(url):
    with urllib.request.urlopen(url, timeout=5) as r:      # noqa: S310 — a fixed local URL
        assert r.status == 200, f"{url} -> {r.status}"
        return f"{url} 200"


def _probes(env):
    """Override in the project: return extra (name, fn) pairs. One real call each."""
    return []


def main(argv=None):
    env = os.environ
    print(f"AZURE_CRED_MODE = {env.get('AZURE_CRED_MODE', '(unset)')}")
    print(f"APP_VERSION = {env.get('APP_VERSION', '(unset)')}")
    results = [_run(name, fn) for name, fn in _probes(env)]
    url = _health_url(env)
    try:
        urllib.request.urlopen(url, timeout=3).close()
        listening = True
    except (urllib.error.URLError, OSError, ValueError):
        listening = False
    if listening:
        results.append(_run("health (live server)", lambda: _probe_health(url)))
    else:
        print(f"health (live server)   SKIP  nothing listens at {url} (not inside the running container)")
    drill = _drill_lever(env)
    if drill:
        results.append(drill)
    bad = 0
    for name, ok, detail in results:
        print(f"{name:22} {'PASS' if ok else 'FAIL'}  {detail}")
        bad += 0 if ok else 1
    print("-" * 72)
    if bad:
        print(f"{bad} service(s) FAILED.")
        return 1
    print(f"all {len(results)} configured service(s) reachable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

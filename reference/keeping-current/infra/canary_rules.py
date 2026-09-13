"""The canary's verdict on a self-test transcript — the rules behind `infra/canary.sh` (spec/keeping-current.md B3).

`az containerapp exec` returns 0 whatever the remote command did (measured 2026-09-11: "No module named
pip" came back with exit 0), so the transcript is the only evidence, and it is read here, in a pure
module behind tests, never by a grep in the shell.

Three outcomes, never two (the two-lanes panel's failure lens, F9):

    PASS           the self-test ran on the expected version, every service passed, the closing line is there
    FAIL           it ran and something is wrong: a service failed, the wrong version answered, the closing
                   line is missing, or the drill lever is on a revision that was not a drill
    COULD_NOT_RUN  no transcript: the exec door refused, hung, was rate-limited or answered with an error page.
                   This is neither green nor red. The shell retries once after a wait longer than the
                   door's lockout, then fails closed with an issue that says "the check could not run".

A drill (`APP_SELFTEST_FAIL=1` on the new revision) is a run that MUST fail on the lever and on nothing else:
a green drill means the lever never reached the revision (the wiring is wrong); a drill that fails on a real
service is a real failure and is reported as one. `python3 -m infra.canary_rules` is the flagless CLI the
shell calls: inputs from the environment (TRANSCRIPT, EXPECTED_VERSION, DRILL, OUT); exit 0 PASS, 1 FAIL,
3 COULD_NOT_RUN, 2 misuse.
"""
import dataclasses
import json
import os
import pathlib
import re
import sys

PASS, FAIL, COULD_NOT_RUN = "PASS", "FAIL", "COULD_NOT_RUN"

_HEALTH_OK = re.compile(r'"status"\s*:\s*"ok"')                         # /health JSON; whitespace is not a fail
_HEADER = re.compile(r"^AZURE_CRED_MODE = ", re.M)                      # the self-test's first line
_VERSION = re.compile(r"^APP_VERSION = (\S+)", re.M)
_ROW = re.compile(r"^(?P<name>.+?)\s+(?P<verdict>PASS|FAIL)\s{2}(?P<detail>.*)$", re.M)
_CLOSING = re.compile(r"^all \d+ configured service\(s\) reachable", re.M)
_DRILL = "drill"


@dataclasses.dataclass(frozen=True)
class SelftestResult:
    ran: bool
    version: str = ""
    passed: bool = False
    failed: tuple = ()          # the FAIL rows' names, in transcript order
    tail: str = ""              # the last lines, for the issue


@dataclasses.dataclass(frozen=True)
class Verdict:
    kind: str
    reason: str = ""
    drill_fired: bool = False


def health_body_ok(body):
    """True when GET /health says status ok. Compact or spaced JSON both count; `"okay"` does not."""
    return _HEALTH_OK.search(body or "") is not None


def parse_selftest(text):
    """The transcript as the self-test wrote it, whatever the exec door wrapped around it."""
    text = (text or "").replace("\r", "")
    tail = "\n".join(text.strip().splitlines()[-12:])
    if not _HEADER.search(text):
        return SelftestResult(ran=False, tail=tail)
    m = _VERSION.search(text)
    failed = tuple(r.group("name").strip() for r in _ROW.finditer(text) if r.group("verdict") == "FAIL")
    passed = bool(_CLOSING.search(text)) and not failed
    return SelftestResult(ran=True, version=(m.group(1) if m else ""), passed=passed, failed=failed, tail=tail)


def decide(result, *, expected_version, drill=False):
    """One verdict. RED-first inside the FAIL family: the wrong version before anything, then real services."""
    if not result.ran:
        return Verdict(COULD_NOT_RUN, "the self-test could not run: the exec door did not answer with a transcript"
                                     + (f" — it said: {result.tail[:160]!r}" if result.tail else ""))
    lever = tuple(n for n in result.failed if _DRILL in n.lower())
    real = tuple(n for n in result.failed if _DRILL not in n.lower())
    if expected_version and result.version != expected_version:
        return Verdict(FAIL, f"the revision reports APP_VERSION {result.version or '(none)'}, not the expected "
                             f"{expected_version} — the check ran against the wrong bytes", drill_fired=bool(lever))
    if real:
        return Verdict(FAIL, f"self-test FAIL: {', '.join(real)}", drill_fired=False)
    if drill:
        if lever:
            return Verdict(FAIL, "the drill lever fired as intended: one deliberate failure, nothing else — "
                                 "rollback must follow", drill_fired=True)
        return Verdict(FAIL, "the drill lever did not fire: the revision does not carry APP_SELFTEST_FAIL=1, "
                             "so this run proves nothing about the rollback", drill_fired=False)
    if lever:
        return Verdict(FAIL, "the drill lever is set on a revision that is not a drill — a real deploy must "
                             "never carry APP_SELFTEST_FAIL", drill_fired=True)
    if not result.passed:
        return Verdict(FAIL, "the transcript ended without the self-test's closing line — the run was cut short")
    return Verdict(PASS, f"self-test passed on {result.version}")


def _say(text):
    sys.stdout.buffer.write((text + "\n").encode("utf-8")); sys.stdout.flush()


def main(argv=None):
    env = os.environ
    path = env.get("TRANSCRIPT", "")
    if not path:
        _say("usage: TRANSCRIPT=<file> EXPECTED_VERSION=<tag> DRILL=0|1 [OUT=<dir>] python3 -m infra.canary_rules")
        return 2
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        _say(f"REFUSED: cannot read the transcript {path}: {e}")
        return 2
    v = decide(parse_selftest(text), expected_version=env.get("EXPECTED_VERSION", ""), drill=env.get("DRILL", "0") == "1")
    _say(f"verdict {v.kind}\n{v.reason}")
    if env.get("OUT"):
        pathlib.Path(env["OUT"], "canary-verdict.json").write_text(
            json.dumps({"kind": v.kind, "reason": v.reason, "drill_fired": v.drill_fired}, indent=2), encoding="utf-8")
    return {PASS: 0, FAIL: 1, COULD_NOT_RUN: 3}[v.kind]


if __name__ == "__main__":
    sys.exit(main())

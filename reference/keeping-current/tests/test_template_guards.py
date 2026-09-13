"""String-scan the shells and workflows for the fail-closed install surface.

The Python rule modules cannot see a dropped placeholder abort, a self-grep that
never clears, a scheduled `full` default, or an extra `)` in weekly-note.yml.
These pins fail when those lines disappear. Fictional paths only.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def test_freshness_guard_checks_env_values_not_the_file_text():
    fresh = _read("templates", "freshness.yml")
    assert "grep -q '__[A-Z_]*__'" not in fresh
    assert 'case "$SUB$ACR$IMG$REG$OWNER"' in fresh
    assert "vars.FRESHNESS_APPLY == 'on'" in fresh
    assert "inputs.mode || 'full'" not in fresh
    assert "the three repositories" not in fresh
    assert "__OTHER_REPOSITORY" not in fresh
    assert 'os.environ["IMG"]' in fresh
    assert "live['__APP_REPOSITORY__']" not in fresh
    assert "--assignee __OWNER_GITHUB_LOGIN__" not in fresh


def test_deploy_and_canary_and_retention_guards_are_value_cases():
    deploy = _read("templates", "deploy.yml")
    canary = _read("infra", "canary.sh")
    retention = _read("infra", "registry-retention.sh")
    assert 'case "$RG$ACR$APP$IMG$OWNER"' in deploy
    assert "--assignee __OWNER_GITHUB_LOGIN__" not in deploy
    assert 'case "$SUB$RG$APP$REG$IMG"' in canary
    assert '*__*)' in retention


def test_weekly_note_issue_create_is_valid_bash():
    note = _read("templates", "weekly-note.yml")
    assert note.count('--assignee "$OWNER"))') == 0
    assert '--assignee "$OWNER")' in note


def test_automerge_noops_until_the_routine_lane_is_on():
    auto = _read("templates", "dependabot-automerge.yml")
    assert "vars.ROUTINE_LANE == 'on'" in auto
    assert "vars.ROUTINE_LANE != 'on'" in auto


def test_canary_sh_moves_traffic_only_after_the_verdict():
    text = _read("infra", "canary.sh")
    _, _, after_deploy = text.partition("# ------------------------------------------------------------------------------------------ deploy")
    deploy, _, _ = after_deploy.partition("# ---------------------------------------------------------------------------------------- rollback")
    assert deploy, "canary.sh lost its deploy section markers"
    switch = deploy.find('set_traffic "$NEW" "$PREV"')
    verdict = deploy.find("if [ $VRC -eq 3 ]")
    assert 0 <= verdict < switch
    assert deploy.find("health_x3") > switch
    assert "from infra.canary_rules import health_body_ok" in text
    compact_glob = """*'"status":"ok"'*"""
    assert compact_glob not in text

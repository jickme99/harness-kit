"""String-scan the shells and workflows for the fail-closed install surface.

The Python rule modules cannot see a dropped placeholder abort, a self-grep that
never clears, a scheduled `full` default, or an extra `)` in weekly-note.yml.
These pins fail when those lines disappear. Fictional paths only.

Workflows are read through `read_chassis`: the kit keeps them under `templates/`;
STANDUP copies them to `.github/workflows/` (and skips automerge until adoption D).
"""
import conftest as kc


def test_chassis_file_finds_workflows_after_standup_copy(tmp_path, monkeypatch):
    dest = tmp_path / ".github" / "workflows"
    dest.mkdir(parents=True)
    (dest / "freshness.yml").write_text("MODE: dry\n", encoding="utf-8")
    monkeypatch.setattr(kc, "ROOT", tmp_path)
    assert kc.chassis_file("templates", "freshness.yml").read_text(encoding="utf-8") == "MODE: dry\n"
    assert kc.chassis_file("templates", "dependabot-automerge.yml") is None


def test_freshness_guard_checks_env_values_not_the_file_text(read_chassis):
    fresh = read_chassis("templates", "freshness.yml")
    assert "grep -q '__[A-Z_]*__'" not in fresh
    assert 'case "$SUB$ACR$IMG$REG$OWNER"' in fresh
    assert "vars.FRESHNESS_APPLY == 'on'" in fresh
    assert "inputs.mode || 'full'" not in fresh
    assert "the three repositories" not in fresh
    assert "__OTHER_REPOSITORY" not in fresh
    assert 'os.environ["IMG"]' in fresh
    assert "live['__APP_REPOSITORY__']" not in fresh
    assert "--assignee __OWNER_GITHUB_LOGIN__" not in fresh


def test_deploy_guard_checks_env_values_when_the_app_workflow_is_installed(read_chassis):
    deploy = read_chassis("templates", "deploy.yml", optional=True)
    assert 'case "$RG$ACR$APP$IMG$OWNER"' in deploy
    assert "--assignee __OWNER_GITHUB_LOGIN__" not in deploy


def test_canary_and_retention_guards_are_value_cases(read_chassis):
    canary = read_chassis("infra", "canary.sh")
    retention = read_chassis("infra", "registry-retention.sh")
    assert 'case "$SUB$RG$APP$REG$IMG"' in canary
    assert '*__*)' in retention


def test_weekly_note_issue_create_is_valid_bash(read_chassis):
    note = read_chassis("templates", "weekly-note.yml")
    assert note.count('--assignee "$OWNER"))') == 0
    assert '--assignee "$OWNER")' in note


def test_automerge_noops_until_the_routine_lane_is_on(read_chassis):
    auto = read_chassis("templates", "dependabot-automerge.yml", optional=True)
    assert "vars.ROUTINE_LANE == 'on'" in auto
    assert "vars.ROUTINE_LANE != 'on'" in auto


def test_canary_sh_moves_traffic_only_after_the_verdict(read_chassis):
    text = read_chassis("infra", "canary.sh")
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

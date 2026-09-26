from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_production_rollout_documents_security_context_smoke_gate():
    runbook = (ROOT / "docs" / "runbooks" / "production-rollout.md").read_text()

    assert "deployment_security_context_hardened" in runbook
    assert "fsGroup=1000" in runbook
    assert "capabilities.drop=ALL" in runbook


def test_production_rollout_requires_rcon_status_before_disruptive_rollout():
    runbook = (ROOT / "docs" / "runbooks" / "production-rollout.md").read_text()

    assert "Gate 2: pre-rollout disruption check" in runbook
    assert "cs2-rcon.py" in runbook
    assert "status" in runbook
    assert "Do not force a rollout while human players are connected" in runbook


def test_production_rollout_documents_automated_disruption_guard_override():
    runbook = (ROOT / "docs" / "runbooks" / "production-rollout.md").read_text()

    assert "cs2_tools.disruption_guard" in runbook
    assert "allow-active-players" in runbook
    assert "defaults to false" in runbook


def test_production_rollout_documents_update_checker_hardening_gate():
    runbook = (ROOT / "docs" / "runbooks" / "production-rollout.md").read_text()

    assert "update_checker_hardened" in runbook
    assert "rollout waits for ready appmanifest before tracker patch" in runbook
    assert "pods/exec" in runbook


def test_server_generator_documents_platform_managed_security_context():
    runbook = (ROOT / "docs" / "runbooks" / "server-generator.md").read_text()

    assert "security context is platform-managed" in runbook
    assert "securityContext" in runbook
    assert "podSecurityContext" in runbook

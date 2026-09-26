from pathlib import Path

import yaml

from cs2_tools.production_check import ProductionCheck, run_production_checks


def write_minimal_repo(root: Path) -> None:
    (root / "configs" / "modes" / "all-weapons-dm").mkdir(parents=True)
    (root / "plugins").mkdir()
    (root / "k8s" / "base").mkdir(parents=True)
    (root / "k8s" / "servers").mkdir(parents=True)
    (root / "plugins" / "plugins.yaml").write_text("plugins: {}\n")
    (root / "k8s" / "kustomization.yaml").write_text(
        "resources:\n"
        "  - base/update-checker.yaml\n"
        "  - servers/staging-mirage-multicfg-01-deployment.yaml\n"
    )
    (root / "k8s" / "base" / "update-checker.yaml").write_text(
        yaml.safe_dump(
            {
                "apiVersion": "batch/v1",
                "kind": "CronJob",
                "metadata": {"name": "cs2-update-checker", "namespace": "cs2-servers"},
                "spec": {"schedule": "*/15 * * * *"},
            },
            sort_keys=False,
        )
    )
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "staging-mirage-multicfg-01", "namespace": "cs2-servers"},
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "cs2",
                            "image": "zizobg/cs2-server@sha256:" + "a" * 64,
                            "env": [
                                {"name": "CS2_MODE", "value": "all-weapons-dm"},
                                {"name": "MAP_GROUP", "value": "mg_dm"},
                                {"name": "STEAM_UPDATE_POLICY", "value": "always"},
                                {"name": "ENABLE_PLUGIN_RUNTIME", "value": "true"},
                                {"name": "CS2_DISABLED_PLUGINS", "value": "GameModeManager,MenuManagerAPI"},
                            ],
                        }
                    ]
                }
            }
        },
    }
    (root / "k8s" / "servers" / "staging-mirage-multicfg-01-deployment.yaml").write_text(yaml.safe_dump(deployment, sort_keys=False))
    (root / "configs" / "modes" / "all-weapons-dm" / "mode.yaml").write_text(
        "name: all-weapons-dm\n"
        "displayName: All Weapons DM\n"
        "defaultMap: de_mirage\n"
        "exec: all-weapons-dm.cfg\n"
        "maxPlayers: 24\n"
        "gameType: 1\n"
        "gameMode: 2\n"
        "mapGroup: mg_dm\n"
        "plugins:\n"
        "  disabledRuntime:\n"
        "    - GameModeManager\n"
        "    - MenuManagerAPI\n"
    )


def test_production_checks_pass_for_minimal_ready_repo(tmp_path):
    write_minimal_repo(tmp_path)

    checks = run_production_checks(tmp_path)

    assert all(check.ok for check in checks), checks
    assert ProductionCheck("image_pinned", True, "zizobg/cs2-server@sha256:" + "a" * 64) in checks
    assert any(check.name == "update_checker_present" and check.ok for check in checks)
    assert ProductionCheck("disabled_plugins_match_mode", True, "deployment=GameModeManager,MenuManagerAPI mode=GameModeManager,MenuManagerAPI") in checks


def test_production_checks_fail_when_disabled_plugins_drift_from_mode(tmp_path):
    write_minimal_repo(tmp_path)
    deployment_path = tmp_path / "k8s" / "servers" / "staging-mirage-multicfg-01-deployment.yaml"
    deployment = yaml.safe_load(deployment_path.read_text())
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    for item in container["env"]:
        if item["name"] == "CS2_DISABLED_PLUGINS":
            item["value"] = "MenuManagerAPI"
    deployment_path.write_text(yaml.safe_dump(deployment, sort_keys=False))

    checks = {check.name: check for check in run_production_checks(tmp_path)}

    assert checks["disabled_plugins_match_mode"].ok is False
    assert checks["disabled_plugins_match_mode"].detail == "deployment=MenuManagerAPI mode=GameModeManager,MenuManagerAPI"


def test_production_checks_fail_for_tagged_image_and_disabled_updater(tmp_path):
    write_minimal_repo(tmp_path)
    deployment_path = tmp_path / "k8s" / "servers" / "staging-mirage-multicfg-01-deployment.yaml"
    deployment = yaml.safe_load(deployment_path.read_text())
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    container["image"] = "zizobg/cs2-server:latest"
    container["env"] = [{"name": "STEAM_UPDATE_POLICY", "value": "manifest"}]
    deployment_path.write_text(yaml.safe_dump(deployment, sort_keys=False))
    (tmp_path / "k8s" / "kustomization.yaml").write_text("resources:\n  - servers/staging-mirage-multicfg-01-deployment.yaml\n")

    checks = {check.name: check for check in run_production_checks(tmp_path)}

    assert checks["image_pinned"].ok is False
    assert checks["steam_update_policy"].ok is False
    assert checks["update_checker_present"].ok is False

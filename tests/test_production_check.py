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
        "  - servers/staging-mirage-multicfg-01-configmap.yaml\n"
        "  - servers/staging-mirage-multicfg-01-deployment.yaml\n"
        "  - servers/staging-mirage-multicfg-01-service.yaml\n"
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
    configmap = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": "staging-mirage-multicfg-01-config", "namespace": "cs2-servers"},
        "data": {"server.cfg": 'hostname "ZIZO.GG Staging All Weapons DM"\nsv_lan 0\n'},
    }
    (root / "k8s" / "servers" / "staging-mirage-multicfg-01-configmap.yaml").write_text(yaml.safe_dump(configmap, sort_keys=False))
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "staging-mirage-multicfg-01", "namespace": "cs2-servers"},
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "zizo.gg/display-name": "All Weapons DM",
                        "zizo.gg/map": "de_mirage",
                        "zizo.gg/public-address": "zizogaming.duckdns.org:26001",
                    }
                },
                "spec": {
                    "securityContext": {"fsGroup": 1000, "fsGroupChangePolicy": "OnRootMismatch"},
                    "containers": [
                        {
                            "name": "cs2",
                            "image": "zizobg/cs2-server@sha256:" + "a" * 64,
                            "resources": {
                                "requests": {"cpu": "1000m", "memory": "2Gi"},
                                "limits": {"cpu": "4000m", "memory": "8Gi"},
                            },
                            "securityContext": {
                                "runAsUser": 1000,
                                "runAsGroup": 1000,
                                "allowPrivilegeEscalation": False,
                                "capabilities": {"drop": ["ALL"]},
                            },
                            "env": [
                                {"name": "CS2_MODE", "value": "all-weapons-dm"},
                                {"name": "MAP", "value": "de_mirage"},
                                {"name": "PORT", "value": "26001"},
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
    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": "staging-mirage-multicfg-01", "namespace": "cs2-servers"},
        "spec": {
            "type": "LoadBalancer",
            "externalTrafficPolicy": "Local",
            "ports": [
                {"name": "game-tcp", "port": 26001, "targetPort": "game-tcp", "protocol": "TCP"},
                {"name": "game-udp", "port": 26001, "targetPort": "game-udp", "protocol": "UDP"},
            ],
        },
    }
    (root / "k8s" / "servers" / "staging-mirage-multicfg-01-service.yaml").write_text(yaml.safe_dump(service, sort_keys=False))
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
    assert ProductionCheck("map_matches_mode_default", True, "deployment=de_mirage annotation=de_mirage mode=de_mirage") in checks
    assert ProductionCheck("hostname_contains_mode_display", True, "hostname=ZIZO.GG Staging All Weapons DM mode_display=All Weapons DM") in checks
    assert ProductionCheck("service_port_matches_deployment", True, "env=26001 public=26001 service_tcp=26001 service_udp=26001") in checks
    assert ProductionCheck("resources_declared", True, "requests.cpu=1000m requests.memory=2Gi limits.cpu=4000m limits.memory=8Gi") in checks
    assert ProductionCheck("security_context_hardened", True, "pod.fsGroup=1000 pod.fsGroupChangePolicy=OnRootMismatch container.runAsUser=1000 container.runAsGroup=1000 allowPrivilegeEscalation=False capabilities.drop=ALL") in checks


def test_production_checks_fail_when_map_or_hostname_drift_from_mode(tmp_path):
    write_minimal_repo(tmp_path)
    deployment_path = tmp_path / "k8s" / "servers" / "staging-mirage-multicfg-01-deployment.yaml"
    deployment = yaml.safe_load(deployment_path.read_text())
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    for item in container["env"]:
        if item["name"] == "MAP":
            item["value"] = "cs_office"
    deployment["spec"]["template"]["metadata"]["annotations"]["zizo.gg/map"] = "cs_office"
    deployment_path.write_text(yaml.safe_dump(deployment, sort_keys=False))

    configmap_path = tmp_path / "k8s" / "servers" / "staging-mirage-multicfg-01-configmap.yaml"
    configmap = yaml.safe_load(configmap_path.read_text())
    configmap["data"]["server.cfg"] = 'hostname "ZIZO.GG Staging Multi-CFG"\n'
    configmap_path.write_text(yaml.safe_dump(configmap, sort_keys=False))

    checks = {check.name: check for check in run_production_checks(tmp_path)}

    assert checks["map_matches_mode_default"].ok is False
    assert checks["map_matches_mode_default"].detail == "deployment=cs_office annotation=cs_office mode=de_mirage"
    assert checks["hostname_contains_mode_display"].ok is False
    assert checks["hostname_contains_mode_display"].detail == "hostname=ZIZO.GG Staging Multi-CFG mode_display=All Weapons DM"

def test_production_checks_fail_when_security_context_is_missing_or_privileged(tmp_path):
    write_minimal_repo(tmp_path)
    deployment_path = tmp_path / "k8s" / "servers" / "staging-mirage-multicfg-01-deployment.yaml"
    deployment = yaml.safe_load(deployment_path.read_text())
    pod_spec = deployment["spec"]["template"]["spec"]
    pod_spec.pop("securityContext")
    container = pod_spec["containers"][0]
    container["securityContext"] = {"runAsUser": 0, "allowPrivilegeEscalation": True, "capabilities": {"drop": []}}
    deployment_path.write_text(yaml.safe_dump(deployment, sort_keys=False))

    checks = {check.name: check for check in run_production_checks(tmp_path)}

    assert checks["security_context_hardened"].ok is False
    assert checks["security_context_hardened"].detail == "pod.fsGroup=missing pod.fsGroupChangePolicy=missing container.runAsUser=0 container.runAsGroup=missing allowPrivilegeEscalation=True capabilities.drop="


def test_production_checks_fail_when_container_resources_are_missing_or_partial(tmp_path):
    write_minimal_repo(tmp_path)
    deployment_path = tmp_path / "k8s" / "servers" / "staging-mirage-multicfg-01-deployment.yaml"
    deployment = yaml.safe_load(deployment_path.read_text())
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    container["resources"] = {"requests": {"cpu": "1000m"}, "limits": {"memory": "8Gi"}}
    deployment_path.write_text(yaml.safe_dump(deployment, sort_keys=False))

    checks = {check.name: check for check in run_production_checks(tmp_path)}

    assert checks["resources_declared"].ok is False
    assert checks["resources_declared"].detail == "requests.cpu=1000m requests.memory=missing limits.cpu=missing limits.memory=8Gi"


def test_production_checks_fail_when_service_or_public_port_drift_from_deployment(tmp_path):
    write_minimal_repo(tmp_path)
    service_path = tmp_path / "k8s" / "servers" / "staging-mirage-multicfg-01-service.yaml"
    service = yaml.safe_load(service_path.read_text())
    service["spec"]["ports"][0]["port"] = 26002
    service_path.write_text(yaml.safe_dump(service, sort_keys=False))

    deployment_path = tmp_path / "k8s" / "servers" / "staging-mirage-multicfg-01-deployment.yaml"
    deployment = yaml.safe_load(deployment_path.read_text())
    deployment["spec"]["template"]["metadata"]["annotations"]["zizo.gg/public-address"] = "zizogaming.duckdns.org:26003"
    deployment_path.write_text(yaml.safe_dump(deployment, sort_keys=False))

    checks = {check.name: check for check in run_production_checks(tmp_path)}

    assert checks["service_port_matches_deployment"].ok is False
    assert checks["service_port_matches_deployment"].detail == "env=26001 public=26003 service_tcp=26002 service_udp=26001"


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
